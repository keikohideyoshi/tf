import sqlite3,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'app'))
from spell_category import spell_route
from event_index import index_turn
from structured_search import search_structured

class RoutingTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name)/'turn.htm'
  self.path.write_text('<html><table class="par"><tr><td>vv 75 75 109</td><td>elmormolod a 75. varázslatot a 75. varázslatot a 109. varázslatot</td></tr></table></html>')
  self.c=sqlite3.connect(':memory:');self.c.row_factory=sqlite3.Row
  self.c.execute('CREATE TABLE turns(id INTEGER PRIMARY KEY,character_id INTEGER,character TEXT,turn_number INTEGER,source_path TEXT)')
  self.c.execute('INSERT INTO turns VALUES(1,1,"T",1,?)',(str(self.path),))
  index_turn(self.c,1,self.path.read_text())
 def tearDown(self):self.c.close();self.tmp.cleanup()
 def test_encyclopedia_fifth_column(self):
  self.assertEqual(spell_route(self.c,75),'command')
  self.assertEqual(spell_route(self.c,483),'combat')
  self.assertEqual(spell_route(self.c,47),'combat')
  self.assertEqual(spell_route(self.c,96),'command')
 def test_command_ignores_combat_text_and_html(self):
  with patch('structured_search._battle_candidate_turns',side_effect=AssertionError('combat search used')):
   with patch('structured_search.read_html',side_effect=AssertionError('HTML read')):
    rows,missing=search_structured(self.c,'spell','mágiafeloldás',75)
  self.assertEqual((sum(x['count'] for x in rows),missing),(2,0))
 def test_unknown_id_has_no_guessed_matches(self):
  self.assertEqual(search_structured(self.c,'spell','nemlétező',999),([],0))
if __name__=='__main__':unittest.main()
