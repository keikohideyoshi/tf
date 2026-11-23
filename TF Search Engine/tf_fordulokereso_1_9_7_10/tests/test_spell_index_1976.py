import sqlite3,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'app'))
from event_index import index_turn
from spell_index import backfill,lookup
from structured_search import search_structured

class SpellIndexTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory()
  self.path=Path(self.temp.name)/'test.htm'
  self.path.write_text('<html><table class="par"><tr><td>vv 75 75 109</td><td>elmormolod a 75. varázslatot a 75. varázslatot a 109. varázslatot</td></tr></table></html>')
  self.c=sqlite3.connect(':memory:');self.c.row_factory=sqlite3.Row
  self.c.execute('PRAGMA foreign_keys=ON')
  self.c.execute('CREATE TABLE turns(id INTEGER PRIMARY KEY,character_id INTEGER,character TEXT,turn_number INTEGER,source_path TEXT)')
  self.c.execute('INSERT INTO turns VALUES(1,1,"T",1,?)',(str(self.path),))
 def tearDown(self):self.c.close();self.temp.cleanup()
 def test_new_import_and_repeat(self):
  index_turn(self.c,1,self.path.read_text())
  self.assertEqual(len(lookup(self.c,75,{1})[1]),2)
  self.assertEqual(backfill(self.c),set())
  self.assertEqual(backfill(self.c),set())
  rows,missing=search_structured(self.c,'spell','mágiafeloldás',75)
  self.assertEqual((sum(x['count'] for x in rows),missing),(2,0))
 def test_migrate_existing_cache(self):
  from event_index import ensure,pack,VERSION
  ensure(self.c)
  self.c.execute('INSERT INTO tf_event_index VALUES(?,?,?,?)',(1,VERSION,pack([]),pack([('vv',75,'vv 75 75 109 | elmormolod a 75. varázslatot a 75. varázslatot a 109. varázslatot')])))
  self.assertEqual(backfill(self.c),set())
  self.assertEqual(len(lookup(self.c,75,{1})[1]),2)
 def test_no_false_positive(self):
  index_turn(self.c,1,'<html><table class="par"><tr><td>vv 171 171 171</td><td>elmormolod a 171. varázslatot a 171. varázslatot a 171. varázslatot</td></tr></table></html>')
  self.assertEqual(lookup(self.c,75,{1}),{})
if __name__=='__main__':unittest.main()
