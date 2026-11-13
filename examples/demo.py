"""Reproducible, offline demo; uses a fresh temporary database on every run."""
import copy
import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile

from pkm.catalog import import_json, search


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def main():
    source = Path(__file__).with_name('references.synthetic.json')
    original = source.read_bytes()
    items = json.loads(original)
    with tempfile.TemporaryDirectory(prefix='pkm-synthetic-') as folder:
        db = Path(folder) / 'demo.sqlite'
        first = import_json(db, source, 'synthetic-demo')
        repeat = import_json(db, source, 'synthetic-demo')
        matches = search(db, 'aprendizaje')
        creators = search(db, 'ejemplo')
        changed = copy.deepcopy(items)
        changed[0]['title'] = 'Robótica sintética: demostración de actualización'
        update_file = Path(folder) / 'updated.json'
        update_file.write_text(json.dumps(changed, ensure_ascii=False), encoding='utf-8')
        update = import_json(db, update_file, 'synthetic-demo')
        updated_matches = search(db, 'robotica')
        with sqlite3.connect(db) as connection:
            stored = connection.execute('SELECT count(*) FROM references_catalog').fetchone()[0]
        require(first['inserted'] == 10, 'Expected 10 new records')
        require(repeat['inserted'] == 0 and repeat['unchanged'] == 10, 'Repeat import changed records')
        require(len(matches) == len(creators) == 10, 'Search did not return all demo records')
        require(update['updated'] == 1 and update['unchanged'] == 9, 'Update counts differ')
        require(len(updated_matches) == 1 and updated_matches[0]['source_key'] == items[0]['key'], 'FTS update failed')
        require(len(search(db, 'aprendizaje')) == 9 and stored == 10, 'Stale search index or duplicate')
        require(source.read_bytes() == original, 'Source fixture changed')
        print('PKM | Synthetic demonstration')
        print('Data: 10 fictional records. No Zotero connection. No network requests.')
        print('1. First import:      10 inserted')
        print('2. Repeat import:      0 inserted; 10 unchanged')
        print('3. Title search:      10 results for "aprendizaje"')
        print('4. Creator search:    10 results for "ejemplo"')
        print('5. Update one title:   1 updated; 9 unchanged')
        print('6. Accent-free search: 1 result for "robotica"')
        print('7. Final catalog:     10 records; source file unchanged')
        print('PASS | All checks passed. Temporary database removed on exit.')
        print('Fixture SHA-256: ' + hashlib.sha256(original).hexdigest())


if __name__ == '__main__':
    main()
