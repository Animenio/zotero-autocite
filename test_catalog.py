import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch
from docx import Document
from autocite_catalog import Catalog, CatalogError, CatalogResolver, ZoteroWriter, selected_collection
from zotero_autocite import process, item_info

ITEM = {'key':'ABCD1234', 'library': {'id':98765,'type':'user'},
        'data': {'key':'ABCD1234','itemType':'journalArticle','title':'The Good Paper',
                 'DOI':'10.5555/test-paper','date':'2025',
                 'collections':[],
                 'creators':[{'creatorType':'author','firstName':'Anna','lastName':'Rossi'}]}}
CSL = {'id':'http://zotero.org/users/98765/items/ABCD1234','type':'article-journal',
       'title':'The Good Paper','author':[{'given':'Anna','family':'Rossi'}],
       'issued':{'date-parts':[[2025]]},'DOI':'10.5555/test-paper'}

class FakeWriter:
    server_id='test-server'
    def __init__(self): self.added=[];self.created=[]
    def connect(self): return self.server_id
    def ensure_collection(self,key):
        if key!='COLL1234':raise CatalogError('invalid collection')
    def add_to_collection(self,info,key):
        self.ensure_collection(key)
        self.added.append((info['key'],key));return True
    def create_item(self,record,key):
        self.ensure_collection(key)
        self.created.append((record['doi'],key))
        return ITEM

class CatalogTests(unittest.TestCase):
    def test_alias_is_persistent_and_not_duplicated(self):
        with tempfile.TemporaryDirectory() as tmp:
            db=Path(tmp)/'catalog.sqlite3'
            c=Catalog(db)
            one=c.register(doi='10.5555/test-paper',title='The Good Paper',year='2025',authors=[{'given':'Anna','family':'Rossi'}],origin='bibtex')
            self.assertEqual(c.alias(one['id']),'[[Z:00001]]')
            self.assertEqual(c.by_alias('[[Z:00001]]')['title'],'The Good Paper')
            two=c.register(doi='10.5555/test-paper',title='The Good Paper',year='2025',origin='crossref')
            self.assertEqual(one['id'],two['id'])
            c.close()
            d=Catalog(db)
            self.assertEqual(d.by_alias('00001')['doi'],'10.5555/test-paper')
            d.close()

    def test_catalog_sync_from_zotero_without_doi(self):
        with tempfile.TemporaryDirectory() as tmp:
            c=Catalog(Path(tmp)/'catalog.db')
            no_doi=json.loads(json.dumps(ITEM))
            no_doi['key']=no_doi['data']['key']='XYZW4321'
            no_doi['data']['DOI']=''
            no_doi['data']['title']='Book without DOI'
            class FakeLib:
                by_key={'ABCD1234':[item_info(ITEM)],'XYZW4321':[item_info(no_doi)]}
            self.assertEqual(c.ingest_zotero(FakeLib(),'serverX'),2)
            self.assertEqual(c.db.execute('select count(*) from references_catalog').fetchone()[0],2)
            self.assertEqual(c.all(20, 'Book')[0]['doi'],None)
            c.close()

    def test_alias_to_live_docx_with_existing_zotero_item(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)
            c=Catalog(folder/'cat.db')
            row=c.register(doi='10.5555/test-paper',title='The Good Paper',year='2025',origin='crossref')
            setting=folder/'settings.json'
            setting.write_text(json.dumps({'server_id':'test-server','collection_key':'COLL1234'}))
            resolver=CatalogResolver(c,auto_import=True,settings_file=setting)
            resolver.writer=FakeWriter(); resolver.server_id='test-server'
            info=item_info(ITEM)
            resolver.by_doi[info['doi']].append(info)
            resolver.by_key[info['key']].append(info)
            resolver.csl=lambda item: CSL
            doc=Document()
            doc.add_paragraph('Studio '+c.alias(row['id'])+'.')
            origin=folder/'original.docx'; out=folder/'out.docx'
            doc.save(origin)
            result=process(origin,out,resolver)
            self.assertEqual([x['esito'] for x in result].count('CONVERTITA'),1)
            self.assertEqual(resolver.writer.added,[('ABCD1234','COLL1234')])
            with zipfile.ZipFile(out) as f:
                xml=f.read('word/document.xml').decode()
                self.assertIn('ADDIN ZOTERO_ITEM CSL_CITATION',xml)
                self.assertNotIn('[[Z:00001]]',xml)
            c.close()

    def test_alias_imports_missing_item_after_collection_choice(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)
            c=Catalog(folder/'cat.db')
            row=c.register(doi='10.5555/test-paper',title='The Good Paper',year='2025',origin='crossref',
                           authors=[{'given':'Anna','family':'Rossi'}],meta={'type':'journal-article', 'container-title':'Journal of Tests'})
            setting=folder/'settings.json'
            setting.write_text(json.dumps({'server_id':'test-server','collection_key':'COLL1234'}))
            resolver=CatalogResolver(c,auto_import=True,settings_file=setting)
            resolver.writer=FakeWriter(); resolver.server_id='test-server'
            status, info, note=resolver.find('alias','1')
            self.assertEqual(status,'TROVATA')
            self.assertEqual(resolver.writer.created,[('10.5555/test-paper','COLL1234')])
            self.assertEqual(info['key'],'ABCD1234')
            self.assertEqual(c.by_alias('1')['zotero_key'],'ABCD1234')
            c.close()

    def test_not_selected_does_not_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            c=Catalog(Path(tmp)/'cat.db')
            c.register(doi='10.5555/test-paper',title='The Good Paper',origin='crossref')
            resolver=CatalogResolver(c,auto_import=True,settings_file=Path(tmp)/'missing.json')
            resolver.server_id='test-server'; resolver.writer=FakeWriter()
            status,_,_=resolver.find('alias','1')
            self.assertEqual(status,'RACCOLTA_NON_SCELTA')
            self.assertFalse(resolver.writer.created)
            c.close()

    def test_zotero_post_item_payload(self):
        with tempfile.TemporaryDirectory() as tmp:
            c=Catalog(Path(tmp)/'cat.db')
            row=c.register(doi='10.5555/test-paper',title='The Good Paper',year='2025',origin='crossref',
                           authors=[{'given':'Anna','family':'Rossi'}],meta={'type':'journal-article','container-title':'Journal of Testing'})
            writer=ZoteroWriter()
            writer.server_id='test-server'
            sent=[]
            writer.ensure_collection=lambda key: True
            writer.template=lambda item_type:{'itemType':item_type,'title':'','DOI':'','date':'','publicationTitle':'',
                                              'creators':[], 'collections':[], 'tags':[], 'relations':{}}
            def fake(path,method='GET',payload=None,params=None,write=False,token=False):
                if method=='POST':
                    sent.append((path,payload))
                    return {'success':{'0':'ABCD1234'}}
                return ITEM
            writer.request=fake
            obj=writer.create_item(row,'COLL1234')
            self.assertEqual(obj['key'],'ABCD1234')
            self.assertEqual(sent[0][0],'/users/0/items')
            self.assertEqual(sent[0][1][0]['collections'],['COLL1234'])
            self.assertEqual(sent[0][1][0]['creators'][0]['lastName'],'Rossi')
            c.close()


    def test_clean_test_document_only_contains_real_06937_alias(self):
        from docx import Document
        document=Path(__file__).parent/'Test_AutoCite_042_Frey_Osborne_PULITO.docx'
        content='\n'.join(paragraph.text for paragraph in Document(document).paragraphs)
        self.assertEqual(content.count('[[Z:06937]]'),2)
        self.assertEqual(content.count('[[ZBIB]]'),1)
        self.assertNotIn('[[Z:00421]]',content)

    def test_new_item_import_does_not_call_unavailable_local_template_endpoint(self):
        """Regression from live 0.4.1: local GET /items/new returned HTTP 404."""
        with tempfile.TemporaryDirectory() as tmp:
            c = Catalog(Path(tmp)/'test.sqlite3')
            row=c.register(doi='10.5555/test-paper',title='The Good Paper',year='2025',
                           authors=[{'given':'Anna','family':'Rossi'}],origin='crossref',
                           meta={'type':'journal-article','container-title':'Journal of Testing',
                                 'volume':'12','issue':'3','page':'14-19'})
            w=ZoteroWriter();w.server_id='test-server'
            w.ensure_collection=lambda key: self.assertEqual(key, 'COLL1234')
            calls=[]
            def fake(path,method='GET',payload=None,params=None,write=False,token=False):
                calls.append((method,path,payload))
                if path.endswith('/items/new'):
                    self.fail('0.4.2 must not GET /items/new from local Zotero')
                if method=='POST' and path=='/users/0/items':
                    self.assertTrue(write)
                    self.assertTrue(token)
                    self.assertEqual(payload[0]['itemType'],'journalArticle')
                    self.assertEqual(payload[0]['DOI'],'10.5555/test-paper')
                    self.assertEqual(payload[0]['title'],'The Good Paper')
                    self.assertEqual(payload[0]['publicationTitle'],'Journal of Testing')
                    self.assertEqual(payload[0]['collections'],['COLL1234'])
                    self.assertEqual(payload[0]['creators'][0]['lastName'],'Rossi')
                    return {'success':{'0':'ABCD1234'}}
                if method=='GET' and path=='/users/0/items/ABCD1234':
                    return ITEM
                self.fail(f'Unexpected API operation {method} {path}')
            w.request=fake
            result=w.create_item(row,'COLL1234')
            self.assertEqual(result['key'],'ABCD1234')
            self.assertEqual([(m,p) for m,p,_ in calls],
                             [('POST','/users/0/items'),('GET','/users/0/items/ABCD1234')])
            c.close()

    def test_failed_import_attempted_once_per_alias_per_document(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            c=Catalog(root/'cat.db')
            c.register(doi='10.5555/test-paper', title='The Good Paper', year='2025',
                       origin='crossref',authors=[{'family':'Rossi','given':'Anna'}])
            settings=root/'settings.json'
            settings.write_text(json.dumps({'server_id':'test-server','collection_key':'COLL1234'}))
            resolver=CatalogResolver(c, auto_import=True,settings_file=settings)
            class FailingWriter(FakeWriter):
                def create_item(self,record,key):
                    self.created.append((record['doi'],key))
                    raise CatalogError('write not supported in fake Zotero')
            resolver.writer=FailingWriter();resolver.server_id='test-server'
            first=resolver.find('alias','1')
            second=resolver.find('alias','1')
            self.assertEqual(first[0],'IMPORTAZIONE_FALLITA')
            self.assertEqual(second[0],'IMPORTAZIONE_FALLITA')
            self.assertEqual(len(resolver.writer.created),1)
            c.close()

if __name__ == '__main__':unittest.main()
