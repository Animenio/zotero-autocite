"""DOI-first offline tests. Never calls a live API or Zotero."""
import json
import tempfile
import unittest
from pathlib import Path
from autocite_catalog import Catalog
from autocite_openalex import interactive_doi, is_doi_query, SourceError
from test_openalex import WORK, CROSSREF

class FakeOA:
    def __init__(self, work=WORK, absent=False):
        self.work=work
        self.absent=absent
        self.inputs=[]
    def by_doi(self, doi):
        self.inputs.append(doi)
        if self.absent:
            raise SourceError('Record inesistente su https://api.openalex.org (HTTP 404)')
        return self.work

class FakeCR:
    def __init__(self, entry=CROSSREF):
        self.entry=entry
        self.inputs=[]
    def get(self, doi):
        self.inputs.append(doi)
        return self.entry

class DoiFirstTests(unittest.TestCase):
    def test_detection(self):
        for x in ('10.5555/test-paper', 'doi:10.5555/test-paper', 'https://doi.org/10.5555/test-paper'):
            self.assertTrue(is_doi_query(x))
        self.assertFalse(is_doi_query('How susceptible are jobs to computerisation?'))
        self.assertFalse(is_doi_query('10.not/a-doi'))

    def test_exact_doi_register_preserve_alias(self):
        with tempfile.TemporaryDirectory() as tmp:
            cat=Catalog(Path(tmp)/'db.sqlite3')
            oa=FakeOA();cr=FakeCR();printed=[]
            first=interactive_doi(cat,'https://doi.org/10.5555/test-paper',input_fn=lambda q:'s',print_fn=printed.append,openalex=oa,crossref=cr)
            self.assertEqual(cat.alias(first['id']),'[[Z:00001]]')
            self.assertEqual(first['openalex_id'],'W1234567890')
            self.assertEqual(oa.inputs,['10.5555/test-paper'])
            self.assertEqual(cr.inputs,['10.5555/test-paper'])
            second=interactive_doi(cat,'doi:10.5555/test-paper',input_fn=lambda q:'s',print_fn=printed.append,openalex=oa,crossref=cr)
            self.assertEqual(first['id'],second['id'])
            self.assertEqual(len(cat.all()),1)
            cat.close()

    def test_cancel_does_not_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            cat=Catalog(Path(tmp)/'db.sqlite3')
            result=interactive_doi(cat,'10.5555/test-paper',input_fn=lambda q:'n',print_fn=lambda x:None,openalex=FakeOA(),crossref=FakeCR())
            self.assertIsNone(result)
            self.assertEqual(len(cat.all()),0)
            cat.close()

    def test_crossref_fallback_on_openalex_404_and_stable_alias(self):
        with tempfile.TemporaryDirectory() as tmp:
            cat=Catalog(Path(tmp)/'db.sqlite3')
            oa=FakeOA(absent=True)
            first=interactive_doi(cat,'10.5555/test-paper',input_fn=lambda q:'s',print_fn=lambda x:None,openalex=oa,crossref=FakeCR())
            self.assertEqual(first['origin'],'crossref')
            self.assertIsNone(first['openalex_id'])
            second=interactive_doi(cat,'10.5555/test-paper',input_fn=lambda q:'s',print_fn=lambda x:None,openalex=oa,crossref=FakeCR())
            self.assertEqual(first['id'],second['id'])
            self.assertEqual(len(cat.all()),1)
            cat.close()

    def test_wrong_openalex_doi_aborts(self):
        with tempfile.TemporaryDirectory() as tmp:
            cat=Catalog(Path(tmp)/'db.sqlite3')
            work={**WORK,'doi':'https://doi.org/10.5555/different'}
            with self.assertRaisesRegex(SourceError,'non corrisponde'):
                interactive_doi(cat,'10.5555/test-paper',openalex=FakeOA(work),crossref=FakeCR())
            self.assertEqual(len(cat.all()),0)
            cat.close()

    def test_crossref_wrong_doi_aborts(self):
        with tempfile.TemporaryDirectory() as tmp:
            cat=Catalog(Path(tmp)/'db.sqlite3')
            entry={**CROSSREF,'DOI':'10.5555/other'}
            with self.assertRaisesRegex(SourceError,'non coerente'):
                interactive_doi(cat,'10.5555/test-paper',openalex=FakeOA(absent=True),crossref=FakeCR(entry=entry))
            self.assertEqual(len(cat.all()),0)
            cat.close()

    def test_network_or_rate_error_does_not_fall_back(self):
        class RateLimited:
            def by_doi(self, doi): raise SourceError('API https://api.openalex.org: HTTP 429')
        with tempfile.TemporaryDirectory() as tmp:
            cat=Catalog(Path(tmp)/'db.sqlite3')
            cr=FakeCR()
            with self.assertRaisesRegex(SourceError,'429'):
                interactive_doi(cat,'10.5555/test-paper',openalex=RateLimited(),crossref=cr)
            self.assertEqual(cr.inputs,[])
            cat.close()

if __name__=='__main__':
    unittest.main()
