import hashlib
from pathlib import Path
import sqlite3
import tempfile
import unittest
from pkm.applebooks import import_snapshot, read_snapshot
from pkm.catalog import connect
from pkm.unified import search_resources

class AppleBooksTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.source=Path(self.tmp.name)/'source.sqlite'; self.db=Path(self.tmp.name)/'pkm.sqlite'
        connect(self.db).close()
        with sqlite3.connect(self.source) as c:
            c.execute('CREATE TABLE ZBKLIBRARYASSET (Z_PK INTEGER,ZASSETID TEXT,ZTITLE TEXT,ZAUTHOR TEXT,ZYEAR TEXT,ZCONTENTTYPE INTEGER,ZISSAMPLE INTEGER,ZISHIDDEN INTEGER,ZGENRE TEXT,ZLANGUAGE TEXT,ZSERIESID TEXT,ZACCOUNTID TEXT)')
            c.executemany('INSERT INTO ZBKLIBRARYASSET VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',[
                (1,'book','Aprendizaje ficticio','Autora sintética','2020',1,0,0,'Educación','es',None,'SECRET'),
                (2,'series','Serie ficticia','Autora sintética',None,5,0,0,None,None,None,'SECRET'),
                (3,'sample','Muestra ficticia','Autora sintética',None,1,1,0,None,None,None,'SECRET')])
    def test_import_is_idempotent_and_source_unchanged(self):
        before=hashlib.sha256(self.source.read_bytes()).digest()
        stats=import_snapshot(self.db,self.source)
        self.assertEqual((stats['inserted'],stats['series_excluded'],stats['samples']),(2,1,1))
        self.assertEqual(import_snapshot(self.db,self.source)['unchanged'],2)
        self.assertEqual(hashlib.sha256(self.source.read_bytes()).digest(),before)
        self.assertEqual(search_resources(self.db,'aprendizaje')[0]['source'],'Apple Books')
    def test_private_fields_not_imported(self):
        records,_=read_snapshot(self.source)
        self.assertNotIn('SECRET',str(records))
        self.assertTrue(records[1]['is_sample'])
    def test_update_removes_old_fts_text(self):
        import_snapshot(self.db,self.source)
        with sqlite3.connect(self.source) as c:c.execute("UPDATE ZBKLIBRARYASSET SET ZTITLE='Robótica sintética' WHERE Z_PK=1")
        self.assertEqual(import_snapshot(self.db,self.source)['updated'],1)
        self.assertFalse(search_resources(self.db,'aprendizaje'))
        self.assertEqual(len(search_resources(self.db,'robotica')),1)
    def test_incompatible_schema_does_not_write_destination(self):
        with sqlite3.connect(self.source) as c:c.execute('DROP TABLE ZBKLIBRARYASSET')
        other=Path(self.tmp.name)/'unused.sqlite'
        with self.assertRaises(ValueError):import_snapshot(other,self.source)
        self.assertFalse(other.exists())
