import hashlib,plistlib,sqlite3,tempfile,unittest
from pathlib import Path
from pkm.kindle import import_snapshot,read_snapshot,unpack
from pkm.catalog import connect
from pkm.unified import search_resources

class KindleTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  self.source=Path(self.tmp.name)/'source.sqlite';self.db=Path(self.tmp.name)/'pkm.sqlite';connect(self.db).close()
  self.meta={'authors':{'author':['Ana Sintética','Instituto ficticio']},'cde_contenttype':'EBOK','origins':{'origin':{'type':'Purchase','id':'SECRET-ORDER'}},'publication_date':'2020-01-01'}
  with sqlite3.connect(self.source) as c:
   c.execute('CREATE TABLE ZBOOK(ZBOOKID TEXT,ZDISPLAYTITLE TEXT,ZRAWBOOKTYPE INTEGER,ZLANGUAGE TEXT,ZISHIDDENBYUSER INTEGER,ZSYNCMETADATAATTRIBUTES BLOB)')
   c.execute('INSERT INTO ZBOOK VALUES(?,?,?,?,?,?)',('A:SYNTH-0','Aprendizaje sintético',10,'es',0,self.blob()))
 def blob(self):return plistlib.dumps({'$objects':[None,{'attributes':self.meta}],'$top':{'root':plistlib.UID(1)}},fmt=plistlib.FMT_BINARY)
 def test_idempotence_search_and_readonly_source(self):
  before=hashlib.sha256(self.source.read_bytes()).digest()
  self.assertEqual(import_snapshot(self.db,self.source)['inserted'],1)
  self.assertEqual(import_snapshot(self.db,self.source)['unchanged'],1)
  self.assertEqual(search_resources(self.db,'aprendizaje')[0]['source'],'Kindle')
  self.assertEqual(hashlib.sha256(self.source.read_bytes()).digest(),before)
 def test_author_decode_and_no_order_identifiers(self):
  rows,_=read_snapshot(self.source)
  self.assertIn('Ana Sintética',rows[0]['authors']);self.assertNotIn('SECRET-ORDER',str(rows))
 def test_samples_and_incomplete_records(self):
  self.meta['cde_contenttype']='EBSP'
  with sqlite3.connect(self.source) as c:
   c.execute('UPDATE ZBOOK SET ZSYNCMETADATAATTRIBUTES=?',(self.blob(),))
   c.execute('INSERT INTO ZBOOK VALUES(?,?,?,?,?,?)',('unknown','Unknown',17,None,0,None))
  rows,review=read_snapshot(self.source);self.assertTrue(rows[0]['is_sample']);self.assertEqual(len(review),1)
 def test_update_refreshes_search_and_collision_rejected(self):
  import_snapshot(self.db,self.source)
  with sqlite3.connect(self.source) as c:c.execute("UPDATE ZBOOK SET ZDISPLAYTITLE='Robótica ficticia'")
  import_snapshot(self.db,self.source)
  self.assertFalse(search_resources(self.db,'aprendizaje'));self.assertEqual(len(search_resources(self.db,'robotica')),1)
  with self.assertRaises(ValueError):import_snapshot(self.source,self.source)
