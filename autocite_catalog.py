#!/usr/bin/env python3
"""AutoCite catalogo v0.4: alias persistenti, OpenAlex+Crossref, import Zotero 10+ (API ufficiale).
Non scrive mai sul database SQLite Zotero. Importazioni tramite API locale e consenso.
"""
from __future__ import annotations
import argparse
import csv
import json
import os
import re
import sqlite3
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote, urlencode
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from zotero_autocite import BASE, LocalZotero, ZoteroError, get_json, item_info, norm_doi, first_author_year


def data_dir():
    root = Path(os.environ.get('APPDATA') or (Path.home() / '.config')) / 'ZoteroAutoCite'
    root.mkdir(parents=True, exist_ok=True)
    return root

DEFAULT_DB = data_dir() / 'catalogo.sqlite3'
DEFAULT_SETTINGS = data_dir() / 'settings.json'


class CatalogError(RuntimeError):
    pass


def now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


class Catalog:
    def __init__(self, filename=DEFAULT_DB):
        self.filename = Path(filename)
        self.filename.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(str(self.filename), timeout=30)
        self.db.row_factory = sqlite3.Row
        self.db.executescript('''
        CREATE TABLE IF NOT EXISTS references_catalog (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          doi TEXT,
          title TEXT NOT NULL,
          year TEXT,
          authors TEXT NOT NULL DEFAULT '[]',
          meta_json TEXT NOT NULL DEFAULT '{}',
          origin TEXT NOT NULL,
          zotero_server TEXT,
          zotero_libtype TEXT,
          zotero_libid TEXT,
          zotero_key TEXT,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL
        );
        CREATE UNIQUE INDEX IF NOT EXISTS catalog_zotero_link ON references_catalog
          (zotero_server, zotero_libtype, zotero_libid, zotero_key);
        CREATE INDEX IF NOT EXISTS catalog_doi_index ON references_catalog(doi);
        ''')
        # Schema migration from v0.3: retains IDs/aliases and all Zotero links.
        columns = {r['name'] for r in self.db.execute('PRAGMA table_info(references_catalog)')}
        if 'openalex_id' not in columns:
            if self.filename.exists() and self.filename.stat().st_size:
                # Consistent, one-time backup of the v0.3 database before migration.
                backup = self.filename.with_name(self.filename.stem + '_backup_pre_0.4.sqlite3')
                if not backup.exists():
                    with sqlite3.connect(str(backup)) as archive:
                        self.db.backup(archive)
            self.db.execute('ALTER TABLE references_catalog ADD COLUMN openalex_id TEXT')
        self.db.execute('CREATE UNIQUE INDEX IF NOT EXISTS catalog_openalex_unique ON references_catalog(openalex_id) WHERE openalex_id IS NOT NULL')
        self.db.commit()

    def by_openalex(self, wid):
        return self.db.execute('SELECT * FROM references_catalog WHERE openalex_id=?', (wid,)).fetchone()

    def attach_openalex(self, ident, wid):
        already = self.by_openalex(wid)
        if already and already['id'] != int(ident):
            raise CatalogError('Identificativo OpenAlex già assegnato a un altro codice')
        self.db.execute('UPDATE references_catalog SET openalex_id=?, updated_at=? WHERE id=?',
                        (wid, now(), int(ident)))
        self.db.commit()

    def close(self):
        self.db.close()

    def alias(self, ident):
        return f'[[Z:{int(ident):05d}]]'

    def by_alias(self, value):
        match = re.fullmatch(r'(?:\[\[Z:)?0*(\d+)(?:\]\])?', str(value).strip(), re.I)
        if not match:
            return None
        return self.db.execute('SELECT * FROM references_catalog WHERE id=?', (int(match.group(1)),)).fetchone()

    def by_doi(self, value):
        return self.db.execute('SELECT * FROM references_catalog WHERE doi=? ORDER BY id', (norm_doi(value),)).fetchall()

    def register(self, *, doi='', title, year='', authors=None, meta=None, origin, zotero_server=None,
                 zotero_libtype=None, zotero_libid=None, zotero_key=None, match_id=None):
        doi = norm_doi(doi)
        authors = list(authors or [])
        match = self.by_alias(str(match_id)) if match_id is not None else None
        if match_id is not None and match is None:
            raise CatalogError('Codice locale da aggiornare inesistente')
        if match is None and zotero_key:
            match = self.db.execute('''SELECT * FROM references_catalog WHERE
              zotero_server=? AND zotero_libtype=? AND zotero_libid=? AND zotero_key=?''',
              (zotero_server, zotero_libtype, str(zotero_libid), str(zotero_key).upper())).fetchone()
        if match is None and doi:
            pool = self.by_doi(doi)
            # If duplicates with same DOI exist, they remain distinct (no silent merging).
            if len(pool) == 1:
                candidate = pool[0]
                # Do not overwrite a link to another existing item in the same Zotero database.
                if not zotero_key or not candidate['zotero_key'] or (candidate['zotero_server'] == zotero_server and candidate['zotero_key'] == zotero_key):
                    match = candidate
        if match is not None and match['doi'] and doi and match['doi'] != doi:
            raise CatalogError('Tentativo di cambiare il DOI di un alias esistente')
        fields = (doi or None, str(title), str(year), json.dumps(authors, ensure_ascii=False),
                  json.dumps(meta or {}, ensure_ascii=False), origin,
                  zotero_server, zotero_libtype, str(zotero_libid) if zotero_libid is not None else None,
                  str(zotero_key).upper() if zotero_key else None, now())
        if match:
            # When reindexing an item, update all metadata. Never change its alias.
            self.db.execute('''UPDATE references_catalog SET doi=?, title=?, year=?, authors=?,
              meta_json=?, origin=?, zotero_server=?, zotero_libtype=?, zotero_libid=?,
              zotero_key=?, updated_at=? WHERE id=?''', fields + (match['id'],))
            ident = match['id']
        else:
            cur = self.db.execute('''INSERT INTO references_catalog
              (doi,title,year,authors,meta_json,origin,zotero_server,zotero_libtype,zotero_libid,zotero_key,created_at,updated_at)
              VALUES (?,?,?,?,?,?,?,?,?,?,?,?)''', fields[:-1] + (now(), fields[-1]))
            ident = cur.lastrowid
        self.db.commit()
        return self.by_alias(str(ident))

    def ingest_zotero(self, library, server_id):
        items = {}
        for pool in library.by_key.values():
            for info in pool:
                items[(info['libtype'], info['libid'], info['key'])] = info
        count = 0
        for info in items.values():
            d = info['item'].get('data') or {}
            creators = d.get('creators') or []
            authors = [{'given': c.get('firstName',''), 'family':c.get('lastName') or c.get('name','')} for c in creators if c.get('creatorType') == 'author']
            prior = self.by_doi(info['doi']) if info['doi'] else []
            meta = {'zotero_data': d}
            if len(prior) == 1:
                old = json.loads(prior[0]['meta_json'] or '{}')
                meta.update({k: v for k,v in old.items() if k not in ('zotero_data',)})
            self.register(doi=info['doi'], title=info['title'] or '[Senza titolo]',year=info['year'],
                          authors=authors, meta=meta, origin='zotero',
                          zotero_server=server_id, zotero_libtype=info['libtype'],
                          zotero_libid=info['libid'], zotero_key=info['key'])
            count += 1
        return count

    def all(self, limit=30, query=None):
        if query:
            rows = self.db.execute('SELECT * FROM references_catalog WHERE title LIKE ? OR doi LIKE ? ORDER BY id LIMIT ?',
                                   (f'%{query}%', f'%{query}%', limit))
        else:
            rows = self.db.execute('SELECT * FROM references_catalog ORDER BY id LIMIT ?', (limit,))
        return list(rows)


def fetch_crossref(doi):
    doi = norm_doi(doi)
    if not re.match(r'^10\.\d{4,9}/\S+$', doi):
        raise CatalogError('DOI non valido: ' + doi)
    url = 'https://api.crossref.org/works/' + quote(doi, safe='/')
    request = Request(url, headers={'User-Agent':'ZoteroAutoCite/0.3 (research metadata); Python urllib', 'Accept':'application/json'})
    try:
        with urlopen(request, timeout=20) as resp:
            entry = json.loads(resp.read().decode('utf-8')).get('message') or {}
    except HTTPError as exc:
        raise CatalogError(f'Crossref HTTP {exc.code}: impossibile recuperare il DOI {doi}') from exc
    except (URLError, TimeoutError, ValueError) as exc:
        raise CatalogError(f'Crossref non raggiungibile o risposta non valida: {exc}') from exc
    title = (entry.get('title') or [''])[0] if isinstance(entry.get('title'), list) else entry.get('title','')
    if not title:
        raise CatalogError('Crossref non fornisce un titolo; importazione sospesa')
    raw_authors = entry.get('author') or []
    authors = [{'given':x.get('given',''), 'family':x.get('family') or x.get('name','')} for x in raw_authors]
    y = entry.get('published') or entry.get('published-print') or entry.get('issued') or {}
    parts = y.get('date-parts') or []
    year = str(parts[0][0]) if parts and parts[0] else ''
    result = {'DOI':doi,'title':title,'authors':authors,'year':year,
              'container-title': (entry.get('container-title') or [''])[0],
              'volume':entry.get('volume',''),'issue':entry.get('issue',''),
              'page':entry.get('page',''),'publisher':entry.get('publisher',''),
              'type':entry.get('type',''),'URL':entry.get('URL','')}
    return result


def search_crossref(query, limit=8):
    """Query public Crossref search; user explicitly picks a candidate DOI."""
    if len(query.strip()) < 4:
        raise CatalogError('Digita almeno quattro caratteri del titolo o degli autori')
    params = urlencode({'query.bibliographic':query.strip(), 'rows':min(15,max(1,limit))})
    request = Request('https://api.crossref.org/works?' + params,
                      headers={'User-Agent':'ZoteroAutoCite/0.3 (research metadata)', 'Accept':'application/json'})
    try:
        with urlopen(request,timeout=20) as resp:
            entries=json.loads(resp.read().decode('utf-8')).get('message',{}).get('items',[])
    except (HTTPError,URLError,TimeoutError,ValueError) as exc:
        raise CatalogError('Ricerca Crossref non disponibile: '+str(exc)) from exc
    results=[]
    for entry in entries:
        if not entry.get('DOI'):
            continue
        title=entry.get('title') or ['']
        title=title[0] if isinstance(title,list) else title
        parts=(entry.get('published') or entry.get('issued') or {}).get('date-parts') or []
        year=str(parts[0][0]) if parts and parts[0] else ''
        results.append({'doi':norm_doi(entry['DOI']),'title':title,'year':year})
    return results


def interactive_search(catalog, query, input_fn=input, print_fn=print):
    candidates=search_crossref(query)
    if not candidates:
        print_fn('Nessuna corrispondenza con DOI su Crossref')
        return None
    print_fn('\nPossibili articoli (verifica sempre titolo, autore e anno):')
    for idx, x in enumerate(candidates,1):
        print_fn(f" {idx}. [{x['year']}] {x['title'][:115]}\n    DOI: {x['doi']}")
    chosen=input_fn('\nSeleziona un numero (0 per annullare): ').strip()
    if not chosen.isdigit() or int(chosen)==0:
        print_fn('Nessun articolo selezionato')
        return None
    index=int(chosen)-1
    if index<0 or index>=len(candidates):
        raise CatalogError('Numero fuori elenco')
    row,new=add_doi(catalog,candidates[index]['doi'])
    print_fn(f"\nCodice assegnato: {catalog.alias(row['id'])} | {row['title']}")
    return row


def add_doi(catalog, doi):
    existing = catalog.by_doi(doi)
    if len(existing) == 1:
        return existing[0], False
    if len(existing) > 1:
        raise CatalogError('DOI duplicato nel catalogo: verifica gli elementi già salvati, nessuna scelta automatica')
    data = fetch_crossref(doi)
    row = catalog.register(doi=data['DOI'], title=data['title'], year=data['year'],
                           authors=data['authors'], meta=data, origin='crossref')
    return row, True


class ZoteroWriter:
    """Uses documented Zotero 10+ API. Does not persist write key or touch SQLite."""
    def __init__(self, server_base=BASE):
        self.base = server_base.rstrip('/')
        self.server_id = None
        self.key = None
        self.item_templates = {}

    def request(self, path='/', method='GET', payload=None, params=None, write=False, token=False):
        path = '/' + path.lstrip('/')
        url = self.base + path + ('?' + urlencode(params) if params else '')
        headers = {'Accept':'application/json','Zotero-API-Version':'3'}
        if self.server_id:
            headers['Zotero-Server-ID'] = self.server_id
        if payload is not None:
            headers['Content-Type'] = 'application/json'
        if write:
            if not self.server_id:
                raise CatalogError('Zotero-Server-ID non verificato, scrittura rifiutata')
            if not self.key:
                self.authorize()
            headers['Zotero-API-Key'] = self.key
            if token:
                headers['Zotero-Write-Token'] = uuid.uuid4().hex
        data = json.dumps(payload, ensure_ascii=False).encode('utf-8') if payload is not None else None
        req = Request(url, data=data, method=method, headers=headers)
        try:
            with urlopen(req, timeout=65 if write else 20) as r:
                raw = r.read()
                if path == '/' and not self.server_id:
                    self.server_id = r.headers.get('Zotero-Server-ID')
                if not raw:
                    return None
                try:
                    return json.loads(raw.decode('utf-8'))
                except (ValueError,UnicodeDecodeError):
                    if path == '/':
                        return None  # Bare /api/ response is used only for headers.
                    raise CatalogError('Risposta JSON Zotero non valida: '+path)
        except HTTPError as exc:
            # Authorization may expire; retry one time after explicit user approval.
            if exc.code == 401 and write:
                self.key = None
                return self._retry_after_auth(path, method, payload, params, token)
            raise CatalogError(f'Zotero API HTTP {exc.code} per {method} {path}: {exc.read().decode("utf-8",errors="replace")[:350]}') from exc
        except (URLError, TimeoutError) as exc:
            raise CatalogError('Connessione locale Zotero non disponibile: '+str(exc)) from exc

    def _retry_after_auth(self,path,method,payload,params,token):
        self.authorize()
        return self.request(path,method,payload,params,write=True,token=token)

    def connect(self):
        # Bare GET is required before any authorization/write.
        self.request('/')
        if not self.server_id:
            raise CatalogError('Zotero non espone Server-ID: necessaria versione Zotero 10+ per la scrittura locale')
        return self.server_id

    def authorize(self):
        if not self.server_id:
            self.connect()
        req = Request(self.base+'/local/authorize', data=json.dumps({'appName':'Zotero AutoCite'}).encode(),
                      headers={'Content-Type':'application/json', 'Zotero-Server-ID':self.server_id},method='POST')
        try:
            with urlopen(req,timeout=90) as r:
                data=json.loads(r.read().decode())
        except HTTPError as exc:
            if exc.code == 403:
                raise CatalogError('Autorizzazione scrittura negata da Zotero') from exc
            raise CatalogError(f'Autorizzazione Zotero fallita (HTTP {exc.code})') from exc
        self.key=data.get('key')
        if not self.key:
            raise CatalogError('Autorizzazione non concessa')

    def collections(self):
        rows = self.request('/users/0/collections')
        if not isinstance(rows,list):
            raise CatalogError('Elenco raccolte Zotero non valido')
        return rows

    def ensure_collection(self, collection_key):
        rows=self.collections()
        match = [r for r in rows if (r.get('key') or (r.get('data') or {}).get('key')) == collection_key]
        if len(match)!=1:
            raise CatalogError('Raccolta Zotero non trovata o non selezionata: '+str(collection_key))
        return match[0]

    # Zotero's *local* API does not necessarily expose GET /items/new,
    # although that route is documented for the public Web API. Creation
    # accepts a partial editable item in POST /users/0/items. Build a small
    # schema-controlled payload rather than depending on the template route.
    WRITABLE_FIELDS = {
        'journalArticle': frozenset(('title', 'date', 'DOI', 'publicationTitle',
                                     'volume', 'issue', 'pages', 'url')),
        'book': frozenset(('title', 'date', 'publisher', 'url')),
        'bookSection': frozenset(('title', 'date', 'bookTitle', 'pages',
                                  'publisher', 'url')),
        'report': frozenset(('title', 'date', 'institution', 'url')),
    }

    def template(self, item_type):
        if item_type not in self.WRITABLE_FIELDS:
            raise CatalogError('Tipo Zotero non supportato per importazione: ' + item_type)
        return {'itemType': item_type, 'creators': [], 'collections': [],
                'tags': [], 'relations': {}}

    def create_item(self, record, collection_key):
        self.ensure_collection(collection_key)
        if not record['doi']:
            meta = json.loads(record['meta_json'] or '{}')
            # A DOI-less item can be imported only if explicitly selected via OpenAlex.
            if not record['openalex_id'] or meta.get('verification') != 'OPENALEX_ONLY':
                raise CatalogError('Fonte senza DOI: serve un ID OpenAlex selezionato e metadati sufficienti')
            if not record['title'] or not record['year'] or not json.loads(record['authors']):
                raise CatalogError('Fonte senza DOI e metadati incompleti: importazione sospesa')
        raw = json.loads(record['meta_json'])
        original_zotero = raw.get('zotero_data') or {}
        kind = raw.get('type')
        if not kind and original_zotero:
            kind = {'book':'book','bookSection':'book-chapter'}.get(original_zotero.get('itemType'),'journal-article')
        zotero_type = ('book' if kind in ('book','monograph') else 'bookSection' if kind in ('book-chapter','book-section')
                       else 'report' if kind in ('report','preprint','working-paper') else 'journalArticle')
        item = self.template(zotero_type)
        # Explicit allowlist per item type: no remote /items/new template call.
        fields = {
          'title': record['title'], 'date': record['year'], 'DOI': record['doi'] or '',
          'publicationTitle': raw.get('container-title') or original_zotero.get('publicationTitle',''),
          'bookTitle': raw.get('container-title') or original_zotero.get('bookTitle',''),
          'volume': raw.get('volume') or original_zotero.get('volume',''),
          'issue': raw.get('issue') or original_zotero.get('issue',''),
          'pages': raw.get('page') or original_zotero.get('pages',''),
          'publisher': raw.get('publisher') or original_zotero.get('publisher',''),
          'institution': raw.get('publisher') or original_zotero.get('institution',''),
          'url': raw.get('URL') or original_zotero.get('url','')}
        for name, value in fields.items():
            if name in self.WRITABLE_FIELDS[zotero_type] and value:
                item[name] = str(value)
        item['creators']=[{'creatorType':'author',
                           'firstName':a.get('given',''), 'lastName':a.get('family','')}
                          for a in json.loads(record['authors']) if a.get('family')]
        item['collections']=[collection_key]
        result=self.request('/users/0/items', method='POST', payload=[item], write=True,token=True)
        success=(result or {}).get('success',{})
        if '0' not in success:
            raise CatalogError('Zotero ha rifiutato la creazione: ' + str((result or {}).get('failed',result)))
        key=success['0']
        return self.request('/users/0/items/'+key)

    def add_to_collection(self, info, collection_key):
        self.ensure_collection(collection_key)
        if info['libtype']!='user':
            raise CatalogError('Non è possibile spostare riferimenti di librerie di gruppo nella raccolta personale')
        key=info['key']
        for attempt in range(2):
            actual=self.request('/users/0/items/'+key)
            data=actual.get('data') or {}
            collections=data.get('collections') or []
            if collection_key in collections:
                return False
            new=list(dict.fromkeys([*collections,collection_key]))
            try:
                # PATCH leaves every other metadata field unmodified. Existing collections preserved.
                self.request('/users/0/items/'+key, method='PATCH', payload={'collections':new,'version':actual['version']},write=True)
                return True
            except CatalogError as exc:
                if '412' not in str(exc) or attempt:
                    raise
        return False


def choose_collection(writer, settings_file=DEFAULT_SETTINGS, input_fn=input, print_fn=print):
    writer.connect()
    rows=writer.collections()
    by_key={x.get('key') or x.get('data',{}).get('key'):x for x in rows}
    if not rows:
        raise CatalogError('Crea prima una raccolta in Zotero, poi ripeti la selezione')
    print_fn('\nRaccolte disponibili nella libreria personale:')
    for i,x in enumerate(rows,1):
        print_fn(f" {i:>3}. {(x.get('data') or {}).get('name','(senza nome)')} | {x.get('key')}" )
    text=input_fn('\nInserisci il numero della raccolta destinataria: ').strip()
    if not text.isdigit() or not 1<=int(text)<=len(rows):
        raise CatalogError('Scelta annullata o non valida')
    entry=rows[int(text)-1]
    key=entry.get('key') or (entry.get('data') or {}).get('key')
    store = {'server_id':writer.server_id, 'collection_key':key,
             'collection_name':(entry.get('data') or {}).get('name',''), 'saved_at':now()}
    settings_file=Path(settings_file)
    settings_file.parent.mkdir(parents=True, exist_ok=True)
    settings_file.write_text(json.dumps(store,ensure_ascii=False,indent=2),encoding='utf-8')
    print_fn('\nRaccolta selezionata:',store['collection_name'],f'[{key}]')
    return key


def selected_collection(writer, settings_file=DEFAULT_SETTINGS):
    path=Path(settings_file)
    if not path.exists():
        return None
    info=json.loads(path.read_text(encoding='utf-8'))
    if not writer.server_id:
        writer.connect()
    if info.get('server_id') != writer.server_id:
        raise CatalogError('Il database Zotero è cambiato. Riseleziona la raccolta di destinazione.')
    key=info.get('collection_key')
    if key:
        writer.ensure_collection(key)
    return key


class CatalogResolver(LocalZotero):
    """Resolver for [[Z:xxxxx]]. Imports on demand only when requested by --auto-import.
    A missing reference is not silently turned into a new Zotero item.
    """
    def __init__(self, catalog, auto_import=False, group_ids=None, settings_file=DEFAULT_SETTINGS):
        super().__init__(group_ids=group_ids)
        self.catalog = catalog
        self.auto_import = auto_import
        self.settings_file = settings_file
        self.writer = None
        self.server_id = None
        self.actions=[]
        # Do not repeat a failed write for each occurrence of the same alias.
        self.failed_imports={}

    def load(self):
        self.writer=ZoteroWriter()
        try:
            self.server_id=self.writer.connect()
        except CatalogError as exc:
            # Keep the tested read-only conversion working with older Zotero clients.
            if 'Zotero-Server-ID' not in str(exc):
                raise
            self.server_id=None
            self.writer=None
        return super().load()

    def find(self, type_, value, label=None):
        if type_.lower()!='alias':
            return super().find(type_,value,label)
        entry=self.catalog.by_alias(value)
        if entry is None:
            return 'CODICE_SCONOSCIUTO',None,'Alias non registrato nel catalogo AutoCite'
        doi=entry['doi']
        # Avoid selecting one of multiple Zotero items with the same DOI.
        matches = self.by_doi.get(doi,[]) if doi else []
        if not matches and entry['zotero_key'] and entry['zotero_server']==self.server_id:
            matches=[i for i in self.by_key.get(entry['zotero_key'].upper(),[]) if i['libtype']==entry['zotero_libtype'] and str(i['libid'])==str(entry['zotero_libid'])]
        if len(matches)>1:
            return 'AMBIGUA',None,'DOI presente più volte in Zotero: verifica i duplicati'
        if matches:
            info=matches[0]
            # Explicitly selected destination also receives existing personal items,
            # without removing them from their current collections.
            if self.auto_import and info['libtype']=='user' and self.writer:
                try:
                    collection=selected_collection(self.writer,self.settings_file)
                    if collection and self.writer.add_to_collection(info,collection):
                        self.actions.append(('AGGIUNTA_A_RACCOLTA',self.catalog.alias(entry['id']),info['key']))
                        return 'TROVATA',info,'Elemento Zotero esistente aggiunto alla raccolta scelta'
                except CatalogError as exc:
                    return 'IMPORTAZIONE_FALLITA',None,str(exc)
            return 'TROVATA',info,''
        if self.auto_import and entry['id'] in self.failed_imports:
            return 'IMPORTAZIONE_FALLITA', None, self.failed_imports[entry['id']]
        if self.auto_import:
            # We cannot safely deduplicate by DOI when an existing Zotero record
            # has no DOI. Block instead of silently making a second copy.
            from autocite_openalex import normalize_title
            title = normalize_title(entry['title'])
            year = str(entry['year'] or '')
            possible = {}
            if title and year:
                for pool in self.by_key.values():
                    for candidate in pool:
                        if candidate['libtype'] != 'user':
                            continue
                        if candidate['year'] == year and normalize_title(candidate['title']) == title:
                            possible[candidate['key']] = candidate
            if possible:
                return 'POSSIBILE_DUPLICATO', None, ('Titolo e anno identici in Zotero: ' +
                    ', '.join(sorted(possible)) + '. Verifica/aggiungi DOI a Zotero e sincronizza nuovamente.')
        if not self.auto_import:
            return 'NON_IN_ZOTERO',None,'Record nel catalogo ma non in Zotero. Abilitare --auto-import dopo aver scelto la raccolta.'
        if not self.writer or not self.server_id:
            return 'ERRORE',None,'Zotero 10+ necessario per importazione automatica tramite API locale' 
        try:
            collection=selected_collection(self.writer,self.settings_file)
            if not collection:
                return 'RACCOLTA_NON_SCELTA',None,'Usa Configura_Raccolta.bat per scegliere la raccolta di destinazione.'
            obj=self.writer.create_item(entry,collection)
            info=item_info(obj)
            if not info['uri']:
                return 'METADATI_INCOMPLETI',None,'URI dell’articolo importato mancante'
            self.by_key[info['key']].append(info)
            if info['doi']:
                self.by_doi[info['doi']].append(info)
            self.catalog.register(doi=info['doi'],title=info['title'],year=info['year'],
                                  authors=json.loads(entry['authors']),meta=json.loads(entry['meta_json']),
                                  origin=entry['origin'],zotero_server=self.server_id,
                                  zotero_libtype=info['libtype'],zotero_libid=info['libid'],zotero_key=info['key'],
                                  match_id=entry['id'])
            self.actions.append(('IMPORTATA',self.catalog.alias(entry['id']),info['key']))
            return 'TROVATA',info,'Articolo importato in Zotero nella raccolta scelta'
        except (CatalogError,ZoteroError) as exc:
            self.failed_imports[entry['id']] = str(exc)
            return 'IMPORTAZIONE_FALLITA',None,str(exc)


def ingest_bib(catalog,file):
    try:
        import bibtexparser
    except ImportError as exc:
        raise CatalogError('Per importare BibTeX esegui: py -m pip install -r requirements.txt') from exc
    with open(file,encoding='utf-8-sig') as f:
        bib=bibtexparser.load(f)
    accepted=[]; rejected=[]
    for entry in bib.entries:
        doi=norm_doi(entry.get('doi'))
        if not doi:
            rejected.append((entry.get('ID','?'),'DOI assente: non importato nel catalogo di questa versione'))
            continue
        if catalog.by_doi(doi):
            accepted.append((entry.get('ID','?'),catalog.alias(catalog.by_doi(doi)[0]['id']),'già presente'))
            continue
        authors=[]
        for a in re.split(r'\s+and\s+',entry.get('author',''),flags=re.I):
            if ',' in a:
                family,given=a.split(',',1)
            else:
                words=a.split(); family=words[-1] if words else ''; given=' '.join(words[:-1])
            if family.strip():
                authors.append({'given':given.strip(),'family':family.strip()})
        clean=lambda s: str(s or '').strip().strip('{}')
        title=clean(entry.get('title'))
        if not title:
            rejected.append((entry.get('ID','?'),'Titolo assente'))
            continue
        meta={'DOI':doi,'title':title,'year':entry.get('year',''), 'authors':authors,
              'container-title':clean(entry.get('journal') or entry.get('booktitle')),
              'volume':entry.get('volume',''), 'issue':entry.get('number',''),
              'page':entry.get('pages',''),'type':'journal-article'}
        row=catalog.register(doi=doi,title=title,year=entry.get('year',''),authors=authors,meta=meta,origin='bibtex')
        accepted.append((entry.get('ID','?'),catalog.alias(row['id']),'importato'))
    return accepted,rejected


def main(argv=None):
    parser=argparse.ArgumentParser(description='Catalogo di articoli e alias compatti Zotero AutoCite (gratuito)')
    parser.add_argument('--catalog',type=Path,default=DEFAULT_DB,help='Database catalogo persistente SQLite')
    sub=parser.add_subparsers(dest='command',required=True)
    sub.add_parser('sync',help='Indicizza le voci Zotero e assegna codici brevi, senza modificare Zotero')
    p=sub.add_parser('add-doi',help='Aggiunge un DOI al catalogo via Crossref (senza importarlo ancora in Zotero)')
    p.add_argument('doi')
    p=sub.add_parser('import-bib',help='Registra DOI e metadati di un file BibTeX')
    p.add_argument('file',type=Path)
    p=sub.add_parser('search',help='Cerca per DOI esatto oppure titolo/autore su OpenAlex e verifica con Crossref')
    p.add_argument('query',nargs='?',default='')
    p=sub.add_parser('search-crossref',help='Ricerca alternativa soltanto su Crossref')
    p.add_argument('query',nargs='?',default='')
    p=sub.add_parser('add-openalex',help='Registra un ID OpenAlex W... (verifica DOI con Crossref)')
    p.add_argument('work_id',nargs='?',default='')
    p=sub.add_parser('batch',help='Aggiunge DOI da file TXT o CSV, uno per riga; CSV con colonna DOI')
    p.add_argument('file',type=Path)
    p=sub.add_parser('list',help='Mostra i codici brevi (eventuale filtro)')
    p.add_argument('query',nargs='?',default='')
    p.add_argument('--limit',type=int,default=30)
    sub.add_parser('choose-collection',help='Seleziona la raccolta Zotero personale in cui importare')
    p=sub.add_parser('export-csv',help='Esporta tutti i codici brevi e metadati in CSV per Excel')
    p.add_argument('file',nargs='?',type=Path,default=data_dir() / 'Catalogo_AutoCite.csv')
    args=parser.parse_args(argv)
    cat=Catalog(args.catalog)
    try:
        if args.command=='sync':
            z=LocalZotero(); n=z.load()
            w=ZoteroWriter(); sid=w.connect()
            total=cat.ingest_zotero(z,sid)
            print(f'Indicizzati {total}/{n} riferimenti Zotero nel catalogo persistente: {cat.filename}')
        elif args.command=='add-doi':
            row,new=add_doi(cat,args.doi)
            print(cat.alias(row['id']), '|',row['title'],'|',('aggiunto' if new else 'già presente'))
        elif args.command=='search':
            from autocite_openalex import interactive_openalex, interactive_doi, is_doi_query
            query = args.query or input('DOI (consigliato), titolo o autore da cercare: ').strip()
            if is_doi_query(query):
                interactive_doi(cat, query)
            else:
                interactive_openalex(cat, query)
        elif args.command=='search-crossref':
            interactive_search(cat, args.query or input('Titolo o autore da cercare in Crossref: ').strip())
        elif args.command=='add-openalex':
            from autocite_openalex import add_selected_id
            entry = add_selected_id(cat, args.work_id or input('ID OpenAlex W...: ').strip())
            print(cat.alias(entry['id']), '|',entry['title'],'|',entry['openalex_id'])
        elif args.command=='import-bib':
            accepted, rejected=ingest_bib(cat,args.file)
            for bibid,alias,status in accepted:
                print(f'{bibid}: {alias} ({status})')
            for bibid,reason in rejected:
                print(f'NON IMPORTATO {bibid}: {reason}')
            print(f'{len(accepted)} identificati, {len(rejected)} esclusi')
        elif args.command=='batch':
            txt=args.file.read_text(encoding='utf-8-sig')
            if args.file.suffix.lower()=='.csv':
                dialect=csv.Sniffer().sniff(txt[:4096],delimiters=',;\t')
                reader=csv.DictReader(txt.splitlines(),dialect=dialect)
                dois=[(r.get('DOI') or r.get('doi') or '').strip() for r in reader]
            else:
                dois=[x.strip() for x in txt.splitlines() if x.strip()]
            for doi in dois:
                try:
                    row,new=add_doi(cat,doi)
                    print(cat.alias(row['id']),doi,('aggiunto' if new else 'già presente'))
                except CatalogError as exc:
                    print('NON RISOLTO',doi,str(exc))
        elif args.command=='list':
            for row in cat.all(args.limit,args.query):
                print(f"{cat.alias(row['id'])} | {row['year'] or 's.d.'} | {row['title'][:90]} | {row['doi'] or 'senza DOI'}")
            print('Catalogo:',cat.filename)
        elif args.command=='choose-collection':
            choose_collection(ZoteroWriter())
        elif args.command=='export-csv':
            args.file.parent.mkdir(parents=True,exist_ok=True)
            with args.file.open('w',encoding='utf-8-sig',newline='') as file:
                writer=csv.writer(file,delimiter=';')
                writer.writerow(['Codice','Autori','Anno','Titolo','DOI','OpenAlex ID','Verifica','Origine','Chiave Zotero'])
                for row in cat.db.execute('SELECT * FROM references_catalog ORDER BY id'):
                    authors=json.loads(row['authors'] or '[]')
                    author_text='; '.join(a.get('family') or '' for a in authors)
                    writer.writerow([cat.alias(row['id']),author_text,row['year'],row['title'],row['doi'],row['openalex_id'],json.loads(row['meta_json'] or '{}').get('verification',''),row['origin'],row['zotero_key']])
            print('Catalogo CSV Excel:',args.file)
        return 0
    except (CatalogError,ZoteroError,OSError,ValueError) as exc:
        print('ERRORE:',exc,file=sys.stderr)
        return 2
    except Exception as exc:
        from autocite_openalex import SourceError
        if not isinstance(exc, SourceError):
            raise
        print('ERRORE:',exc,file=sys.stderr)
        return 2
    finally:
        cat.close()

if __name__=='__main__':
    raise SystemExit(main())
