import sqlite3,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'app'))
from event_index import index_turn
from structured_search import search_structured
from search_diagnostics import SearchTrace

class FastSpellTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory()
  self.c=sqlite3.connect(':memory:');self.c.row_factory=sqlite3.Row
  self.c.execute('CREATE TABLE turns(id INTEGER PRIMARY KEY,character_id INTEGER,character TEXT,turn_number INTEGER,source_path TEXT)')
  for tid,cmd in [(1,'vv 75 75 109'),(2,'vv 171 171 171'),(3,'v 75 1 0')]:
   p=Path(self.tmp.name)/f'{tid}.htm'
   p.write_text(f'<html><table class="par"><tr><td>{cmd}</td><td>elmormolod</td></tr></table></html>')
   self.c.execute('INSERT INTO turns VALUES(?,?,?,?,?)',(tid,1,'T',tid,str(p)))
   index_turn(self.c,tid,p.read_text())
 def tearDown(self):self.c.close();self.tmp.cleanup()
 def test_index_only_no_turn_loop_or_html(self):
  with patch('structured_search._rows',side_effect=AssertionError('full scan')):
   with patch('core.read_html',side_effect=AssertionError('HTML read')):
    rows,missing=search_structured(self.c,'spell','mágiafeloldás',75)
  self.assertEqual((sum(x['count'] for x in rows),len(rows),missing),(3,2,0))
 def test_indexed_search_profiling(self):
  with SearchTrace('test','spell',75,enabled=True) as trace:
   rows,_=search_structured(self.c,'spell','mágiafeloldás',75)
  self.assertIn('spell_command_index_sql',trace.record['stages'])
  self.assertEqual(trace.record['counts']['spell_command_result_events'],3)
 def test_last_n(self):
  rows,_=search_structured(self.c,'spell','mágiafeloldás',75,last_n=1)
  self.assertEqual([r['turn_number'] for r in rows],[3])
if __name__=='__main__':unittest.main()
