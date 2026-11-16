import json
from pathlib import Path
import tempfile
import unittest
from pkm.kobo import FIELDS,import_metadata,normalize_metadata
from pkm.catalog import connect
from pkm.unified import search_resources

class KoboTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  self.db=Path(self.tmp.name)/'catalog.sqlite';connect(self.db).close()
  self.file=Path(self.tmp.name)/'input.json'
  row=dict.fromkeys(FIELDS);row.update(ContentID='synthetic',Title='Aprendizaje ficticio',Attribution='Autora sintética',Accessibility=1,has_account=1,IsDownloaded='true',expiration_status=0)
  self.rows=[row];self.save()
 def save(self):self.file.write_text(json.dumps(self.rows))
 def test_idempotence_and_unified_search(self):
  self.assertEqual(import_metadata(self.db,self.file)['inserted'],1)
  self.assertEqual(import_metadata(self.db,self.file)['unchanged'],1)
  self.assertEqual(search_resources(self.db,'aprendizaje')[0]['source'],'Kobo')
 def test_preview_cache_and_chapter_separated(self):
  base=self.rows[0]
  rows=[dict(base,ContentID='preview',Accessibility=6),dict(base,ContentID='cache',Accessibility=-1,has_account=0,IsDownloaded='false'),dict(base,ContentID='chapter',BookID='parent')]
  records,review,stats=normalize_metadata(rows)
  self.assertTrue(records[0]['is_preview']);self.assertEqual(len(records),1)
  self.assertEqual(len(review),1);self.assertEqual(stats['internal_rows_excluded'],1)
 def test_private_fields_dropped_and_expired_excluded(self):
  self.rows[0]['secret']='NEVER EXPORT'
  self.assertNotIn('NEVER EXPORT',str(normalize_metadata(self.rows)))
  self.rows[0]['expiration_status']=3
  self.assertFalse(normalize_metadata(self.rows)[0])
 def test_invalid_input_atomic_and_update_index(self):
  import_metadata(self.db,self.file)
  self.rows[0]['Title']='Robótica ficticia';self.save();import_metadata(self.db,self.file)
  self.assertFalse(search_resources(self.db,'aprendizaje'))
  self.assertEqual(len(search_resources(self.db,'robotica')),1)
  self.rows*=2;self.save()
  with self.assertRaises(ValueError):import_metadata(self.db,self.file)
