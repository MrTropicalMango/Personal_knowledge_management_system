import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from pkm.catalog import import_json, search


class CatalogTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.db = self.root / 'catalog.sqlite'
        self.file = self.root / 'input.json'
        self.items = [{'key': 'A1', 'title': 'Aprendizaje sintético',
                       'creators': [{'firstName': 'Ana', 'lastName': 'García'}]}]

    def save(self, items):
        self.file.write_text(json.dumps(items), encoding='utf-8')

    def test_import_search_and_idempotence(self):
        self.save(self.items)
        original = self.file.read_bytes()
        self.assertEqual(import_json(self.db, self.file)['inserted'], 1)
        self.assertEqual(search(self.db, 'garcia')[0]['source_key'], 'A1')
        self.assertEqual(import_json(self.db, self.file)['unchanged'], 1)
        self.assertEqual(self.file.read_bytes(), original)

    def test_update_refreshes_index(self):
        self.save(self.items)
        import_json(self.db, self.file)
        self.items[0]['title'] = 'Robótica'
        self.save(self.items)
        self.assertEqual(import_json(self.db, self.file)['updated'], 1)
        self.assertEqual(search(self.db, 'Aprendizaje'), [])
        self.assertEqual(len(search(self.db, 'robotica')), 1)

    def test_validation_leaves_existing_catalog_unchanged(self):
        self.save(self.items)
        import_json(self.db, self.file)
        self.save([{'key': 'B', 'title': 'Nuevo'}, {'key': 'C'}])
        with self.assertRaises(ValueError):
            import_json(self.db, self.file)
        with sqlite3.connect(self.db) as conn:
            self.assertEqual(conn.execute('SELECT count(*) FROM references_catalog').fetchone()[0], 1)

    def test_duplicate_input_keys_rejected(self):
        self.save(self.items * 2)
        with self.assertRaises(ValueError):
            import_json(self.db, self.file)
        self.assertFalse(self.db.exists())

    def test_api_envelope_and_library_namespaces(self):
        self.save([{'key': 'A1', 'data': {'title': 'Prueba', 'creators': [{'name': 'Instituto'}]}}])
        import_json(self.db, self.file, 'library-one')
        import_json(self.db, self.file, 'library-two')
        self.assertEqual(len(search(self.db, 'Instituto')), 2)

    def test_invalid_json_and_input_types(self):
        for payload in ({}, [None], [{'key': 'A', 'title': 'T', 'creators': None}]):
            self.save(payload)
            with self.assertRaises(ValueError):
                import_json(self.db, self.file)
        self.file.write_text('{')
        with self.assertRaises(ValueError):
            import_json(self.db, self.file)

    def test_source_and_destination_must_differ(self):
        self.save(self.items)
        with self.assertRaises(ValueError):
            import_json(self.file, self.file)

    def test_search_does_not_create_database(self):
        with self.assertRaises(sqlite3.OperationalError):
            search(self.db, 'hello')
        self.assertFalse(self.db.exists())


if __name__ == '__main__':
    unittest.main()
