"""Read-only, interleaved search across references and private resource catalogs."""
from pathlib import Path
import sqlite3

# Identifiers below are fixed application schema, never user-supplied SQL.
RESOURCE_SOURCES = (
    ('kindle', 'kindle_search', 'kindle_bibliography', 'resource_id', 'Kindle'),
    ('kobo', 'kobo_search', 'kobo_bibliography', 'resource_id', 'Kobo'),
    ('applebooks', 'applebooks_search', 'applebooks_bibliography', 'resource_id', 'Apple Books'),
    ('drive', 'drive_search', 'drive_bibliography', 'drive_id', 'Google Drive'),
    ('dropbox', 'dropbox_search', 'dropbox_bibliography', 'resource_id', 'Dropbox'),
)


def connection(db):
    conn = sqlite3.connect(Path(db).resolve().as_uri() + '?mode=ro', uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def has_table(conn, name):
    return conn.execute("SELECT 1 FROM sqlite_master WHERE name=? AND type='table'", (name,)).fetchone() is not None


def has_drive(conn):
    return has_table(conn, 'drive_search')


def decorate(rows):
    results = []
    for item in rows:
        row = dict(item)
        row.setdefault('url', 'zotero://select/library/items/' + row['source_key'] if row['source'] == 'zotero-local-personal' else '')
        row.setdefault('metadata_status', 'Referencia bibliográfica importada')
        row.setdefault('path', '')
        results.append(row)
    return results


def interleave(groups, limit):
    result=[]
    for index in range(max((len(group) for group in groups), default=0)):
        for group in groups:
            if index < len(group):result.append(group[index])
            if len(result) == limit:return result
    return result


def is_resource_excluded(db, source, source_key):
    conn=connection(db)
    try:
        if not has_table(conn,'security_exclusions'):
            return False
        return conn.execute('SELECT 1 FROM security_exclusions WHERE source=? AND source_key=?', (source,source_key)).fetchone() is not None
    finally:
        conn.close()


def resource_groups(conn, limit, expression=None):
    groups=[]
    guarded=has_table(conn,'security_exclusions')
    for prefix, fts, table, key, label in RESOURCE_SOURCES:
        if not has_table(conn,fts):continue
        path='r.path' if prefix=='dropbox' else "''"
        select=(f"SELECT '{prefix}:'||r.{key} AS id,? AS source,r.{key} AS source_key,"
                f"r.title,r.authors,'' AS date,'' AS doi,r.url,r.metadata_status,{path} AS path ")
        blocked=(f'NOT EXISTS (SELECT 1 FROM security_exclusions e WHERE e.source=? AND e.source_key=r.{key})') if guarded else '1=1'
        params=[label]
        if expression is None:
            sql=select+f'FROM {table} r WHERE '+blocked+f' ORDER BY r.title,r.{key} LIMIT ?'
        else:
            sql=select+f'FROM {fts} JOIN {table} r ON r.{key}={fts}.{key} WHERE {fts} MATCH ? AND '+blocked+' ORDER BY rank,r.title LIMIT ?'
            params.append(expression)
        if guarded:params.append(label)
        params.append(limit)
        groups.append(decorate(conn.execute(sql,params).fetchall()))
    return groups


def validate_limit(limit):
    if not isinstance(limit,int) or not 1 <= limit <= 1000:
        raise ValueError('El límite debe estar entre 1 y 1000.')


def search_resources(db, query, limit=200):
    if not isinstance(query,str) or not query.strip():
        raise ValueError('Escribe una consulta de búsqueda.')
    validate_limit(limit)
    expression=' AND '.join('"'+word.replace('"','""')+'"' for word in query.split())
    conn=connection(db)
    try:
        refs=decorate(conn.execute('SELECT r.id,r.source,r.source_key,r.title,r.authors,r.date,r.doi '
            'FROM references_fts JOIN references_catalog r ON r.id=references_fts.rowid '
            'WHERE references_fts MATCH ? ORDER BY rank,r.id LIMIT ?', (expression,limit)).fetchall())
        return interleave([refs]+resource_groups(conn,limit,expression),limit)
    finally:
        conn.close()


def list_resources(db, limit=200):
    validate_limit(limit)
    conn=connection(db)
    try:
        conn.execute('SELECT title,authors FROM references_fts LIMIT 0')
        refs=decorate(conn.execute('SELECT id,source,source_key,title,authors,date,doi '
                    'FROM references_catalog ORDER BY title,id LIMIT ?', (limit,)).fetchall())
        return interleave([refs]+resource_groups(conn,limit),limit)
    finally:
        conn.close()
