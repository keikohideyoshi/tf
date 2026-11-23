import unittest, sqlite3, tempfile, sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'app'))
from object_search import search_item_events
from search_diagnostics import SearchTrace
class SQLPrefilterTests(unittest.TestCase):
 def test_results_and_diagnostic_counts(self):
  with tempfile.TemporaryDirectory() as d:
   c=sqlite3.connect(':memory:');c.row_factory=sqlite3.Row
   c.executescript("""CREATE TABLE entities(kind TEXT,entity_id INTEGER,name TEXT);
    CREATE TABLE turns(id INTEGER PRIMARY KEY,character_id INTEGER,character TEXT,turn_number INTEGER,source_path TEXT);
    CREATE TABLE blocks(id INTEGER PRIMARY KEY,turn_id INTEGER,seq INTEGER,content TEXT);
    CREATE VIRTUAL TABLE block_fts USING fts5(content,content='blocks',content_rowid='id',tokenize='unicode61 remove_diacritics 2');""")
   c.execute("INSERT INTO entities VALUES('item',1463,'garling kristály')")
   p=Path(d)/'turn.htm';p.write_text('Nincs link.',encoding='utf8')
   c.execute("INSERT INTO turns VALUES(1,1,'Teszt',1,?)",(str(p),))
   blocks=['Nincs itt semmi.']*50+['Találtál garling kristály.','Nem kaptál garling kristály.','Lássuk, mire bukkantál: garling kristály.']
   for i,b in enumerate(blocks,1):
    c.execute('INSERT INTO blocks VALUES(?,?,?,?)',(i,1,i,b))
    c.execute('INSERT INTO block_fts(rowid,content) VALUES(?,?)',(i,b))
   rows=search_item_events(c,1463,'Megszereztem')
   self.assertEqual(rows[0]['count'],2)
   self.assertEqual(len(rows),1)
   c.close()
if __name__=='__main__':unittest.main()
