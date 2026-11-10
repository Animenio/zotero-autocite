"""Offline deterministic integration tests: no network calls and no real Zotero writes."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from autocite_openalex import (SourceError, openalex_id, extract_openalex,
                              verify_crossref, get_checked_work, register_checked,
                              interactive_openalex)
from autocite_catalog import Catalog, CatalogResolver, ZoteroWriter
from zotero_autocite import item_info, initial_visible_citation

WORK = {
    'id': 'https://openalex.org/W1234567890',
    'doi': 'https://doi.org/10.5555/test-paper',
    'display_name': 'The Good Paper',
    'publication_year': 2025,
    'authorships': [{'author': {'display_name': 'Anna Rossi'}}],
    'type': 'article',
    'primary_location': {'source': {'display_name': 'Journal of Testing'}},
    'biblio': {'volume': '1', 'first_page': '10', 'last_page': '19'}
}
CROSSREF = {
    'DOI': '10.5555/test-paper',
    'title': ['The Good Paper'],
    'published': {'date-parts': [[2025,4,2]]},
    'author': [{'given': 'Anna', 'family': 'Rossi'}],
    'container-title': ['Journal of Testing'],
    'type': 'journal-article', 'volume': '1', 'page': '10-19'
}
NO_DOI = {**WORK, 'id':'https://openalex.org/W1111111111', 'doi': None,
          'display_name':'Another Working Paper', 'publication_year': 2022}

class FakeOA:
    def __init__(self, work=WORK): self.work=work
    def get(self, wid): return dict(self.work)
    def search(self, text): return [dict(self.work)]

class FakeCR:
    def __init__(self, entry=CROSSREF): self.entry=entry
    def get(self, doi): return dict(self.entry)

class FakeWriter:
    def __init__(self, item): self.item=item; self.created=[]; self.server_id='sid-1'
    def connect(self):return self.server_id
    def create_item(self, row, collection):
        self.created.append((row['id'],collection))
        return self.item
    def ensure_collection(self,collection):
        assert collection=='COLL1234'

class OAIntegrationTests(unittest.TestCase):
    def test_two_author_preview_is_not_truncated(self):
        preview=initial_visible_citation({'authors':['fama','french'],'year':'1993'},
                                         {'author':[{'family':'Fama'},{'family':'French'}],
                                          'issued':{'date-parts':[[1993]]}})
        self.assertEqual(preview,'(Fama & French, 1993)')

    def test_id_normalization_and_bad_values(self):
        self.assertEqual(openalex_id('https://openalex.org/w1234567890'),'W1234567890')
        with self.assertRaises(SourceError):openalex_id('WXX123')
        with self.assertRaises(SourceError):openalex_id('https://foreign.example/W123')

    def test_verify_metadata(self):
        checked = get_checked_work('W1234567890',openalex=FakeOA(),crossref=FakeCR())
        self.assertEqual(checked['verification'],'CROSSREF_VERIFIED')
        self.assertEqual(checked['openalex_id'],'W1234567890')
        self.assertEqual(checked['authors'][0]['family'],'Rossi')
        self.assertEqual(checked['DOI'],'10.5555/test-paper')

    def test_crossref_title_conflict_aborts_before_registration(self):
        invalid = {**CROSSREF,'title':['An Entirely Unrelated Study']}
        with self.assertRaisesRegex(SourceError,'Titoli discordanti'):
            get_checked_work('W1234567890',openalex=FakeOA(),crossref=FakeCR(invalid))

    def test_author_conflict_aborts(self):
        invalid={**CROSSREF,'author':[{'given':'Giorgio','family':'Bianchi'}]}
        with self.assertRaisesRegex(SourceError,'Primo autore discordante'):
            get_checked_work('W1234567890',openalex=FakeOA(),crossref=FakeCR(invalid))

    def test_year_conflict_aborts(self):
        invalid={**CROSSREF,'published':{'date-parts':[[2021]]}}
        with self.assertRaisesRegex(SourceError,'Anno discordante'):
            get_checked_work('W1234567890',openalex=FakeOA(),crossref=FakeCR(invalid))

    def test_doi_conflict_aborts(self):
        invalid={**CROSSREF,'DOI':'10.9999/another-paper'}
        with self.assertRaisesRegex(SourceError,'DOI OpenAlex/Crossref differenti'):
            get_checked_work('W1234567890',openalex=FakeOA(),crossref=FakeCR(invalid))

    def test_register_persistent_alias_and_0_3_schema_migration(self):
        with tempfile.TemporaryDirectory() as temp:
            db=Path(temp)/'catalog.sqlite3'
            cat=Catalog(db)
            first=cat.register(doi='10.5555/test-paper', title='The Good Paper',
                         year='2025',origin='crossref',authors=[{'family':'Rossi','given':'Anna'}])
            code=cat.alias(first['id'])
            cat.close()
            # Simulate a pre-0.4 database by removing the new column via SQLite copy.
            import sqlite3
            with sqlite3.connect(db) as conn:
                conn.execute('DROP INDEX catalog_openalex_unique')
                conn.execute('ALTER TABLE references_catalog DROP COLUMN openalex_id')
            cat=Catalog(db)
            self.assertTrue((Path(temp)/'catalog_backup_pre_0.4.sqlite3').exists())
            checked=get_checked_work('W1234567890',openalex=FakeOA(),crossref=FakeCR())
            result=register_checked(cat,checked)
            self.assertEqual(cat.alias(result['id']),code)
            self.assertEqual(cat.by_openalex('W1234567890')['id'],first['id'])
            again=register_checked(cat,checked)
            self.assertEqual(again['id'],first['id'])
            self.assertEqual(cat.db.execute('SELECT COUNT(*) FROM references_catalog').fetchone()[0],1)
            cat.close()

    def test_doi_less_record_stable_alias(self):
        with tempfile.TemporaryDirectory() as temp:
            cat=Catalog(Path(temp)/'new.sqlite3')
            checked=get_checked_work('W1111111111',openalex=FakeOA(NO_DOI),crossref=FakeCR())
            self.assertEqual(checked['verification'],'OPENALEX_ONLY')
            x=register_checked(cat,checked)
            y=register_checked(cat,checked)
            self.assertEqual(x['id'],y['id'])
            self.assertIsNone(y['doi'])
            self.assertEqual(cat.db.execute('SELECT COUNT(*) FROM references_catalog').fetchone()[0],1)
            cat.close()

    def test_interactive_cancel_leaves_registry_unchanged(self):
        with tempfile.TemporaryDirectory() as temp:
            cat=Catalog(Path(temp)/'new.sqlite3')
            result=interactive_openalex(cat,'Good Paper',input_fn=lambda _: '0',print_fn=lambda _: None,
                                        openalex=FakeOA(),crossref=FakeCR())
            self.assertIsNone(result)
            self.assertFalse(cat.all())
            cat.close()

    def test_doi_less_item_import_keeps_existing_alias(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            cat=Catalog(root/'catalog.sqlite3')
            original=register_checked(cat,get_checked_work('W1111111111',openalex=FakeOA(NO_DOI)))
            settings=root/'settings.json'
            settings.write_text(json.dumps({'server_id':'sid-1','collection_key':'COLL1234'}),encoding='utf-8')
            item={'key':'ABCD1234','library':{'id':1,'type':'user'},'data': {
                'key':'ABCD1234','itemType':'journalArticle','DOI':'', 'title':'Another Working Paper',
                'date':'2022','creators':[{'creatorType':'author','firstName':'Anna','lastName':'Rossi'}]}}
            resolver=CatalogResolver(cat,auto_import=True,settings_file=settings)
            resolver.writer=FakeWriter(item)
            resolver.server_id='sid-1'
            status,info,note=resolver.find('alias','00001')
            self.assertEqual(status,'TROVATA')
            self.assertEqual(info['key'],'ABCD1234')
            self.assertEqual(cat.by_alias('1')['zotero_key'],'ABCD1234')
            self.assertEqual(cat.db.execute('SELECT COUNT(*) FROM references_catalog').fetchone()[0],1)
            cat.close()

    def test_possible_duplicate_blocks_local_write(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            cat=Catalog(root/'catalog.sqlite3')
            register_checked(cat,get_checked_work('W1111111111',openalex=FakeOA(NO_DOI)))
            settings=root/'settings.json'
            settings.write_text(json.dumps({'server_id':'sid-1','collection_key':'COLL1234'}))
            item={'key':'ABCD1234','library':{'id':1,'type':'user'},'data': {
                'key':'ABCD1234','itemType':'journalArticle','DOI':'', 'title':'Another Working Paper',
                'date':'2022','creators':[{'creatorType':'author','firstName':'Anna','lastName':'Rossi'}]}}
            resolver=CatalogResolver(cat,auto_import=True,settings_file=settings)
            resolver.writer=FakeWriter(item);resolver.server_id='sid-1'
            resolver.by_key['ABCD1234'].append(item_info(item))
            status,info,_=resolver.find('alias','1')
            self.assertEqual(status,'POSSIBILE_DUPLICATO')
            self.assertFalse(resolver.writer.created)
            cat.close()

    def test_zotero_writer_accepts_checked_doi_less_template(self):
        with tempfile.TemporaryDirectory() as temp:
            cat=Catalog(Path(temp)/'catalog.sqlite3')
            row=register_checked(cat,get_checked_work('W1111111111',openalex=FakeOA(NO_DOI)))
            w=ZoteroWriter();w.server_id='sid-1'
            w.ensure_collection=lambda key: True
            w.template=lambda typ:{'itemType':typ,'title':'','DOI':'','date':'','publicationTitle':'','url':'',
                                   'creators':[],'collections':[]}
            payloads=[]
            def fake_request(path,method='GET',payload=None,**kwargs):
                if method=='POST':
                    payloads.append(payload)
                    return {'success':{'0':'ABCD1234'}}
                return {'key':'ABCD1234'}
            w.request=fake_request
            w.create_item(row,'COLL1234')
            self.assertEqual(payloads[0][0]['title'],'Another Working Paper')
            self.assertEqual(payloads[0][0]['DOI'],'')
            self.assertTrue(payloads[0][0]['url'].startswith('https://openalex.org/'))
            cat.close()

if __name__=='__main__':
    unittest.main()
