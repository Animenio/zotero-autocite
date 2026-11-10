"""Servizi senza interfaccia grafica per Zotero AutoCite Desktop 0.5.

Mantiene compatibilita' con il motore 0.4.2; non altera originali Word.
"""
from __future__ import annotations

import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from autocite_catalog import (Catalog, CatalogResolver, ZoteroWriter,
                              DEFAULT_SETTINGS, selected_collection)
from autocite_openalex import (OpenAlexClient, CrossrefClient, SourceError,
                               doi_normalize, is_doi_query, extract_openalex,
                               verify_crossref, crossref_title, crossref_year,
                               openalex_id, get_checked_work, register_checked)
from zotero_autocite import process, write_logs


def parse_doi_result(doi: str, crossref: dict) -> dict:
    """Metadati Crossref verificati rispetto al DOI chiesto (fallback OpenAlex 404)."""
    canonical = doi_normalize(doi)
    if doi_normalize(crossref.get('DOI')) != canonical:
        raise SourceError('Il DOI di Crossref non corrisponde al DOI richiesto')
    title = crossref_title(crossref)
    year = crossref_year(crossref)
    authors = [{'family': str(a.get('family') or a.get('name') or '').strip(),
                'given': str(a.get('given') or '').strip()}
               for a in crossref.get('author') or []]
    authors = [a for a in authors if a['family']]
    if not (title and year and authors):
        raise SourceError('Metadati Crossref insufficienti (titolo, anno o autori mancanti)')
    source = crossref.get('container-title') or []
    if isinstance(source, list):
        source = source[0] if source else ''
    return {'DOI': canonical, 'title': title, 'year': year, 'authors': authors,
            'container-title': source, 'volume': str(crossref.get('volume') or ''),
            'issue': str(crossref.get('issue') or ''),
            'page': str(crossref.get('page') or ''),
            'publisher': crossref.get('publisher') or '',
            'type': crossref.get('type') or 'article',
            'URL': crossref.get('URL') or 'https://doi.org/' + canonical,
            'verification': 'CROSSREF_ONLY', 'origin': 'crossref'}


def get_doi_exact(doi: str, openalex=None, crossref=None) -> dict:
    """Ricerca esatta: fallback Crossref esclusivamente per assenza OpenAlex (404)."""
    if not is_doi_query(doi):
        raise SourceError('DOI non valido: formato atteso 10.xxxx/...')
    canonical = doi_normalize(doi)
    oa = openalex or OpenAlexClient()
    cr = crossref or CrossrefClient()
    try:
        work = oa.by_doi(canonical)
    except SourceError as exc:
        if '404' not in str(exc):
            raise
        return parse_doi_result(canonical, cr.get(canonical))
    meta = extract_openalex(work)
    if doi_normalize(meta.get('DOI')) != canonical:
        raise SourceError('Il DOI OpenAlex non coincide con quello richiesto')
    return verify_crossref(meta, cr.get(canonical))


def search_publications(query: str, openalex=None, crossref=None) -> list[dict]:
    query = query.strip()
    if not query:
        raise ValueError('Inserisci un titolo, un autore oppure un DOI')
    if is_doi_query(query):
        meta = get_doi_exact(query, openalex=openalex, crossref=crossref)
        return [{'id': 'exact:' + doi_normalize(query), 'title': meta['title'],
                 'year': meta['year'], 'authors': meta['authors'], 'doi': meta['DOI'],
                 'verification': meta['verification'], 'meta': meta}]
    if re.match(r'^https?://(?:dx\.)?doi\.org/', query, flags=re.I) or re.match(r'^doi:', query, flags=re.I):
        raise ValueError('Il valore sembra un DOI ma non ha un formato valido')
    oa = openalex or OpenAlexClient()
    records = []
    for row in oa.search(query, limit=10):
        author = (row.get('authorships') or [{}])[0].get('author') or {}
        records.append({'id': openalex_id(row['id']),
                        'title': row.get('display_name',''),
                        'year': str(row.get('publication_year') or ''),
                        'first_author': author.get('display_name',''),
                        'doi': doi_normalize(row.get('doi')),
                        'verification': 'DA_VERIFICARE'})
    return records


def verify_result(result: dict, openalex=None, crossref=None) -> dict:
    if result.get('meta'):
        return dict(result['meta'])
    return get_checked_work(result['id'], openalex=openalex, crossref=crossref)


def save_verified_meta(meta: dict, catalog_class=Catalog) -> tuple[str, dict]:
    """Registra solo dopo conferma esplicita UI, mantenendo alias esistente."""
    cat = catalog_class()
    try:
        if meta.get('openalex_id'):
            row = register_checked(cat, meta)
        else:
            doi = doi_normalize(meta['DOI'])
            found = cat.by_doi(doi)
            if len(found) > 1:
                raise SourceError('DOI duplicato nel catalogo: verifica manuale necessaria')
            if found:
                row = found[0]
            else:
                row = cat.register(doi=doi, title=meta['title'], year=meta['year'],
                                   authors=meta['authors'], meta=meta, origin='crossref')
        return cat.alias(row['id']), dict(row)
    finally:
        cat.close()


def list_catalog(query='', limit=250) -> list[dict]:
    cat = Catalog()
    try:
        return [dict(r) for r in cat.all(limit=limit, query=query.strip() or None)]
    finally:
        cat.close()


def zotero_collection_choices() -> tuple[str, list[dict]]:
    w = ZoteroWriter()
    sid = w.connect()
    rows = w.collections()
    options = []
    for item in rows:
        data = item.get('data') or {}
        key = item.get('key') or data.get('key')
        if key:
            options.append({'key': key, 'name': data.get('name') or '(senza nome)'})
    options.sort(key=lambda x: (x['name'].casefold(), x['key']))
    return sid, options


def configured_collection():
    if not Path(DEFAULT_SETTINGS).exists():
        return None
    return json.loads(Path(DEFAULT_SETTINGS).read_text(encoding='utf-8'))


def save_collection_choice(server_id: str, key: str, name: str, options: list[dict]):
    if not any(x['key'] == key and x['name'] == name for x in options):
        raise ValueError('Raccolta non inclusa nell’elenco verificato da Zotero')
    path = Path(DEFAULT_SETTINGS)
    path.parent.mkdir(parents=True, exist_ok=True)
    info = {'server_id': server_id, 'collection_key': key,
            'collection_name': name, 'saved_at': datetime.now(timezone.utc).isoformat()}
    path.write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding='utf-8')
    return info


def planned_output_path(filename):
    source = Path(filename).resolve()
    if source.suffix.lower() != '.docx' or not source.is_file():
        raise ValueError('Seleziona un documento .docx esistente')
    if source.stem.endswith('_Zoterizzato'):
        raise ValueError('Seleziona il documento originale, non una copia _Zoterizzato')
    output = source.with_name(source.stem + '_Zoterizzato.docx')
    if not output.exists():
        return output
    for idx in range(2,10000):
        alt = source.with_name(f'{source.stem}_Zoterizzato_{idx}.docx')
        if not alt.exists():
            return alt
    raise OSError('Impossibile trovare un nome libero per la copia Word')


def convert_word(filename, *, auto_import=False, style='apa', resolver_factory=CatalogResolver):
    """Esegue conversione 0.4.2 su COPIA. Ritorna output, log e conteggi."""
    source = Path(filename).resolve()
    output = planned_output_path(source)
    catalog = Catalog()
    try:
        resolver = resolver_factory(catalog, auto_import=auto_import)
        if auto_import:
            # Preflight: no modification unless a valid target collection is configured.
            writer = ZoteroWriter()
            writer.connect()
            if not selected_collection(writer):
                raise ValueError('Seleziona una raccolta Zotero prima di autorizzare importazioni')
        count = resolver.load()
        results = process(source, output, resolver, style=style)
        csv_log, json_log, counts = write_logs(results, source, output)
        return {'source': str(source), 'output': str(output), 'csv': str(csv_log),
                'json': str(json_log), 'counts': dict(counts), 'indexed': count}
    finally:
        catalog.close()


def export_catalog_csv(output):
    import csv
    output = Path(output)
    cat = Catalog()
    try:
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open('w', encoding='utf-8-sig', newline='') as stream:
            writer = csv.writer(stream, delimiter=';')
            writer.writerow(['Codice', 'Autori', 'Anno', 'Titolo', 'DOI', 'OpenAlex ID', 'Origine', 'Chiave Zotero'])
            for r in cat.db.execute('SELECT * FROM references_catalog ORDER BY id'):
                authors = json.loads(r['authors'] or '[]')
                writer.writerow([cat.alias(r['id']),
                                 '; '.join(x.get('family','') for x in authors),
                                 r['year'], r['title'], r['doi'], r['openalex_id'],
                                 r['origin'], r['zotero_key']])
    finally:
        cat.close()
    return str(output)
