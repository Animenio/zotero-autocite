#!/usr/bin/env python3
"""Zotero AutoCite - DOI/Zotero key/alias markers to live Word Zotero fields.
Core preserves v0.1.2 behavior; optional catalog imports via official Zotero API.
"""
from __future__ import annotations
import argparse
import copy
import csv
import json
import re
import sys
import uuid
import zipfile
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from xml.etree import ElementTree as ET
from lxml import etree
from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.text.paragraph import Paragraph

BASE = "http://127.0.0.1:23119/api"
SCHEMA = "https://github.com/citation-style-language/schema/raw/master/csl-citation.json"
XMLNS = "http://www.w3.org/XML/1998/namespace"
W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
CUSTOM = "http://schemas.openxmlformats.org/officeDocument/2006/custom-properties"
VT = "http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes"
REL = "http://schemas.openxmlformats.org/package/2006/relationships"
CT = "http://schemas.openxmlformats.org/package/2006/content-types"
CUSTOM_REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/custom-properties"
CUSTOM_CT = "application/vnd.openxmlformats-officedocument.custom-properties+xml"
FMTID = "{D5CDD505-2E9C-101B-9397-08002B2CF9AE}"
# Supported:
# {(Rossi, 2023); doi:10.1234/xyz} and {(Rossi, 2023); key:ABCD1234}
# [[ZCITE:doi:10.1234/xyz]] and [[ZCITE:key:ABCD1234]]
MARKER = re.compile(
    r"\{\s*\((?P<label>[^{}\r\n]{2,120}?)\)\s*;\s*(?P<kt>doi|key)\s*:\s*(?P<kv>[^{}\s;]+)\s*\}"
    r"|\[\[\s*ZCITE\s*:\s*(?P<kt2>doi|key)\s*:\s*(?P<kv2>[^\]\s]+)\s*\]\]"
    r"|\[\[\s*Z\s*:\s*(?P<alias>\d{1,10})\s*\]\]",
    flags=re.IGNORECASE,
)
BIB_MARKER = "[[ZBIB]]"
IGNORE_TYPES = {"attachment", "note", "annotation"}

class ZoteroError(RuntimeError):
    pass

def get_json(path, params=None):
    url = BASE + path + ("?" + urlencode(params) if params else "")
    request = Request(url, headers={"Zotero-API-Version": "3", "Accept": "application/json"})
    try:
        with urlopen(request, timeout=18) as r:
            return json.loads(r.read().decode("utf-8"))
    except HTTPError as e:
        raise ZoteroError(f"Zotero API HTTP {e.code}: {url}. Se è 403, abilitare Zotero > Impostazioni > Avanzate > accesso locale.") from e
    except (URLError, TimeoutError) as e:
        raise ZoteroError("Impossibile collegarsi a Zotero locale. Apri Zotero e abilita 'Allow other applications on this computer to communicate with Zotero'.") from e


def norm_doi(value):
    s = str(value or "").strip().lower()
    return re.sub(r"^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)", "", s).rstrip(".,;)")


def full_year(date):
    m = re.search(r"\b(?:1[89]|20)\d{2}\b", str(date or ""))
    return m.group(0) if m else ""


def last_names(creators):
    return [str(c.get("lastName") or c.get("name") or "").strip().lower() for c in creators or [] if c.get("creatorType") in ("author", "editor", "bookAuthor")]


def first_author_year(label):
    """Checks only simple (LastName, YYYY) or (LastName et al., YYYY) labels.
    Complex labels are considered display-only and not crosschecked.
    """
    if not label:
        return None
    m = re.match(r"^\s*([\wÀ-ÿ'’\-]+)(?:\s+et\s+al\.?)?\s*,\s*((?:19|20)\d{2})[a-z]?\s*$", label, re.I)
    if m:
        return m.group(1).casefold(), m.group(2)
    return None


def item_info(item):
    data = item.get("data") or {}
    lib = item.get("library") or {}
    key = item.get("key") or data.get("key") or ""
    libtype = lib.get("type") or "user"
    libid = lib.get("id")
    # Use actual user/group ID, not local API alias 0, when available.
    uri = item.get("uri") or data.get("uri")
    if not uri and libid is not None:
        part = "groups" if libtype == "group" else "users"
        uri = f"http://zotero.org/{part}/{libid}/items/{key}"
    return {"key": key.upper(), "doi": norm_doi(data.get("DOI")), "title": data.get("title", ""),
            "year": full_year(data.get("date")), "authors": last_names(data.get("creators")),
            "uri": uri, "item": item, "libid": libid, "libtype": libtype}


class LocalZotero:
    def __init__(self, group_ids=None):
        self.group_ids = list(group_ids or [])
        self.by_doi = defaultdict(list)
        self.by_key = defaultdict(list)
        self.csl_cache = {}
        self.count = 0

    def load(self):
        paths = ["/users/0/items/top"] + [f"/groups/{gid}/items/top" for gid in self.group_ids]
        for path in paths:
            # The Zotero HTTP API is paginated; indexing the first page alone
            # can produce false MANCANTE reports for large personal libraries.
            start, limit = 0, 100
            while True:
                result = get_json(path, {"format": "json", "start": start, "limit": limit})
                if not isinstance(result, list):
                    raise ZoteroError("Risposta non valida dalla API Zotero: lista di item attesa")
                for item in result:
                    if (item.get("data") or {}).get("itemType") in IGNORE_TYPES:
                        continue
                    info = item_info(item)
                    if not info["key"]:
                        continue
                    self.by_key[info["key"]].append(info)
                    if info["doi"]:
                        self.by_doi[info["doi"]].append(info)
                    self.count += 1
                if len(result) < limit:
                    break
                start += len(result)
        return self.count

    def find(self, type_, value, label=None):
        pool = self.by_doi.get(norm_doi(value), []) if type_.lower() == "doi" else self.by_key.get(str(value).upper(), [])
        if not pool:
            return "MANCANTE", None, "Riferimento non presente nelle librerie indicizzate"
        if len(pool) > 1:
            return "AMBIGUA", None, "Più voci Zotero con lo stesso identificativo: " + ", ".join(p["key"] for p in pool)
        info = pool[0]
        simple = first_author_year(label)
        if simple:
            surname, year = simple
            if info["year"] and year != info["year"]:
                return "INCOERENTE", None, f"Anno nel testo: {year}; anno in Zotero: {info['year']}"
            if info["authors"] and surname not in info["authors"][0].casefold():
                return "INCOERENTE", None, f"Primo autore nel testo: {surname}; Zotero: {info['authors'][0]}"
        if not info["uri"]:
            return "METADATI_INCOMPLETI", None, "URI della libreria assente: impossibile collegare il campo a Zotero"
        return "TROVATA", info, ""

    def csl(self, info):
        key = (info["libtype"], info["libid"], info["key"])
        if key in self.csl_cache:
            return self.csl_cache[key]
        path = f"/groups/{info['libid']}/items/{info['key']}" if info["libtype"] == "group" else f"/users/0/items/{info['key']}"
        result = get_json(path, {"format": "csljson"})
        if isinstance(result, list):
            result = result[0] if len(result) == 1 else None
        if not isinstance(result, dict):
            raise ZoteroError("Esportazione CSL-JSON Zotero non valida")
        if not result.get("title") and not result.get("author"):
            raise ZoteroError("CSL-JSON privo di titolo e autori")
        self.csl_cache[key] = result
        return result


def initial_visible_citation(info, csl, label=None):
    """Readable placeholder until Zotero Refresh applies the document's CSL style.

    Avoid truncating two-author citations to the first author in the initial DOCX.
    The Zotero field itself, not this preview, is the authoritative citation.
    """
    if label:
        return "(" + label.strip() + ")"
    people = csl.get("author") or csl.get("editor") or []
    names = [str(p.get("family") or p.get("literal") or "").strip() for p in people]
    names = [name for name in names if name]
    if not names:
        names = [a.title() for a in (info.get("authors") or []) if a] or ["Autore"]
    authors = names[0] if len(names) == 1 else (
        names[0] + " & " + names[1] if len(names) == 2 else names[0] + " et al.")
    issued = (csl.get("issued") or {}).get("date-parts") or []
    year = str(issued[0][0]) if issued and issued[0] else (info.get("year") or "s.d.")
    return f"({authors}, {year})"


def citation_code(info, csl, visible):
    csl = copy.deepcopy(csl)
    csl.setdefault("id", info["uri"])
    payload = {
        "citationID": uuid.uuid4().hex[:10],
        "properties": {"formattedCitation": visible, "plainCitation": visible, "noteIndex": 0},
        "citationItems": [{"id": info["key"], "uris": [info["uri"]], "itemData": csl}],
        "schema": SCHEMA,
    }
    return "ADDIN ZOTERO_ITEM CSL_CITATION " + json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def make_run(kind, content=None):
    run = OxmlElement("w:r")
    run.append(OxmlElement("w:rPr"))
    if kind == "char":
        f = OxmlElement("w:fldChar"); f.set(qn("w:fldCharType"), content); run.append(f)
    elif kind == "instruction":
        t = OxmlElement("w:instrText"); t.set(f"{{{XMLNS}}}space", "preserve"); t.text = " " + content + " "; run.append(t)
    elif kind == "text":
        t = OxmlElement("w:t"); t.set(f"{{{XMLNS}}}space", "preserve"); t.text = content; run.append(t)
    return run


def field_runs(code, visible):
    return [make_run("char", "begin"), make_run("instruction", code),
            make_run("char", "separate"), make_run("text", visible), make_run("char", "end")]


def text_nodes(para_el):
    """Only paragraphs without existing Word field codes are mutated in MVP.
    Matches may cross multiple text runs. Hyperlinks are intentionally excluded.
    """
    nodes = []
    for child in para_el.iterchildren():
        if child.tag != qn("w:r"):
            continue
        nodes.extend(child.findall(qn("w:t")))
    return nodes


def span_of_nodes(nodes):
    cursor, spans = 0, []
    for n in nodes:
        t = n.text or ""
        spans.append((cursor, cursor + len(t), n))
        cursor += len(t)
    return spans


def set_word_text(node, value):
    """Preserve boundary whitespace when a w:t is split around a Zotero field.

    Word strips leading/trailing spaces in w:t unless xml:space="preserve".
    """
    node.text = value
    if value and (value[0].isspace() or value[-1].isspace()):
        node.set(f"{{{XMLNS}}}space", "preserve")


def needs_space_before(char):
    """Insert a separator only when the author did not type one already."""
    return bool(char) and (char.isalnum() or char in ".,;:!?)]}”’\"'»")


def needs_space_after(char):
    return bool(char) and (char.isalnum() or char in "(“«")


def replace_text_with_field(para, start, end, code, visible):
    """Replaces a marker without rewriting the whole paragraph or losing formatting.
    Other runs and paragraph styling stay intact; cite field appears at first marker run.
    """
    nodes = text_nodes(para._p)
    spans = span_of_nodes(nodes)
    plain_text = "".join(n.text or "" for n in nodes)
    # Preserve existing whitespace and avoid run boundaries eating a space.
    # When the original has no separator at all, insert exactly one.
    need_left = start > 0 and needs_space_before(plain_text[start - 1])
    need_right = end < len(plain_text) and needs_space_after(plain_text[end])
    overlapping = [(a, b, n) for a, b, n in spans if a < end and b > start]
    if not overlapping:
        raise ValueError("Marker spans not found")
    a0, b0, first = overlapping[0]
    a1, b1, last = overlapping[-1]
    first_run = first.getparent()
    if first_run.tag != qn("w:r"):
        raise ValueError("Marcatore in una struttura Word non supportata")
    after = (last.text or "")[end - a1:]
    before = (first.text or "")[:start - a0]
    same = first is last
    if need_left:
        before += " "
    if need_right:
        after = " " + after
    set_word_text(first, before)
    for _, _, n in overlapping[1:]:
        set_word_text(n, "")
    # Preceding/trailing text nodes can end on whitespace even when the marker
    # begins in another run; make sure Word does not trim those separators.
    for _, _, n in spans:
        if n is not first and n is not last and n.text:
            set_word_text(n, n.text)
    # For same-node markers, suffix must move AFTER the inserted field.
    if same:
        trailing_run = copy.deepcopy(first_run)
        # Preserve only run style and new suffix, since any other content would duplicate.
        for child in list(trailing_run):
            if child.tag != qn("w:rPr"):
                trailing_run.remove(child)
        trailing_text = OxmlElement("w:t")
        trailing_text.set(f"{{{XMLNS}}}space", "preserve")
        trailing_text.text = after
        trailing_run.append(trailing_text)
    else:
        set_word_text(last, after)
    position = para._p.index(first_run) + 1
    for r in field_runs(code, visible):
        para._p.insert(position, r)
        position += 1
    if same and after:
        para._p.insert(position, trailing_run)


def iter_paragraphs(doc):
    # Keep references to the XML paragraph objects, not their integer id().
    # lxml can recycle wrapper ids when traversing tables after many paragraphs.
    seen = set()
    def walk(container):
        for p in container.paragraphs:
            if p._p not in seen:
                seen.add(p._p)
                yield p
        for table in container.tables:
            for row in table.rows:
                for cell in row.cells:
                    yield from walk(cell)
    yield from walk(doc)


def paragraph_number(el, mapping):
    return mapping.get(id(el), "?")


def bib_field_present(doc):
    return any("ZOTERO_BIBL" in t.text for t in doc.element.body.iter(qn("w:instrText")) if t.text)


def add_bibliography(doc, report):
    if bib_field_present(doc):
        report.append({"paragrafo": "bibliografia", "marcatore": "", "esito": "BIBLIOGRAFIA_GIA_PRESENTE", "key": "", "doi": "", "titolo": "", "dettagli": "Campo Zotero esistente conservato"})
        return
    target = None
    for p in iter_paragraphs(doc):
        if p.text.strip() == BIB_MARKER:
            target = p
            break
    if target is None:
        doc.add_page_break()
        doc.add_heading("Bibliografia", level=1)
        target = doc.add_paragraph()
    else:
        # Clear the marker only, preserving surrounding paragraph styles.
        for n in text_nodes(target._p):
            n.text = ""
    for run in field_runs('ADDIN ZOTERO_BIBL {"uncited":[],"omitted":[],"custom":[]} CSL_BIBLIOGRAPHY',
                          "[Bibliografia Zotero: aprire il documento in Word e premere Zotero → Refresh]"):
        target._p.append(run)
    report.append({"paragrafo": "bibliografia", "marcatore": BIB_MARKER, "esito": "BIBLIOGRAFIA_INSERITA", "key": "", "doi": "", "titolo": "", "dettagli": "Il contenuto sarà generato dal plugin Zotero durante Refresh"})


def document_has_prefs(filename):
    with zipfile.ZipFile(filename) as z:
        if "docProps/custom.xml" not in z.namelist():
            return False
        try:
            root = ET.fromstring(z.read("docProps/custom.xml"))
        except ET.ParseError:
            return False
        return any((e.get("name") or "").startswith("ZOTERO_PREF") for e in root)


def insert_document_prefs(docx_filename, style):
    """Write Zotero custom properties (only for new documents without Zotero prefs).
    Existing Zotero styles are never overwritten.
    """
    p = Path(docx_filename)
    if document_has_prefs(p):
        return False
    prefs = (f'<data data-version="3" zotero-version="7.0">'
             f'<session id="{uuid.uuid4().hex}"/>'
             f'<style id="http://www.zotero.org/styles/{style}" locale="en-US" hasBibliography="1" bibliographyStyleHasBeenSet="1"/>'
             f'<prefs><pref name="fieldType" value="Field"/>'
             f'<pref name="automaticJournalAbbreviations" value="true"/>'
             f'<pref name="noteType" value="0"/></prefs></data>')
    chunks = [prefs[i:i+255] for i in range(0, len(prefs), 255)]
    with zipfile.ZipFile(p, "r") as zi:
        content = {name: zi.read(name) for name in zi.namelist()}
    if "docProps/custom.xml" in content:
        custom = ET.fromstring(content["docProps/custom.xml"])
    else:
        custom = ET.Element(f"{{{CUSTOM}}}Properties")
    pid = max((int(n.get("pid", 1)) for n in custom), default=1) + 1
    for i, chunk in enumerate(chunks, start=1):
        prop = ET.SubElement(custom, f"{{{CUSTOM}}}property", {"fmtid": FMTID,"pid": str(pid),"name": f"ZOTERO_PREF_{i}"})
        ET.SubElement(prop, f"{{{VT}}}lpwstr").text = chunk
        pid += 1
    content["docProps/custom.xml"] = ET.tostring(custom, encoding="utf-8", xml_declaration=True)
    root = ET.fromstring(content["_rels/.rels"])
    if not any(e.get("Type") == CUSTOM_REL for e in root):
        used = {e.get("Id") for e in root}
        i = 1
        while f"rId{i}" in used:
            i += 1
        ET.SubElement(root, f"{{{REL}}}Relationship", {"Id": f"rId{i}","Type": CUSTOM_REL,"Target": "docProps/custom.xml"})
        content["_rels/.rels"] = ET.tostring(root, encoding="utf-8", xml_declaration=True)
    root = ET.fromstring(content["[Content_Types].xml"])
    if not any(e.get("PartName") == "/docProps/custom.xml" for e in root):
        ET.SubElement(root, f"{{{CT}}}Override", {"PartName": "/docProps/custom.xml", "ContentType": CUSTOM_CT})
        content["[Content_Types].xml"] = ET.tostring(root, encoding="utf-8", xml_declaration=True)
    tmp = p.with_name(p.stem + ".autocite-tmp.docx")
    with zipfile.ZipFile(tmp, "w", compression=zipfile.ZIP_DEFLATED) as zo:
        for name, raw in content.items():
            zo.writestr(name, raw)
    tmp.replace(p)
    return True


def process(filename, destination, resolver, style="apa", bibliography=True):
    if Path(filename).resolve() == Path(destination).resolve():
        raise ValueError("Il documento originale non deve essere sovrascritto")
    doc = Document(filename)
    results = []
    paras = list(iter_paragraphs(doc))
    for index, p in enumerate(paras, 1):
        nodes = text_nodes(p._p)
        content = "".join(n.text or "" for n in nodes)
        matches = list(MARKER.finditer(content))
        if not matches:
            continue
        # Word fields in the paragraph are skipped to avoid corruption.
        has_field = any(x.tag == qn("w:fldChar") for x in p._p.iter())
        # Processing right-to-left preserves original offsets for earlier markers.
        for m in reversed(matches):
            marker = m.group(0)
            rec = {"paragrafo": index, "marcatore": marker, "esito": "", "key": "", "doi": "", "titolo": "", "dettagli": ""}
            if has_field:
                rec.update(esito="NON_SUPPORTATA", dettagli="Paragrafo contenente campi Word preesistenti (protezione conservativa)")
                results.append(rec)
                continue
            kind = "alias" if m.group("alias") is not None else (m.group("kt") or m.group("kt2")).lower()
            value = m.group("alias") if kind == "alias" else (m.group("kv") or m.group("kv2"))
            label = m.group("label")
            status, info, note = resolver.find(kind, value, label)
            if status != "TROVATA":
                rec.update(esito=status, dettagli=note)
                results.append(rec)
                continue
            try:
                csl = resolver.csl(info)
                visible = initial_visible_citation(info, csl, label)
                code = citation_code(info, csl, visible)
                replace_text_with_field(p, m.start(), m.end(), code, visible)
                rec.update(esito="CONVERTITA", key=info["key"], doi=info["doi"], titolo=info["title"], dettagli=(note + "; " if note else "") + "Campo Word CSL_CITATION inserito; verifica con Zotero Refresh")
            except Exception as exc:
                rec.update(esito="ERRORE", dettagli=str(exc))
            results.append(rec)
    converted = sum(r["esito"] == "CONVERTITA" for r in results)
    if converted and bibliography:
        add_bibliography(doc, results)
    Path(destination).parent.mkdir(parents=True, exist_ok=True)
    doc.save(destination)
    if converted:
        insert_document_prefs(destination, style=style)
    return results


def write_logs(results, filename, output):
    prefix = Path(output).with_suffix("")
    csv_file = prefix.with_name(prefix.name + "_LOG.csv")
    json_file = prefix.with_name(prefix.name + "_riepilogo.json")
    fields = ["paragrafo", "marcatore", "esito", "key", "doi", "titolo", "dettagli"]
    with csv_file.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, delimiter=";")
        writer.writeheader()
        writer.writerows(results)
    counts = Counter(r["esito"] for r in results)
    stats = {"origine": str(filename), "output": str(output), "timestamp": datetime.now().isoformat(timespec="seconds"),
             "conteggi": dict(counts), "citazioni_non_risolte": [r for r in results if r["esito"] not in ("CONVERTITA", "BIBLIOGRAFIA_INSERITA", "BIBLIOGRAFIA_GIA_PRESENTE")],
             "nota": "Compatibilità dei campi Zotero da verificare tramite Word Desktop > Zotero > Refresh."}
    json_file.write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")
    return csv_file, json_file, counts


def main(argv=None):
    parser = argparse.ArgumentParser(description="Convertitore gratuito di marcatori DOI/key in campi Zotero dentro Word")
    parser.add_argument("document", type=Path, help="Percorso del file .docx originale")
    parser.add_argument("--output", type=Path, help="Nome del documento generato (default: *_Zoterizzato.docx)")
    parser.add_argument("--style", choices=["apa", "harvard1", "chicago-author-date"], default="apa")
    parser.add_argument("--group-id", type=int, action="append", default=[], help="Librerie Zotero di gruppo da indicizzare; ripetibile")
    parser.add_argument("--no-bibliography", action="store_true", help="Non aggiungere un nuovo campo bibliografico")
    parser.add_argument("--auto-import", action="store_true", help="Importa automaticamente nel Zotero locale gli alias non presenti, esclusivamente nella raccolta scelta")
    parser.add_argument("--no-catalog", action="store_true", help="Disabilita i codici brevi e usa solo DOI/key")
    args = parser.parse_args(argv)
    if not args.document.exists() or args.document.suffix.lower() != ".docx":
        parser.error("Devi indicare un file .docx esistente (non .doc o .pdf)")
    dest = args.output or args.document.with_name(args.document.stem + "_Zoterizzato.docx")
    try:
        catalog = None
        if args.no_catalog:
            library = LocalZotero(args.group_id)
        else:
            from autocite_catalog import Catalog, CatalogResolver
            catalog = Catalog()
            library = CatalogResolver(catalog, auto_import=args.auto_import, group_ids=args.group_id)
        n = library.load()
        print(f"Libreria Zotero locale: {n} voci bibliografiche indicizzate")
        results = process(args.document, dest, library, args.style, bibliography=not args.no_bibliography)
        log, summary, counts = write_logs(results, args.document, dest)
        if catalog is not None:
            catalog.close()
    except (ZoteroError, OSError, ValueError) as e:
        print("ERRORE:", e, file=sys.stderr)
        return 2
    print("Documento creato:", dest)
    print("LOG CSV:", log)
    print("Riepilogo JSON:", summary)
    print("Esiti:", dict(counts))
    print("Apri il DOCX in Word Desktop e usa Zotero > Refresh per completare la formattazione.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
