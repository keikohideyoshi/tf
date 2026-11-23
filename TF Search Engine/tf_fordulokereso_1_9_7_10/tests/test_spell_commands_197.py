import unittest,sys,sqlite3,tempfile
from pathlib import Path
from bs4 import BeautifulSoup
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'app'))
from structured_search import _commands,search_structured
from event_index import ensure,index_turn

HTML='''<html><table class="par"><tr><td>* 1. KP: vv 71 243 224</td><td>elmormolod</td></tr></table>
Gyorsvarázsolsz!<table class="par"><tr><td>* 2. KP: v 75</td><td>mágiafeloldás</td></tr></table>
Elmondod a varázslatot.</html>'''
class TestSpellCommands(unittest.TestCase):
 def test_commands(self):
  commands=list(_commands(BeautifulSoup(HTML,'lxml')))
  self.assertEqual([x[:2] for x in commands],[('vv',71),('v',75)])
 def test_search_ids(self):
  with tempfile.TemporaryDirectory() as d:
   db=sqlite3.connect(':memory:');db.row_factory=sqlite3.Row
   db.execute('CREATE TABLE turns(id INTEGER PRIMARY KEY,character_id INTEGER,character TEXT,turn_number INTEGER,source_path TEXT)')
   path=Path(d)/'t.htm';path.write_text(HTML)
   db.execute('INSERT INTO turns VALUES(1,1,\'T\',1,?)',(str(path),))
   index_turn(db,1,HTML)
   for spell in (71,243,224,75):
    rows,missing=search_structured(db,'spell','mágiafeloldás' if spell==75 else 'egyéb',spell)
    self.assertEqual((len(rows),rows[0]['count'],missing),(1,1,0))
   rows,_=search_structured(db,'spell','nemlétező',999)
   self.assertFalse(rows)
if __name__=='__main__':unittest.main()
