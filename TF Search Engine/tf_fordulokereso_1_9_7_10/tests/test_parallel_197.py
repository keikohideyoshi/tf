import unittest,sys,tempfile,sqlite3
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'app'))
from core import search_turns,search_turns_advanced
class TestRanges(unittest.TestCase):
 def setUp(self):
  self.c=sqlite3.connect(':memory:');self.c.row_factory=sqlite3.Row
  self.c.executescript('CREATE TABLE turns(id INTEGER PRIMARY KEY,character_id INTEGER,character TEXT,turn_number INTEGER,source_path TEXT);CREATE TABLE blocks(id INTEGER PRIMARY KEY,turn_id INTEGER,seq INTEGER,content TEXT);')
  for i in range(1,6):
   self.c.execute('INSERT INTO turns VALUES(?,?,?,?,?)',(i,1,'A',i,'x'))
   self.c.execute('INSERT INTO blocks VALUES(?,?,?,?)',(i,i,1,'savzuhatag savzuhatag' if i%2 else 'más'))
 def test_partition_matches_full(self):
  for fn in (search_turns,search_turns_advanced):
   allrows=fn(self.c,'savzuhatag')
   pieces=fn(self.c,'savzuhatag',turn_range=(1,2))+fn(self.c,'savzuhatag',turn_range=(3,5))
   self.assertEqual(sorted((r['turn_id'],r['count']) for r in allrows),sorted((r['turn_id'],r['count']) for r in pieces))
if __name__=='__main__':unittest.main()
