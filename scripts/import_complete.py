"""Private, read-only Zotero snapshot import. No remote services or library writes."""
import collections
import datetime
import json
import os
from pathlib import Path
import sqlite3
import urllib.parse
import urllib.request
from pkm.catalog import import_json

BASE = 'http://127.0.0.1:23119/api'
EXCLUDE = '-attachment || note || annotation'
FIELDS = ('key', 'version', 'itemType', 'title', 'creators', 'date', 'DOI', 'ISBN',
          'ISSN', 'abstractNote', 'language', 'tags', 'collections', 'url',
          'publisher', 'publicationTitle', 'edition', 'volume', 'issue', 'pages',
          'place', 'series', 'university', 'bookTitle', 'shortTitle', 'accessDate')


def get(route, **params):
    url = BASE + route + ('?' + urllib.parse.urlencode(params) if params else '')
    request = urllib.request.Request(url, headers={'Zotero-API-Version': '3'})
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def pages(route, **params):
    result = []
    while True:
        page = get(route, start=len(result), limit=100, **params)
        if not isinstance(page, list):
            raise ValueError('Respuesta inesperada al paginar Zotero.')
        result.extend(page)
        if len(page) < 100:
            return result


def main():
    global EXCLUDE
    EXCLUDE = ' || '.join(x['itemType'] for x in get('/itemTypes') if x['itemType'] not in ('attachment', 'note', 'annotation'))
    os.umask(0o077)
    root = Path(__file__).resolve().parents[1]
    run = root / 'data' / ('zotero-full-' + datetime.datetime.now().strftime('%Y%m%d-%H%M%S'))
    run.mkdir(parents=True, mode=0o700)
    groups = pages('/users/0/groups', format='json')
    libraries = [('personal', '/users/0')]
    for group in groups:
        identifier = group.get('id') or group.get('data', {}).get('id')
        if identifier is None:
            raise ValueError('Grupo sin identificador; no se omitirá silenciosamente.')
        libraries.append((f'group-{identifier}', f'/groups/{identifier}'))
    db = run / 'catalog.sqlite'
    summary = []
    for name, route in libraries:
        records = None
        for attempt in range(3):
            before = get(route + '/items', format='versions', itemType=EXCLUDE)
            items = pages(route + '/items', format='json', itemType=EXCLUDE, sort='dateAdded', direction='asc')
            after = get(route + '/items', format='versions', itemType=EXCLUDE)
            keys = [item.get('key', item.get('data', {}).get('key')) for item in items]
            if before == after and set(keys) == set(before) and len(keys) == len(set(keys)):
                records = items
                break
        if records is None:
            raise RuntimeError('La biblioteca cambió durante la lectura; repite la importación.')
        metadata = []
        for item in records:
            data = item.get('data', item)
            if data.get('itemType') in ('attachment', 'note', 'annotation'):
                raise ValueError('El filtro de bibliografía devolvió un elemento no bibliográfico.')
            metadata.append({key: data[key] for key in FIELDS if key in data})
        missing_titles = []
        for record in metadata:
            if not isinstance(record.get('title'), str) or not record['title'].strip():
                missing_titles.append(record['key'])
                record['_pkm_import'] = {'missing_source_title': True, 'original_title': record.get('title')}
                record['title'] = '[Sin título en Zotero · ' + record['key'] + ']'
        path = run / (name + '.json')
        path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + '\n')
        collection_data = pages(route + '/collections', format='json')
        (run / (name + '-collections.json')).write_text(json.dumps(collection_data, ensure_ascii=False, indent=2) + '\n')
        source = 'zotero-local-' + name
        first = import_json(db, path, source)
        second = import_json(db, path, source)
        if second['inserted'] or second['updated'] or second['unchanged'] != len(metadata):
            raise RuntimeError('Falló la comprobación de idempotencia.')
        with sqlite3.connect(db) as connection:
            count = connection.execute('SELECT count(*) FROM references_catalog WHERE source=?', (source,)).fetchone()[0]
            if count != len(metadata):
                raise RuntimeError('Recuento de destino diferente al origen.')
        summary.append({'library': name, 'references': count, 'collections': len(collection_data),
                        'missing_source_titles': len(missing_titles), 'types': dict(collections.Counter(x.get('itemType', '') for x in metadata)),
                        'first_import': first, 'repeat_import': second})
    if not db.exists():
        raise RuntimeError('No se creó el catálogo.')
    with sqlite3.connect(db) as connection:
        if connection.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
            raise RuntimeError('Falló la integridad de SQLite.')
        connection.execute("INSERT INTO references_fts(references_fts,rank) VALUES('integrity-check',1)")
    report = {'status': 'complete', 'scope': 'all accessible local personal and group libraries; excludes trash, notes, attachments and annotations',
              'libraries': summary, 'total_references': sum(x['references'] for x in summary),
              'database': str(db), 'source_writes': False, 'uploaded': False}
    (run / 'verification.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
