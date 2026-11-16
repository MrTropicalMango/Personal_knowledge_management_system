import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from pkm.catalog import import_json
from pkm.gui import list_records


class InterfaceCatalogTests(unittest.TestCase):
    def test_catalog_rows_include_details(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / 'synthetic.json'
            source.write_text(json.dumps([{'key': 'DEMO1', 'title': 'Ejemplo ficticio', 'DOI': 'synthetic-only'}]))
            db = root / 'catalog.sqlite'
            import_json(db, source, 'demo')
            rows = list_records(db)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]['source_key'], 'DEMO1')
            self.assertEqual(rows[0]['doi'], 'synthetic-only')

    def test_unrelated_database_remains_unchanged(self):
        with tempfile.TemporaryDirectory() as folder:
            db = Path(folder) / 'other.sqlite'
            with sqlite3.connect(db) as connection:
                connection.execute('CREATE TABLE unrelated (value TEXT)')
            original = db.read_bytes()
            with self.assertRaises(sqlite3.OperationalError):
                list_records(db)
            self.assertEqual(db.read_bytes(), original)

    def test_missing_database_is_not_created(self):
        with tempfile.TemporaryDirectory() as folder:
            db = Path(folder) / 'missing.sqlite'
            with self.assertRaises(sqlite3.OperationalError):
                list_records(db)
            self.assertFalse(db.exists())
