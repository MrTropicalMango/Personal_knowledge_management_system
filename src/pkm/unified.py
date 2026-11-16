"""Read-only queries across Zotero references and enriched Drive resources."""
from pathlib import Path
import sqlite3


def connection(db):
    conn = sqlite3.connect(Path(db).resolve().as_uri() + '?mode=ro', uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def has_drive(conn):
    return conn.execute("SELECT 1 FROM sqlite_master WHERE name='drive_search' AND type='table'").fetchone() is not None


def decorate(rows):
    results = []
    for item in rows:
        row = dict(item)
        row.setdefault('url', 'zotero://select/library/items/' + row['source_key'] if row['source'] == 'zotero-local-personal' else '')
        row.setdefault('metadata_status', 'Referencia bibliográfica importada')
        results.append(row)
    return results


def search_resources(db, query, limit=200):
    if not isinstance(query, str) or not query.strip():
        raise ValueError('Escribe una consulta de búsqueda.')
    if not 1 <= limit <= 1000:
        raise ValueError('El límite debe estar entre 1 y 1000.')
    expression = ' AND '.join('"' + w.replace('"', '""') + '"' for w in query.split())
    conn = connection(db)
    try:
        refs = conn.execute('SELECT r.id,r.source,r.source_key,r.title,r.authors,r.date,r.doi '
             'FROM references_fts JOIN references_catalog r ON r.id=references_fts.rowid '
             'WHERE references_fts MATCH ? ORDER BY rank,r.id LIMIT ?', (expression,limit)).fetchall()
        rows = decorate(refs)
        if has_drive(conn):
            drive = conn.execute("SELECT 'drive:'||r.drive_id AS id,'Google Drive' AS source,r.drive_id AS source_key,"
                "r.title,r.authors,'' AS date,'' AS doi,r.url,r.metadata_status "
                'FROM drive_search JOIN drive_bibliography r ON r.drive_id=drive_search.drive_id '
                'WHERE drive_search MATCH ? ORDER BY rank,r.title LIMIT ?', (expression,limit)).fetchall()
            rows += decorate(drive)
        # Interleave sources so one source cannot hide the other at the display limit.
        if has_drive(conn):
            left,right=rows[:len(refs)],rows[len(refs):]
            rows=[]
            for i in range(max(len(left),len(right))):
                if i<len(left):rows.append(left[i])
                if i<len(right):rows.append(right[i])
        return rows[:limit]
    finally:
        conn.close()


def list_resources(db, limit=200):
    conn=connection(db)
    try:
        conn.execute('SELECT title,authors FROM references_fts LIMIT 0')
        rows=decorate(conn.execute('SELECT id,source,source_key,title,authors,date,doi '
                    'FROM references_catalog ORDER BY title,id LIMIT ?', (limit,)).fetchall())
        if has_drive(conn):
            drive=decorate(conn.execute("SELECT 'drive:'||drive_id AS id,'Google Drive' AS source,drive_id AS source_key,"
                "title,authors,'' AS date,'' AS doi,url,metadata_status FROM drive_bibliography ORDER BY title LIMIT ?",(limit,)).fetchall())
            merged=[]
            for i in range(max(len(rows),len(drive))):
                if i<len(rows):merged.append(rows[i])
                if i<len(drive):merged.append(drive[i])
            rows=merged
        return rows[:limit]
    finally:
        conn.close()
