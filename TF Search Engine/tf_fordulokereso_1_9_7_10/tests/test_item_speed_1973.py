import unittest, sqlite3, tempfile, sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'app'))
from object_search import search_item_events

class ItemSpeed1973Tests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  self.c=sqlite3.connect(':memory:');self.c.row_factory=sqlite3.Row;self.addCleanup(self.c.close)
  self.c.executescript('''CREATE TABLE entities(kind TEXT,entity_id INTEGER,name TEXT);
  CREATE TABLE turns(id INTEGER PRIMARY KEY,character_id INTEGER,character TEXT,turn_number INTEGER,source_path TEXT);
  CREATE TABLE blocks(id INTEGER PRIMARY KEY,turn_id INTEGER,seq INTEGER,content TEXT);
  CREATE VIRTUAL TABLE block_fts USING fts5(content,content='blocks',content_rowid='id',tokenize='unicode61 remove_diacritics 2');''')
  self.c.execute("INSERT INTO entities VALUES('item',1463,'garling kristály')")
 def test_actions_after_large_unrelated_prefix_and_separate_clauses(self):
  p=Path(self.tmp.name)/'1.htm';p.write_text('<p>nincs hivatkozás</p>')
  self.c.execute('INSERT INTO turns VALUES(1,1,\'Teszt\',1,?)',(str(p),))
  blocks=['Nincs itt semmi.' for _ in range(100)] + [
   'Szereztél egy garling kristály tárgyat.',
   'Egy garling kristály. Találtál egy garling kristály tárgyat.',
   'Nem kaptál garling kristály tárgyat.',
   'Találtál egy másik tárgyat. Garling kristály.',
   'Lássuk, mire bukkantál: garling kristály',
  ]
  for i,body in enumerate(blocks,1):
   self.c.execute('INSERT INTO blocks VALUES(?,?,?,?)',(i,1,i,body))
   self.c.execute('INSERT INTO block_fts(rowid,content) VALUES(?,?)',(i,body))
  rows=search_item_events(self.c,1463,'Megszereztem')
  self.assertEqual(len(rows),1)
  self.assertEqual(rows[0]['count'],4)
if __name__=='__main__':unittest.main()
