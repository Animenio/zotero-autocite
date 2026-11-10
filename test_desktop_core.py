import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from docx import Document
import autocite_desktop_core as d
from autocite_openalex import SourceError


class DummyOA:
    def __init__(self, *, missing=False, wrong=False):
        self.missing=missing;self.wrong=wrong;self.searches=[]
    def by_doi(self, doi):
        if self.missing:
            raise SourceError('Record inesistente su https://api.openalex.org (HTTP 404)')
        return {'id':'https://openalex.org/W123', 'display_name': 'A sample article',
                'doi':'https://doi.org/10.1234/other' if self.wrong else 'https://doi.org/10.1234/ok',
                'publication_year':2020,
                'authorships':[{'author':{'display_name':'Alice Example'}}]}
    def search(self, txt, limit=10):
        self.searches.append(txt)
        return [{'id':'https://openalex.org/W123', 'display_name':'A sample article',
                 'publication_year':2020, 'doi':'https://doi.org/10.1234/ok',
                 'authorships':[{'author':{'display_name':'Alice Example'}}]}]


class DummyCR:
    def get(self,doi):
        return {'DOI':'10.1234/ok','title':['A sample article'],'published':{'date-parts':[[2020]]},
                'author':[{'family':'Example','given':'Alice'}],'container-title':['Test Journal']}


class DesktopCoreTests(unittest.TestCase):
    def test_doi_first_uses_exact_and_returns_single_result(self):
        with patch.object(d,'verify_crossref',side_effect=lambda meta,cr:{**meta,'verification':'CROSSREF_VERIFIED'}):
            entries=d.search_publications('https://doi.org/10.1234/ok',openalex=DummyOA(),crossref=DummyCR())
        self.assertEqual(len(entries),1)
        self.assertEqual(entries[0]['doi'],'10.1234/ok')
        self.assertEqual(entries[0]['title'],'A sample article')

    def test_doi_fallback_requires_exact_crossref_doi(self):
        entry=d.get_doi_exact('10.1234/ok',openalex=DummyOA(missing=True),crossref=DummyCR())
        self.assertEqual(entry['verification'],'CROSSREF_ONLY')
        with self.assertRaises(SourceError):
            d.get_doi_exact('10.1234/different',openalex=DummyOA(missing=True),crossref=DummyCR())

    def test_wrong_openalex_doi_rejected(self):
        with self.assertRaises(SourceError):
            d.get_doi_exact('10.1234/ok',openalex=DummyOA(wrong=True),crossref=DummyCR())

    def test_title_search_then_explicit_selection(self):
        oa=DummyOA(); entries=d.search_publications('A sample article',openalex=oa)
        self.assertEqual(oa.searches,['A sample article'])
        self.assertEqual(entries[0]['id'],'W123')
        self.assertEqual(entries[0]['verification'],'DA_VERIFICARE')

    def test_manual_confirmation_required_to_save(self):
        # A search result doesn't write to the catalog; registry operations are separate.
        result=d.search_publications('A sample article',openalex=DummyOA())
        self.assertNotIn('meta', result[0])

    def test_input_path_does_not_overwrite_original_or_prior_copy(self):
        with tempfile.TemporaryDirectory() as tmp:
            src=Path(tmp)/'paper.docx'; Document().save(src)
            out=d.planned_output_path(src)
            self.assertEqual(out.name,'paper_Zoterizzato.docx')
            Document().save(out)
            self.assertEqual(d.planned_output_path(src).name,'paper_Zoterizzato_2.docx')
            with self.assertRaises(ValueError):d.planned_output_path(out)

    def test_invalid_doi_url_is_not_treated_as_title(self):
        with self.assertRaises(ValueError):
            d.search_publications('https://doi.org/invalid')

    def test_collection_key_must_be_one_of_verified_choices(self):
        with self.assertRaises(ValueError):
            d.save_collection_choice('sid','FAKE','Fake',[{'key':'REAL','name':'AutoCite TEST'}])


if __name__=='__main__':
    unittest.main()
