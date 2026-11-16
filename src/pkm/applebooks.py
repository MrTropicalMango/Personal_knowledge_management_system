"""Import only allowlisted metadata from a read-only Apple Books snapshot."""
import json
from pathlib import Path
import sqlite3

FIELDS = ('Z_PK','ZASSETID','ZTITLE','ZAUTHOR','ZYEAR','ZCONTENTTYPE',
          'ZISSAMPLE','ZISHIDDEN','ZGENRE','ZLANGUAGE','ZSERIESID')

def read_snapshot(snapshot):
    conn = sqlite3.connect(Path(snapshot).resolve().as_uri()+'?mode=ro', uri=True)
    conn.row_factory = sqlite3.Row
    try:
        if conn.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
            raise ValueError('La copia de Apple Books no supera la comprobación de integridad.')
        columns = {r[1] for r in conn.execute('PRAGMA table_info(ZBKLIBRARYASSET)')}
        if not set(FIELDS).issubset(columns):
            raise ValueError('Esquema de Apple Books incompatible; no se importó nada.')
        rows = [dict(r) for r in conn.execute('SELECT '+','.join(FIELDS)+' FROM ZBKLIBRARYASSET ORDER BY Z_PK')]
    finally:
        conn.close()
    records, series, seen = [], [], set()
    for row in rows:
        key = str(row['ZASSETID'] or ('local-row:'+str(row['Z_PK'])))
        if key in seen:
            raise ValueError('Identificador repetido en Apple Books; revisar antes de importar.')
        seen.add(key)
        if row['ZCONTENTTYPE'] == 5:
            series.append({'key':key,'title':row['ZTITLE'] or ''})
            continue
        sample = bool(row['ZISSAMPLE'])
        records.append({'key':key,'title':(row['ZTITLE'] or '').strip() or '[Sin título en Apple Books]',
            'authors':row['ZAUTHOR'] or '', 'date':row['ZYEAR'] or '',
            'content_type':row['ZCONTENTTYPE'],'is_sample':sample,'is_hidden':bool(row['ZISHIDDEN']),
            'genre':row['ZGENRE'] or '', 'language':row['ZLANGUAGE'] or '',
            'series_id':row['ZSERIESID'] or '',
            'metadata_status':('Muestra; disponibilidad parcial' if sample else 'Metadatos de Apple Books; disponibilidad de lectura sin verificar')})
    return records, series


def import_snapshot(db, snapshot):
    if Path(db).resolve() == Path(snapshot).resolve():
        raise ValueError('El destino no puede ser la biblioteca de origen.')
    records, series = read_snapshot(snapshot)
    conn = sqlite3.connect(db)
    stats = {'inserted':0,'updated':0,'unchanged':0,'total':len(records),
             'series_excluded':len(series),'samples':sum(r['is_sample'] for r in records)}
    try:
        conn.executescript('''
        CREATE TABLE IF NOT EXISTS applebooks_bibliography (
            resource_id TEXT PRIMARY KEY,title TEXT NOT NULL,authors TEXT NOT NULL,
            url TEXT NOT NULL,metadata_status TEXT NOT NULL,metadata_json TEXT NOT NULL);
        CREATE VIRTUAL TABLE IF NOT EXISTS applebooks_search USING fts5(
            resource_id UNINDEXED,title,authors,topics,tokenize='unicode61 remove_diacritics 2');
        ''')
        with conn:
            for row in records:
                key=row['key']
                values=(row['title'],row['authors'],'',row['metadata_status'],json.dumps(row,ensure_ascii=False,sort_keys=True))
                old=conn.execute('SELECT title,authors,url,metadata_status,metadata_json FROM applebooks_bibliography WHERE resource_id=?',(key,)).fetchone()
                if old == values:
                    stats['unchanged']+=1
                    continue
                conn.execute('INSERT OR REPLACE INTO applebooks_bibliography VALUES(?,?,?,?,?,?)',(key,*values))
                conn.execute('DELETE FROM applebooks_search WHERE resource_id=?',(key,))
                conn.execute('INSERT INTO applebooks_search VALUES(?,?,?,?)',(key,row['title'],row['authors'],row['genre']))
                stats['inserted' if old is None else 'updated']+=1
    finally:
        conn.close()
    return stats
