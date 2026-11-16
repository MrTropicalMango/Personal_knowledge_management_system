"""Read-only Kindle bibliography import; no book content or account identifiers."""
import json
from pathlib import Path
import plistlib,sqlite3,pathlib,collections

def unpack(blob):
 if not blob:return {}
 p=plistlib.loads(blob);objs=p['$objects']
 def get(x,depth=0):
  if depth>40:raise ValueError('depth')
  if isinstance(x,plistlib.UID):return get(objs[x.data],depth+1)
  if isinstance(x,list):return [get(y,depth+1) for y in x]
  if isinstance(x,dict):
   if 'NS.keys' in x:return dict(zip(get(x['NS.keys'],depth+1),get(x['NS.objects'],depth+1)))
   if 'NS.objects' in x:return get(x['NS.objects'],depth+1)
   return {k:get(v,depth+1) for k,v in x.items() if k!='$class'}
  return x
 return get(p['$top']['root']).get('attributes',{})

def text_names(value,key):
    value=value.get(key,[]) if isinstance(value,dict) else []
    if isinstance(value,str):return value
    return '; '.join(v for v in value if isinstance(v,str)) if isinstance(value,list) else ''

def read_snapshot(snapshot):
    c=sqlite3.connect(Path(snapshot).resolve().as_uri()+'?mode=ro',uri=True)
    try:
        if c.execute('pragma integrity_check').fetchone()[0]!='ok':raise ValueError('Catálogo Kindle inconsistente.')
        rows=c.execute('SELECT ZBOOKID,ZDISPLAYTITLE,ZRAWBOOKTYPE,ZLANGUAGE,ZISHIDDENBYUSER,ZSYNCMETADATAATTRIBUTES FROM ZBOOK ORDER BY ZBOOKID').fetchall()
    finally:c.close()
    records,review,seen=[],[],set()
    for key,title,raw_type,language,hidden,blob in rows:
        if not isinstance(key,str) or not key or key in seen:raise ValueError('Identificador Kindle ausente o duplicado.')
        seen.add(key)
        # Decode only inert plist containers, never instantiate archived classes.
        try:m=unpack(blob)
        except (ValueError,KeyError,TypeError,IndexError,plistlib.InvalidFileException):m={}
        kind=m.get('cde_contenttype')
        origin=m.get('origins',{});origin=origin.get('origin',[]) if isinstance(origin,dict) else []
        if isinstance(origin,dict):origin=[origin]
        origin_types=sorted({x['type'] for x in origin if isinstance(x,dict) and isinstance(x.get('type'),str)})
        category=('sample' if kind=='EBSP' else 'document' if kind=='PDOC' else 'dictionary' if 'KindleDictionary' in origin_types else 'book' if kind=='EBOK' else 'unknown')
        row={'key':key,'title':(title or '').strip(),'authors':text_names(m.get('authors'),'author'),
             'publisher':text_names(m.get('publishers'),'publisher'),
             'publication_date':m.get('publication_date') if isinstance(m.get('publication_date'),str) else '',
             'language':language or '', 'category':category,'is_sample':category=='sample',
             'hidden_by_user':bool(hidden),'origin_types':origin_types,'raw_type':raw_type,
             'metadata_status':('Muestra Kindle; acceso parcial' if category=='sample' else 'Metadatos Kindle; acceso y descarga actuales sin verificar')}
        if category=='unknown' or not row['title']:
            row['metadata_status']='Revisión pendiente; metadatos insuficientes';review.append(row)
        else:records.append(row)
    return records,review

def import_snapshot(db,snapshot):
    if Path(db).resolve()==Path(snapshot).resolve():raise ValueError('El destino debe ser distinto de la biblioteca Kindle.')
    records,review=read_snapshot(snapshot)
    stats={'inserted':0,'updated':0,'unchanged':0,'total':len(records),'review_only':len(review)}
    c=sqlite3.connect(db)
    try:
        c.executescript('''
        CREATE TABLE IF NOT EXISTS kindle_bibliography(resource_id TEXT PRIMARY KEY,title TEXT NOT NULL,
          authors TEXT NOT NULL,url TEXT NOT NULL,metadata_status TEXT NOT NULL,metadata_json TEXT NOT NULL);
        CREATE VIRTUAL TABLE IF NOT EXISTS kindle_search USING fts5(resource_id UNINDEXED,title,authors,topics,
          tokenize='unicode61 remove_diacritics 2');
        ''')
        with c:
            for row in records:
                key=row['key'];values=(row['title'],row['authors'],'',row['metadata_status'],json.dumps(row,sort_keys=True,ensure_ascii=False))
                old=c.execute('SELECT title,authors,url,metadata_status,metadata_json FROM kindle_bibliography WHERE resource_id=?',(key,)).fetchone()
                if old==values:stats['unchanged']+=1;continue
                c.execute('INSERT OR REPLACE INTO kindle_bibliography VALUES(?,?,?,?,?,?)',(key,*values))
                c.execute('DELETE FROM kindle_search WHERE resource_id=?',(key,))
                c.execute('INSERT INTO kindle_search VALUES(?,?,?,?)',(key,row['title'],row['authors'],row['publisher']))
                stats['inserted' if old is None else 'updated']+=1
    finally:c.close()
    return stats
