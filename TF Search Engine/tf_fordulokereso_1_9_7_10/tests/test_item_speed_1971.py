import sqlite3,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'app'))
from object_search import search_item_events,_item_candidate_turns
class ItemSpeed1971Tests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  self.c=sqlite3.connect(':memory:');self.c.row_factory=sqlite3.Row;self.addCleanup(self.c.close)
  self.c.executescript('''CREATE TABLE entities(kind TEXT,entity_id INTEGER,name TEXT);
 CREATE TABLE turns(id INTEGER PRIMARY KEY,character_id INTEGER,character TEXT,turn_number INTEGER,source_path TEXT);
 CREATE TABLE blocks(id INTEGER PRIMARY KEY,turn_id INTEGER,seq INTEGER,content TEXT);
 CREATE VIRTUAL TABLE block_fts USING fts5(content,content='blocks',content_rowid='id',tokenize='unicode61 remove_diacritics 2');''')
  self.c.execute("INSERT INTO entities VALUES('item',1463,'garling kristály')")
 def add(self,tid,body,html):
  p=Path(self.tmp.name)/f'{tid}.htm';p.write_text(html,encoding='utf8')
  self.c.execute('INSERT INTO turns VALUES(?,?,?,?,?)',(tid,1,'Teszt',tid,str(p)))
  self.c.execute('INSERT INTO blocks VALUES(?,?,?,?)',(tid,tid,0,body))
  self.c.execute('INSERT INTO block_fts(rowid,content) VALUES(?,?)',(tid,body))
 def test_shortlist_and_results(self):
  self.add(1,'Találtál egy garling kristály tárgyat.','<p>Találtál egy garling kristály tárgyat.</p>')
  self.add(2,'Nem kaptál semmit.','<p>Nem kaptál semmit.</p>')
  self.assertEqual(_item_candidate_turns(self.c,'garling kristály',1463,None),{1})
  rows=search_item_events(self.c,1463,'Megszereztem')
  self.assertEqual([r['turn_number'] for r in rows],[1])
 def test_enc_link(self):
  self.add(1,'Találtál garling kristály.','<p>Találtál <a href="javascript:Enc(0,1462,\'x\');">garling kristályt</a>.</p>')
  self.assertEqual(search_item_events(self.c,1463,'Megszereztem')[0]['count'],1)
 def test_no_fts_fallback(self):
  self.c.execute('DROP TABLE block_fts')
  self.add_without_fts()
  self.assertEqual(len(search_item_events(self.c,1463,'Megszereztem')),1)
 def add_without_fts(self):
  p=Path(self.tmp.name)/'3.htm';p.write_text('Találtál garling kristály.',encoding='utf8')
  self.c.execute('INSERT INTO turns VALUES(?,?,?,?,?)',(3,1,'Teszt',3,str(p)))
  self.c.execute('INSERT INTO blocks VALUES(?,?,?,?)',(3,3,0,'Találtál garling kristály.'))
if __name__=='__main__':unittest.main()
