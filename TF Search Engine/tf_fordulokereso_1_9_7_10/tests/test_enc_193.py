import unittest,sys,sqlite3
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'app'))
from natural_search import fallback,apply_selected_object
from object_search import _linked_occurrences,search_item_events
from core import visible_blocks,read_html
from bs4 import BeautifulSoup

class Enc193Tests(unittest.TestCase):
 def setUp(self):
  self.c=sqlite3.connect(':memory:');self.c.row_factory=sqlite3.Row
  self.c.execute('CREATE TABLE entities(kind TEXT,entity_id INTEGER,name TEXT)')
  self.c.executemany('INSERT INTO entities VALUES(?,?,?)',[('monster',543,'Garmhuun familiáris'),('monster',542,'vadászskorpió'),('item',911,'skorpiókarom'),('item',522,'tudás gyöngye')])
 def tearDown(self):self.c.close()
 def test_assimilation(self):
  p=fallback('Mikor harcoltam Garmhuun familiárissal?',self.c)
  self.assertEqual((p['intent'],p['monster_id']),('battle',543))
 def test_override(self):
  p=apply_selected_object({'intent':'battle','outcome':'Győzelem','monster_id':542},{'kind':'monster','entity_id':543,'name':'Garmhuun familiáris'})
  self.assertEqual((p['monster_id'],p['outcome']),(543,'Győzelem'))
 def test_item_override(self):
  p=apply_selected_object({'intent':'item','term':'skorpiókarmot','event':'Megszereztem'},{'kind':'item','entity_id':911,'name':'skorpiókarom'})
  self.assertEqual((p['item_id'],p['event']),(911,'Megszereztem'))
 def test_real_skorpion(self):
  path=Path('/mnt/data/2081_328__2081_328.htm')
  if not path.exists():self.skipTest('No sample HTML')
  self.assertEqual(len(_linked_occurrences(str(path),'item',911,'Megszereztem')),5)
 def test_real_keiko(self):
  path=Path('/mnt/data/3042_1677.htm')
  if not path.exists():self.skipTest('No sample HTML')
  self.assertGreaterEqual(len(_linked_occurrences(str(path),'item',211,'Megszereztem')),1)
 def test_no_false_acquisition(self):
  import tempfile
  with tempfile.TemporaryDirectory() as d:
   f=Path(d)/'test.htm';f.write_text('<p>A táskában <a href="JavaScript:Enc(0,910,\'x\');">skorpiókarom</a> van.</p>',encoding='utf8')
   self.assertEqual(_linked_occurrences(str(f),'item',911,'Megszereztem'),[])
