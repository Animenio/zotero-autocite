import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from docx import Document
from docx.oxml.ns import qn
from zotero_autocite import process, document_has_prefs, item_info, LocalZotero, norm_doi

ITEM = {
    "key": "ABCD1234", "library": {"type":"user", "id": 98765},
    "data": {"key":"ABCD1234", "itemType":"journalArticle", "DOI":"10.5555/demo01", "title":"Transparency Research",
             "date":"2023-01-10", "creators":[{"creatorType":"author", "lastName":"Rossi", "firstName":"Luca"}]}
}

class FakeZotero:
    def __init__(self):
        self.info = item_info(ITEM)
        self.info2 = None
    def find(self, kind, val, label=None):
        if (kind=="doi" and norm_doi(val)==self.info['doi']) or (kind=="key" and val.upper()==self.info['key']):
            if label and ('2020' in label or 'Bianchi' in label):
                return "INCOERENTE", None, "Autore o anno non concordano"
            return "TROVATA", self.info, ""
        return "MANCANTE", None, "Non presente in Zotero"
    def csl(self, info):
        return {"id": info["uri"], "type":"article-journal", "title": info["title"],
                "author":[{"given":"Luca", "family":"Rossi"}], "issued":{"date-parts":[[2023]]},
                "DOI": info["doi"]}

class AutoCiteTests(unittest.TestCase):
    def test_doi_norm(self):
        self.assertEqual(norm_doi("https://doi.org/10.5555/DEMO01"), "10.5555/demo01")

    def test_conversion_run_splitting_and_unresolved(self):
        with tempfile.TemporaryDirectory() as temp:
            input_file = Path(temp) / "test.docx"
            output_file = Path(temp) / "out.docx"
            doc = Document()
            p = doc.add_paragraph(style="Normal")
            p.add_run("Prima citazione ")
            r = p.add_run("{(Rossi, 2023); ")
            r.bold = True
            p.add_run("doi:10.5555/demo01}")
            p.add_run(" e due volte { (Rossi, 2023); key:ABCD1234 } fine. ")
            p.add_run("Mancante {(X, 2024); doi:10.5555/missing}.")
            table = doc.add_table(rows=1, cols=1)
            table.cell(0, 0).text = "Test in tabella [[ZCITE:key:ABCD1234]] concluso"
            doc.add_paragraph("[[ZBIB]]")
            doc.save(input_file)
            res = process(input_file, output_file, FakeZotero())
            self.assertEqual(sum(r["esito"] == "CONVERTITA" for r in res), 3)
            self.assertEqual(sum(r["esito"] == "MANCANTE" for r in res), 1)
            self.assertTrue(document_has_prefs(output_file))
            with zipfile.ZipFile(output_file) as z:
                xml = z.read('word/document.xml').decode()
                self.assertEqual(xml.count('ADDIN ZOTERO_ITEM CSL_CITATION'), 3)
                self.assertEqual(xml.count('ADDIN ZOTERO_BIBL'), 1)
                self.assertIn('10.5555/missing', xml)
                self.assertNotIn('doi:10.5555/demo01}', xml)
            new = Document(output_file)
            self.assertIn('Prima citazione',new.paragraphs[0].text)
            self.assertIn('fine.',new.paragraphs[0].text)
            self.assertIn('Test in tabella',new.tables[0].cell(0,0).text)
            self.assertIn('concluso',new.tables[0].cell(0,0).text)

    def test_word_spacing_is_preserved_and_missing_separator_added(self):
        """Regression: Word trims w:t trailing spaces unless xml:space=preserve."""
        with tempfile.TemporaryDirectory() as temp:
            orig = Path(temp) / "spacing.docx"
            out = Path(temp) / "spacing_converted.docx"
            doc = Document()
            doc.add_paragraph("creditori {(Rossi, 2023); doi:10.5555/demo01}.")
            doc.add_paragraph("aziendale{(Rossi, 2023); doi:10.5555/demo01}.")
            doc.add_paragraph("marcatore: [[ZCITE:key:ABCD1234]].")
            doc.add_paragraph("Prima {(Rossi, 2023); doi:10.5555/demo01}dopo.")
            para = doc.add_paragraph()
            para.add_run("Test prima ")
            para.add_run("{(Rossi, 2023); ")
            para.add_run("doi:10.5555/demo01}")
            para.add_run(" e dopo")
            doc.save(orig)
            results = process(orig, out, FakeZotero(), bibliography=False)
            self.assertEqual(sum(r["esito"] == "CONVERTITA" for r in results), 5)
            actual_doc = Document(out)
            visible = ["".join(t.text or "" for t in p._p.iter(qn("w:t"))) for p in actual_doc.paragraphs]
            expected = [
                "creditori (Rossi, 2023).",
                "aziendale (Rossi, 2023).",
                "marcatore: (Rossi, 2023).",
                "Prima (Rossi, 2023) dopo.",
                "Test prima (Rossi, 2023) e dopo",
            ]
            self.assertEqual(visible, expected)
            for p in actual_doc.paragraphs:
                for t in p._p.iter(qn("w:t")):
                    if t.text and (t.text[0].isspace() or t.text[-1].isspace()):
                        self.assertEqual(t.get("{http://www.w3.org/XML/1998/namespace}space"), "preserve")

    def test_table_after_many_paragraphs(self):
        with tempfile.TemporaryDirectory() as temp:
            origin=Path(temp)/"t.docx"
            target=Path(temp)/"u.docx"
            d=Document()
            for i in range(25):
                d.add_paragraph("Paragrafo di riempimento " + str(i))
            d.add_table(rows=1,cols=1).cell(0,0).text="Tabella {(Rossi, 2023); doi:10.5555/demo01}"
            d.add_paragraph("[[ZBIB]]")
            d.save(origin)
            result=process(origin,target,FakeZotero())
            self.assertEqual(sum(r["esito"]=="CONVERTITA" for r in result), 1)

    def test_incoherent_unchanged(self):
        with tempfile.TemporaryDirectory() as temp:
            orig=Path(temp)/'o.docx'; out=Path(temp)/'n.docx'
            d=Document(); d.add_paragraph('Critico {(Bianchi, 2020); doi:10.5555/demo01}'); d.save(orig)
            res=process(orig,out,FakeZotero())
            self.assertEqual(res[0]['esito'],'INCOERENTE')
            self.assertIn('Bianchi, 2020',Document(out).paragraphs[0].text)
            self.assertFalse(document_has_prefs(out))

if __name__ == '__main__':
    unittest.main(verbosity=2)
