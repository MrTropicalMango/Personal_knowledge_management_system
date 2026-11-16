import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from pkm.catalog import import_json
from pkm.unified import list_resources, search_resources


class UnifiedTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.db=Path(self.tmp.name)/'catalog.sqlite'
        src=Path(self.tmp.name)/'input.json'
        src.write_text(json.dumps([{'key':'TEST1','title':'Matemáticas sintéticas'}]))
        import_json(self.db,src,'zotero-local-personal')

    def drive(self):
        with sqlite3.connect(self.db) as c:
            c.executescript('CREATE TABLE drive_bibliography (drive_id TEXT PRIMARY KEY,title TEXT,authors TEXT,url TEXT,metadata_status TEXT); CREATE VIRTUAL TABLE drive_search USING fts5(drive_id UNINDEXED,title,authors,topics);')
            c.execute('INSERT INTO drive_bibliography VALUES(?,?,?,?,?)',('FILE1','Matemáticas en Drive','Ana Ejemplo','https://drive.google.com/file/d/FILE1/view','Candidato interno'))
            c.execute('INSERT INTO drive_search VALUES(?,?,?,?)',('FILE1','Matemáticas en Drive','Ana Ejemplo','Autovalores sintéticos'))

    def test_old_catalog_compatible(self):
        self.assertEqual(search_resources(self.db,'matematicas')[0]['source_key'],'TEST1')

    def test_both_sources_searchable(self):
        self.drive(); rows=search_resources(self.db,'matematicas')
        self.assertEqual({r['source_key'] for r in rows},{'FILE1','TEST1'})

    def test_contents_and_author_search(self):
        self.drive()
        self.assertEqual(search_resources(self.db,'autovalores')[0]['source_key'],'FILE1')
        self.assertEqual(search_resources(self.db,'Ejemplo')[0]['source_key'],'FILE1')

    def test_read_only_and_links(self):
        self.drive(); before=self.db.read_bytes()
        rows=search_resources(self.db,'matematicas');list_resources(self.db)
        self.assertEqual(self.db.read_bytes(),before)
        self.assertTrue(rows[1]['url'].startswith('https://drive.google.com/'))
        self.assertIn('metadata_status',rows[1])

    def test_limit_and_validation(self):
        self.drive();self.assertEqual(len(list_resources(self.db,1)),1)
        self.assertEqual(len(search_resources(self.db,'matematicas',1)),1)
        with self.assertRaises(ValueError):search_resources(self.db,'')

    def test_missing_does_not_create(self):
        path=Path(self.tmp.name)/'missing.sqlite'
        with self.assertRaises(sqlite3.OperationalError):list_resources(path)
        self.assertFalse(path.exists())
