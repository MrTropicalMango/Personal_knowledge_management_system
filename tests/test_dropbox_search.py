import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from pkm.catalog import import_json
from pkm.unified import list_resources, search_resources


class DropboxSearchTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        root=Path(self.tmp.name);self.db=root/'test.sqlite'
        f=root/'refs.json';f.write_text(json.dumps([{'key':'Z1','title':'Aprendizaje ficticio'}]));import_json(self.db,f,'synthetic')
        with sqlite3.connect(self.db) as c:
            c.executescript('''CREATE TABLE dropbox_bibliography(resource_id TEXT PRIMARY KEY,title TEXT,authors TEXT,url TEXT,path TEXT,metadata_status TEXT);
            CREATE VIRTUAL TABLE dropbox_search USING fts5(resource_id UNINDEXED,title,authors,topics,tokenize='unicode61 remove_diacritics 2');''')
            c.execute('INSERT INTO dropbox_bibliography VALUES(?,?,?,?,?,?)',('DBX1','Aprendizaje: ejemplo','Ana Ficticia','https://www.dropbox.com/home/example.pdf','/example.pdf','Sintético'))
            c.execute('INSERT INTO dropbox_search VALUES(?,?,?,?)',('DBX1','Aprendizaje: ejemplo','Ana Ficticia','Memorización'))

    def test_search_includes_dropbox_and_references(self):
        rows=search_resources(self.db,'aprendizaje')
        self.assertEqual({r['source'] for r in rows},{'synthetic','Dropbox'})

    def test_contents_accent_insensitive_and_path(self):
        row=search_resources(self.db,'memorizacion')[0]
        self.assertEqual(row['source'],'Dropbox');self.assertEqual(row['path'],'/example.pdf')

    def test_listing_preserves_bytes_and_limits(self):
        before=self.db.read_bytes();rows=list_resources(self.db,2)
        self.assertEqual(len(rows),2);self.assertEqual(self.db.read_bytes(),before)
        self.assertEqual(len(list_resources(self.db,1)),1)

    def test_three_sources_interleave(self):
        with sqlite3.connect(self.db) as c:
            c.executescript('''CREATE TABLE drive_bibliography(drive_id TEXT PRIMARY KEY,title TEXT,authors TEXT,url TEXT,metadata_status TEXT);
            CREATE VIRTUAL TABLE drive_search USING fts5(drive_id UNINDEXED,title,authors,topics);''')
            c.execute('INSERT INTO drive_bibliography VALUES(?,?,?,?,?)',('G1','Aprendizaje Drive','','','Sintético'))
            c.execute('INSERT INTO drive_search VALUES(?,?,?,?)',('G1','Aprendizaje Drive','',''))
        self.assertEqual([r['source'] for r in search_resources(self.db,'aprendizaje',3)],['synthetic','Google Drive','Dropbox'])

    def block(self, source='Dropbox'):
        with sqlite3.connect(self.db) as c:
            c.execute('CREATE TABLE security_exclusions(source TEXT,source_key TEXT,reason TEXT)')
            c.execute('INSERT INTO security_exclusions VALUES(?,?,?)',(source,'DBX1','Synthetic security test'))

    def test_security_exclusion_hides_search(self):
        self.block()
        self.assertNotIn('Dropbox',{r['source'] for r in search_resources(self.db,'aprendizaje')})
        from pkm.unified import is_resource_excluded
        self.assertTrue(is_resource_excluded(self.db,'Dropbox','DBX1'))

    def test_security_exclusion_hides_listing(self):
        self.block()
        self.assertNotIn('Dropbox',{r['source'] for r in list_resources(self.db)})

    def test_security_exclusion_is_source_scoped(self):
        self.block('Google Drive')
        self.assertIn('Dropbox',{r['source'] for r in search_resources(self.db,'aprendizaje')})
