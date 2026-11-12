"""Local bibliographic JSON import; no network or source-library writes."""
import json
import sqlite3
from pathlib import Path


def normalize(items):
    if not isinstance(items, list):
        raise ValueError('El JSON debe contener una lista de referencias.')
    records = []
    seen = set()
    for index, item in enumerate(items, 1):
        if not isinstance(item, dict):
            raise ValueError(f'Referencia {index}: se esperaba un objeto.')
        # Accept Zotero export objects and API envelopes with a data object.
        data = item.get('data', item)
        if not isinstance(data, dict):
            raise ValueError(f'Referencia {index}: data debe ser un objeto.')
        key = data.get('key') or item.get('key')
        title = data.get('title')
        if not isinstance(key, str) or not key.strip():
            raise ValueError(f'Referencia {index}: falta key de origen.')
        if not isinstance(title, str) or not title.strip():
            raise ValueError(f'Referencia {index}: falta title.')
        key = key.strip()
        if key in seen:
            raise ValueError(f'Referencia {index}: key repetida en el archivo: {key}.')
        seen.add(key)
        creators = data.get('creators', [])
        if not isinstance(creators, list):
            raise ValueError(f'Referencia {index}: creators debe ser una lista.')
        names = []
        for creator in creators:
            if not isinstance(creator, dict):
                raise ValueError(f'Referencia {index}: creator inválido.')
            parts = [creator.get('firstName', ''), creator.get('lastName', '')]
            name = creator.get('name') or ' '.join(p for p in parts if isinstance(p, str) and p)
            if not isinstance(name, str):
                raise ValueError(f'Referencia {index}: nombre inválido.')
            if name.strip():
                names.append(name.strip())
        fields = []
        for field in ('date', 'DOI', 'itemType'):
            value = data.get(field, '')
            if not isinstance(value, str):
                raise ValueError(f'Referencia {index}: {field} debe ser texto.')
            fields.append(value.strip())
        records.append((key, title.strip(), '; '.join(names), *fields,
                        json.dumps(item, ensure_ascii=False, sort_keys=True)))
    return records


def connect(path):
    connection = sqlite3.connect(path)
    try:
        connection.executescript('''
        CREATE TABLE IF NOT EXISTS references_catalog (
            id INTEGER PRIMARY KEY, source TEXT NOT NULL, source_key TEXT NOT NULL,
            title TEXT NOT NULL, authors TEXT NOT NULL, date TEXT NOT NULL,
            doi TEXT NOT NULL, item_type TEXT NOT NULL, raw_json TEXT NOT NULL,
            UNIQUE(source, source_key));
        CREATE VIRTUAL TABLE IF NOT EXISTS references_fts USING fts5(
            title, authors, content='references_catalog', content_rowid='id',
            tokenize='unicode61 remove_diacritics 2');
        CREATE TRIGGER IF NOT EXISTS references_insert AFTER INSERT ON references_catalog BEGIN
            INSERT INTO references_fts(rowid,title,authors) VALUES(new.id,new.title,new.authors);
        END;
        CREATE TRIGGER IF NOT EXISTS references_update AFTER UPDATE ON references_catalog BEGIN
            INSERT INTO references_fts(references_fts,rowid,title,authors)
                VALUES('delete',old.id,old.title,old.authors);
            INSERT INTO references_fts(rowid,title,authors) VALUES(new.id,new.title,new.authors);
        END;
        ''')
    except Exception:
        connection.close()
        raise
    return connection


def import_json(db, input_path, source='zotero'):
    if not isinstance(source, str) or not source.strip():
        raise ValueError('source no puede estar vacío.')
    if Path(db).resolve() == Path(input_path).resolve():
        raise ValueError('La base de datos no puede ser el archivo de entrada.')
    # Validate everything before opening the destination; imports are atomic.
    records = normalize(json.loads(Path(input_path).read_text(encoding='utf-8-sig')))
    stats = {'inserted': 0, 'updated': 0, 'unchanged': 0, 'total': len(records)}
    connection = connect(db)
    try:
        with connection:
            for record in records:
                key, *values = record
                previous = connection.execute(
                    'SELECT title,authors,date,doi,item_type,raw_json FROM references_catalog '
                    'WHERE source=? AND source_key=?', (source.strip(), key)).fetchone()
                if previous is None:
                    connection.execute('INSERT INTO references_catalog '
                        '(source,source_key,title,authors,date,doi,item_type,raw_json) '
                        'VALUES(?,?,?,?,?,?,?,?)', (source.strip(), key, *values))
                    stats['inserted'] += 1
                elif previous == tuple(values):
                    stats['unchanged'] += 1
                else:
                    connection.execute('UPDATE references_catalog SET title=?,authors=?,date=?,doi=?,item_type=?,raw_json=? '
                                       'WHERE source=? AND source_key=?', (*values, source.strip(), key))
                    stats['updated'] += 1
    finally:
        connection.close()
    return stats


def search(db, query, limit=20):
    if not query.strip():
        raise ValueError('La consulta no puede estar vacía.')
    if not 1 <= limit <= 1000:
        raise ValueError('limit debe estar entre 1 y 1000.')
    # Treat input as literal words, rather than exposing FTS query syntax.
    expression = ' AND '.join('"' + word.replace('"', '""') + '"' for word in query.split())
    uri = Path(db).resolve().as_uri() + '?mode=ro'
    connection = sqlite3.connect(uri, uri=True)
    connection.row_factory = sqlite3.Row
    try:
        rows = connection.execute('SELECT r.id,r.source,r.source_key,r.title,r.authors,r.date,r.doi '
            'FROM references_fts JOIN references_catalog r ON r.id=references_fts.rowid '
            'WHERE references_fts MATCH ? ORDER BY rank,r.id LIMIT ?', (expression, limit)).fetchall()
        return [dict(row) for row in rows]
    finally:
        connection.close()
