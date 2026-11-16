"""Offline, fictional demonstration of reference and resource search."""
import json
from pathlib import Path
import sqlite3
import tempfile
from pkm.catalog import import_json
from pkm.unified import search_resources


def main():
    with tempfile.TemporaryDirectory(prefix='pkm-unified-demo-') as folder:
        root = Path(folder)
        source = root / 'synthetic.json'
        source.write_text(json.dumps([{'key': 'SYNTHETIC1', 'title': 'Matemáticas sintéticas',
                                      'creators': [{'name': 'Instituto Ficticio'}]}]), encoding='utf-8')
        db = root / 'demo.sqlite'
        import_json(db, source, 'synthetic-library')
        with sqlite3.connect(db) as conn:
            conn.executescript('''
            CREATE TABLE drive_bibliography (
                drive_id TEXT PRIMARY KEY, title TEXT, authors TEXT, url TEXT, metadata_status TEXT);
            CREATE VIRTUAL TABLE drive_search USING fts5(
                drive_id UNINDEXED, title, authors, topics, tokenize='unicode61 remove_diacritics 2');
            ''')
            conn.execute('INSERT INTO drive_bibliography VALUES(?,?,?,?,?)',
                         ('SYNTHETIC-FILE', 'Matemáticas: cuaderno ficticio', 'Ana Ejemplo', '', 'Datos ficticios'))
            conn.execute('INSERT INTO drive_search VALUES(?,?,?,?)',
                         ('SYNTHETIC-FILE', 'Matemáticas: cuaderno ficticio', 'Ana Ejemplo', 'Autovalores sintéticos'))
        results = search_resources(db, 'matematicas')
        if {row['source_key'] for row in results} != {'SYNTHETIC1', 'SYNTHETIC-FILE'}:
            raise RuntimeError('Unified search did not return both fictional sources')
        if search_resources(db, 'autovalores')[0]['source_key'] != 'SYNTHETIC-FILE':
            raise RuntimeError('Contents search failed')
        print('PASS | Both fictional sources found; contents search passed.')
        print('No network requests, personal metadata, or real Drive identifiers used.')


if __name__ == '__main__':
    main()
