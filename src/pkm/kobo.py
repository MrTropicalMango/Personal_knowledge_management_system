"""Import allowlisted Kobo metadata, separating previews and unowned cache rows."""
import json
from pathlib import Path
import sqlite3

FIELDS=('ContentID','ContentType','MimeType','BookID','Title','Attribution','Publisher',
        'ISBN','Language','Series','SeriesNumber','Subtitle','IsDownloaded','Accessibility',
        'InWishlist','DateCreated','expiration_status','has_account')

def normalize_metadata(rows):
    records,review,seen=[],[],set()
    stats={'internal_rows_excluded':0,'review_only':0,'previews':0,'downloaded_full':0}
    for raw in rows:
        if not isinstance(raw,dict) or not set(FIELDS).issubset(raw):
            raise ValueError('Metadatos Kobo incompletos.')
        if raw['BookID']:
            stats['internal_rows_excluded']+=1
            continue
        key=raw['ContentID']
        if not isinstance(key,str) or not key.strip() or key in seen:
            raise ValueError('Identificador Kobo ausente o repetido.')
        seen.add(key)
        row={k:raw[k] for k in FIELDS}
        access=int(row['Accessibility'])
        downloaded=str(row['IsDownloaded']).lower() in ('true','1')
        expired=row['expiration_status']==3
        preview=access==6
        row['is_preview']=preview
        row['is_downloaded']=downloaded
        # Retain only explicitly linked library entries or downloaded sideloads.
        owned=bool(row['has_account']) and access in (1,2,6,8,9)
        local=access==-1 and downloaded
        if not (owned or local) or expired:
            row['metadata_status']='Revisión pendiente; no contar como recurso disponible'
            review.append(row);stats['review_only']+=1
            continue
        if preview:
            status='Vista previa; acceso parcial';stats['previews']+=1
        elif downloaded:
            status='Biblioteca Kobo; marcado como descargado; lectura no comprobada'
            stats['downloaded_full']+=1
        else:
            status='Biblioteca Kobo; no descargado; acceso actual sin verificar'
        row['metadata_status']=status
        records.append(row)
    return records,review,stats

def import_metadata(db,input_path):
    if Path(db).resolve()==Path(input_path).resolve():
        raise ValueError('El destino debe ser distinto del origen.')
    rows=json.loads(Path(input_path).read_text())
    if not isinstance(rows,list):raise ValueError('Se esperaba una lista de metadatos.')
    records,review,stats=normalize_metadata(rows)
    stats.update(inserted=0,updated=0,unchanged=0,total=len(records))
    c=sqlite3.connect(db)
    try:
        c.executescript('''
        CREATE TABLE IF NOT EXISTS kobo_bibliography(resource_id TEXT PRIMARY KEY,
          title TEXT NOT NULL,authors TEXT NOT NULL,url TEXT NOT NULL,
          metadata_status TEXT NOT NULL,metadata_json TEXT NOT NULL);
        CREATE VIRTUAL TABLE IF NOT EXISTS kobo_search USING fts5(resource_id UNINDEXED,
          title,authors,topics,tokenize='unicode61 remove_diacritics 2');
        ''')
        with c:
            for row in records:
                key=row['ContentID'];title=(row['Title'] or '').strip() or '[Sin título en Kobo]'
                authors=row['Attribution'] or ''
                values=(title,authors,'',row['metadata_status'],json.dumps(row,sort_keys=True,ensure_ascii=False))
                old=c.execute('SELECT title,authors,url,metadata_status,metadata_json FROM kobo_bibliography WHERE resource_id=?',(key,)).fetchone()
                if old==values:stats['unchanged']+=1;continue
                c.execute('INSERT OR REPLACE INTO kobo_bibliography VALUES(?,?,?,?,?,?)',(key,*values))
                c.execute('DELETE FROM kobo_search WHERE resource_id=?',(key,))
                c.execute('INSERT INTO kobo_search VALUES(?,?,?,?)',(key,title,authors,' '.join(str(row[k] or '') for k in ('ISBN','Publisher','Series','Subtitle'))))
                stats['inserted' if old is None else 'updated']+=1
    finally:c.close()
    return stats
