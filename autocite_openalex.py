#!/usr/bin/env python3
"""OpenAlex-first discovery + Crossref DOI verification for Zotero AutoCite.

Only the selected publication is saved to the small local SQLite registry.
Never trusts an arbitrary search hit or silently imports a result into Zotero.
No paid service, scraping, direct writes to Zotero's database, or PDF downloads.
"""
from __future__ import annotations

import json
import os
import re
import time
import unicodedata
from difflib import SequenceMatcher
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

OPENALEX = 'https://api.openalex.org'
CROSSREF = 'https://api.crossref.org'
USER_AGENT = 'ZoteroAutoCite/0.4 (local open bibliography manager; Python urllib)'

class SourceError(RuntimeError):
    pass


def doi_normalize(doi):
    doi = str(doi or '').strip().lower()
    doi = re.sub(r'^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)', '', doi)
    return doi.strip().rstrip('.,;')


def openalex_id(value):
    raw = str(value or '').strip()
    m = re.fullmatch(r'(?:https?://(?:www\.)?openalex\.org/)?(W\d+)', raw, re.I)
    if not m:
        raise SourceError('Identificativo OpenAlex non valido: atteso W seguito da cifre')
    return m.group(1).upper()


def request_json(base, endpoint, params=None, timeout=20):
    if not base.startswith('https://'):
        raise SourceError('Origine API non attendibile')
    url = base + endpoint
    if params:
        url += '?' + urlencode(params)
    request = Request(url, headers={'User-Agent': USER_AGENT, 'Accept': 'application/json'})
    for attempt in range(3):
        try:
            with urlopen(request, timeout=timeout) as response:
                return json.loads(response.read().decode('utf-8'))
        except HTTPError as exc:
            if exc.code == 404:
                raise SourceError(f'Record inesistente su {base} (HTTP 404)') from exc
            if exc.code == 429 and attempt < 2:
                retry = exc.headers.get('Retry-After', '2')
                try:
                    delay = min(float(retry), 3.0)
                except ValueError:
                    delay = 2.0
                time.sleep(max(0.5, delay))
                continue
            raise SourceError(f'API {base}: HTTP {exc.code}; riprovare o controllare le quote') from exc
        except (URLError, TimeoutError, ValueError, UnicodeDecodeError) as exc:
            raise SourceError(f'Connessione o risposta non valida da {base}: {exc}') from exc
    raise SourceError(f'API {base}: limite richieste, nessun dato salvato')


class OpenAlexClient:
    def __init__(self, api_key=None):
        self.api_key = api_key if api_key is not None else os.environ.get('OPENALEX_API_KEY', '')

    def params(self, extras=None):
        payload = dict(extras or {})
        if self.api_key:
            payload['api_key'] = self.api_key
        return payload

    def search(self, text, limit=8):
        if len(text.strip()) < 4:
            raise SourceError('Inserisci almeno 4 caratteri per cercare in OpenAlex')
        result = request_json(OPENALEX, '/works', self.params({'search': text.strip(), 'per_page': min(max(limit,1),15)}))
        results = result.get('results') if isinstance(result, dict) else None
        if not isinstance(results, list):
            raise SourceError('La ricerca OpenAlex ha restituito una risposta inattesa')
        return [item for item in results if isinstance(item, dict) and item.get('id') and item.get('display_name')]

    def get(self, identifier):
        wid = openalex_id(identifier)
        item = request_json(OPENALEX, '/works/' + wid, self.params())
        if not isinstance(item, dict) or openalex_id(item.get('id', '')) != wid:
            raise SourceError('Record OpenAlex mancante o identificativo non coerente')
        return item

    def by_doi(self, doi):
        canonical = doi_normalize(doi)
        if not re.fullmatch(r'10\.\d{4,9}/\S+', canonical):
            raise SourceError('DOI non valido')
        return request_json(OPENALEX, '/works/doi:' + quote(canonical, safe='/'), self.params())


class CrossrefClient:
    def get(self, doi):
        canonical = doi_normalize(doi)
        if not re.fullmatch(r'10\.\d{4,9}/\S+', canonical):
            raise SourceError('DOI non valido: ' + canonical)
        result = request_json(CROSSREF, '/works/' + quote(canonical, safe='/'))
        message = result.get('message') if isinstance(result, dict) else None
        if not isinstance(message, dict):
            raise SourceError('Metadati Crossref non validi')
        return message


def normalize_title(value):
    value = re.sub(r'<[^>]*>', ' ', str(value or ''))
    text = unicodedata.normalize('NFKD', value).casefold().replace('&',' and ')
    text = ''.join(c for c in text if not unicodedata.combining(c))
    return ' '.join(re.findall(r'[\w]+', text))


def main_author(name):
    return normalize_title(name).split()[-1] if normalize_title(name) else ''


def crossref_year(entry):
    for key in ('published', 'published-print', 'published-online', 'issued', 'created'):
        parts = (entry.get(key) or {}).get('date-parts') or []
        if parts and parts[0] and isinstance(parts[0][0], int):
            return str(parts[0][0])
    return ''


def crossref_title(entry):
    titles = entry.get('title') or []
    return str(titles[0] if isinstance(titles, list) and titles else titles or '')


def extract_openalex(work):
    wid = openalex_id(work.get('id'))
    doi = doi_normalize(work.get('doi'))
    year = str(work.get('publication_year') or '')
    title = work.get('display_name') or work.get('title') or ''
    authors = []
    for row in work.get('authorships') or []:
        author = row.get('author') or {}
        name = str(author.get('display_name') or '').strip()
        if not name:
            continue
        # OpenAlex provides display_name, not structured given/family names.
        # Parsing is only a fallback; validated Crossref names take precedence.
        if ',' in name:
            family,given = name.split(',',1)
        else:
            pieces = name.split()
            family = pieces[-1]
            given = ' '.join(pieces[:-1])
        authors.append({'family':family.strip(), 'given':given.strip()})
    source = (((work.get('primary_location') or {}).get('source') or {}).get('display_name') or '')
    meta = {'DOI': doi, 'title': title, 'year': year, 'authors': authors,
            'container-title': source, 'volume': str((work.get('biblio') or {}).get('volume') or ''),
            'issue': str((work.get('biblio') or {}).get('issue') or ''),
            'page': '-'.join(str((work.get('biblio') or {}).get(x) or '') for x in ['first_page','last_page']).strip('-'),
            'type': work.get('type') or 'article', 'URL':work.get('doi') or work.get('id') or '',
            'openalex_id': wid, 'verification':'OPENALEX_ONLY', 'origin':'openalex'}
    if not title or not year or not authors:
        raise SourceError('Metadati OpenAlex insufficienti (titolo, anno o autori): importazione sospesa')
    if not re.fullmatch(r'(19|20)\d{2}', year):
        raise SourceError('Anno OpenAlex non valido: importazione sospesa')
    return meta


def verify_crossref(openalex_meta, crossref):
    """Fail closed on inconsistent identity; published vs online year can differ by 1."""
    cdoi = doi_normalize(crossref.get('DOI'))
    if cdoi != openalex_meta['DOI']:
        raise SourceError('DOI OpenAlex/Crossref differenti: verifica manuale necessaria')
    title = crossref_title(crossref)
    a, b = normalize_title(openalex_meta['title']), normalize_title(title)
    ratio = SequenceMatcher(None, a, b).ratio() if a and b else 0
    if ratio < 0.79:
        raise SourceError(f'Titoli discordanti OpenAlex/Crossref (similarità {ratio:.0%}); nessun salvataggio')
    cyear = crossref_year(crossref)
    oyear = openalex_meta['year']
    if cyear and abs(int(cyear)-int(oyear)) > 1:
        raise SourceError(f'Anno discordante OpenAlex {oyear}, Crossref {cyear}; nessun salvataggio')
    cr_authors = crossref.get('author') or []
    oa_authors = openalex_meta['authors']
    if cr_authors and oa_authors:
        ca = main_author(str(cr_authors[0].get('family') or cr_authors[0].get('name') or ''))
        oa = main_author(oa_authors[0]['family'])
        if ca and oa and (ca != oa) and SequenceMatcher(None, ca, oa).ratio() < .8:
            raise SourceError(f'Primo autore discordante OpenAlex ({oa}) / Crossref ({ca}); nessun salvataggio')
    result = dict(openalex_meta)
    result['title'] = title or result['title']
    # Use Crossref bibliographic year when available.
    result['year'] = cyear or result['year']
    if cr_authors:
        result['authors'] = [{'family': str(a.get('family') or a.get('name') or ''),
                              'given': str(a.get('given') or '')} for a in cr_authors]
    for key, src in [('container-title','container-title'),('volume','volume'),('issue','issue'),
                     ('page','page'),('publisher','publisher'),('URL','URL'),('type','type')]:
        val = crossref.get(src)
        if isinstance(val, list):
            val = val[0] if val else ''
        if val:
            result[key] = val
    result['verification'] = 'CROSSREF_VERIFIED'
    result['crossref_title_similarity'] = round(ratio,3)
    result['origin'] = 'openalex+crossref'
    return result


def get_checked_work(identifier, *, openalex=None, crossref=None):
    """Retrieve one explicitly selected ID, do not automatically accept ranked search hits."""
    openalex = openalex or OpenAlexClient()
    crossref = crossref or CrossrefClient()
    work = openalex.get(identifier)
    meta = extract_openalex(work)
    if meta['DOI']:
        entry = crossref.get(meta['DOI'])
        meta = verify_crossref(meta, entry)
    # DOI-less works are allowed only with an explicit OpenAlex ID selection.
    return meta


def register_checked(catalog, checked):
    """Upsert without changing a pre-existing alias; never invent or pick from duplicates."""
    wid = openalex_id(checked['openalex_id'])
    already = catalog.by_openalex(wid)
    doi = doi_normalize(checked.get('DOI'))
    rows = catalog.by_doi(doi) if doi else []
    if len(rows) > 1:
        raise SourceError('DOI ambiguo nel registro locale; scegliere/risolvere manualmente')
    if already and rows and already['id'] != rows[0]['id']:
        raise SourceError('Conflitto: OpenAlex ID e DOI puntano ad alias diversi nel catalogo')
    existing = already or (rows[0] if rows else None)
    if existing and existing['doi'] and doi and existing['doi'] != doi:
        raise SourceError('Conflitto tra DOI esistente e record OpenAlex')
    if existing:
        # Preserve the canonical Zotero relationship rather than creating a new row.
        data = dict(checked)
        previous = json.loads(existing['meta_json'] or '{}')
        data.update({'zotero_data': previous.get('zotero_data', {})} if previous.get('zotero_data') else {})
        row = catalog.register(doi=doi, title=checked['title'], year=checked['year'],
                               authors=checked['authors'], meta=data, origin=checked['origin'],
                               zotero_server=existing['zotero_server'], zotero_libtype=existing['zotero_libtype'],
                               zotero_libid=existing['zotero_libid'], zotero_key=existing['zotero_key'], match_id=existing['id'])
        if row['id'] != existing['id']:
            raise SourceError('Alias imprevisto durante aggiornamento: interrompere')
    else:
        row = catalog.register(doi=doi, title=checked['title'], year=checked['year'],
                               authors=checked['authors'], meta=checked, origin=checked['origin'])
    catalog.attach_openalex(row['id'], wid)
    return catalog.by_alias(str(row['id']))


def add_selected_id(catalog, wid, openalex=None, crossref=None):
    checked = get_checked_work(wid, openalex=openalex, crossref=crossref)
    return register_checked(catalog, checked)


def is_doi_query(value):
    """Recognize DOI, doi:DOI and doi.org URLs; no fuzzy title matching."""
    canonical = doi_normalize(value)
    return bool(re.fullmatch(r'10\.\d{4,9}/\S+', canonical))


def interactive_doi(catalog, doi, input_fn=input, print_fn=print, openalex=None, crossref=None):
    """Look up a DOI exactly, verify metadata and explicitly confirm before registration.

    No Zotero writes occur here: imports only happen later when a Word file is
    converted with --auto-import and a target collection has been configured.
    """
    canonical = doi_normalize(doi)
    if not is_doi_query(doi):
        raise SourceError('DOI non valido: inserisci 10.xxxx/..., doi:10.xxxx/... oppure https://doi.org/10.xxxx/...')
    oa = openalex or OpenAlexClient()
    cr = crossref or CrossrefClient()
    meta = None
    try:
        work = oa.by_doi(canonical)
    except SourceError as exc:
        if 'HTTP 404' not in str(exc):
            raise
        # Some valid Crossref DOIs have no OpenAlex record. Do not invent an OpenAlex ID.
        print_fn('DOI non indicizzato su OpenAlex: provo il recupero esatto da Crossref.')
    else:
        meta = extract_openalex(work)
        if doi_normalize(meta.get('DOI')) != canonical:
            raise SourceError('Il DOI restituito da OpenAlex non corrisponde a quello richiesto')
        meta = verify_crossref(meta, cr.get(canonical))

    if meta is None:
        entry = cr.get(canonical)
        if doi_normalize(entry.get('DOI')) != canonical:
            raise SourceError('DOI restituito da Crossref non coerente con quello richiesto')
        title = crossref_title(entry)
        authors = [{'family': str(a.get('family') or a.get('name') or '').strip(),
                    'given': str(a.get('given') or '').strip()} for a in entry.get('author') or []]
        year = crossref_year(entry)
        if not title or not year or not authors:
            raise SourceError('Metadati Crossref insufficienti: titolo, anno o autori mancanti')
        source = entry.get('container-title') or []
        if isinstance(source, list):
            source = source[0] if source else ''
        meta = {'DOI': canonical, 'title': title, 'year': year, 'authors': authors,
                'container-title': source, 'volume':str(entry.get('volume') or ''),
                'issue':str(entry.get('issue') or ''), 'page':str(entry.get('page') or ''),
                'publisher':entry.get('publisher') or '', 'type':entry.get('type') or 'article',
                'URL': entry.get('URL') or 'https://doi.org/' + canonical,
                'verification':'CROSSREF_ONLY', 'origin':'crossref'}

    family_names = ', '.join(a.get('family') or '' for a in meta['authors'][:3])
    print_fn(f"\nFonte esatta: {meta['title']} ({meta['year']})")
    print_fn(f"Autori: {family_names}{' et al.' if len(meta['authors']) > 3 else ''}")
    print_fn(f"DOI: {canonical} | Verifica: {meta['verification']}")
    if meta.get('openalex_id'):
        print_fn(f"OpenAlex: {meta['openalex_id']}")
    answer = input_fn('Registrare questa fonte nel catalogo locale? [s/N]: ').strip().casefold()
    if answer not in ('s','si','sì','y','yes'):
        print_fn('Operazione annullata; nessun dato modificato.')
        return None
    if meta.get('openalex_id'):
        row = register_checked(catalog, meta)
    else:
        old = catalog.by_doi(canonical)
        if len(old) > 1:
            raise SourceError('DOI presente più volte nel registro: risoluzione manuale necessaria')
        if old:
            row = old[0]  # Preserve any existing Zotero relation and alias.
        else:
            row = catalog.register(doi=canonical, title=meta['title'], year=meta['year'],
                                   authors=meta['authors'], meta=meta, origin='crossref')
    print_fn(f"\nCodice: {catalog.alias(row['id'])} — {row['title']}")
    return row


def interactive_openalex(catalog, query, input_fn=input, print_fn=print, openalex=None, crossref=None):
    openalex = openalex or OpenAlexClient()
    choices = openalex.search(query)
    if not choices:
        print_fn('Nessun risultato OpenAlex. Verifica query o prova direttamente il DOI.')
        return None
    print_fn('\nRisultati OpenAlex — confronta titolo, autori, anno prima di selezionare:')
    for n, w in enumerate(choices, 1):
        name = (w.get('authorships') or [{}])[0].get('author') or {}
        print_fn(f" {n}. [{w.get('publication_year') or 's.d.'}] {w.get('display_name','')[:110]}\n"
                 f"    {name.get('display_name','')[:50]} | {w.get('doi') or 'senza DOI'} | {openalex_id(w.get('id'))}")
    answer = input_fn('\nNumero da registrare (0 = annulla): ').strip()
    if not answer.isdigit() or not 1 <= int(answer) <= len(choices):
        print_fn('Nessuna selezione, catalogo invariato.')
        return None
    wid = openalex_id(choices[int(answer)-1]['id'])
    meta = get_checked_work(wid, openalex=openalex, crossref=crossref)
    print_fn(f"\nFonte: {meta['title']} ({meta['year']})")
    print_fn(f"OpenAlex: {wid} | DOI: {meta['DOI'] or '(assente)'} | Verifica: {meta['verification']}")
    if meta['verification'] == 'OPENALEX_ONLY':
        print_fn('ATTENZIONE: fonte senza DOI. I metadati non sono stati verificati da Crossref.')
    answer = input_fn('Registrare questa fonte nel catalogo locale? [s/N]: ').strip().casefold()
    if answer not in ('s','si','sì','y','yes'):
        print_fn('Operazione annullata; nessun dato modificato.')
        return None
    row = register_checked(catalog, meta)
    print_fn(f"\nCodice: {catalog.alias(row['id'])} — {row['title']}")
    return row
