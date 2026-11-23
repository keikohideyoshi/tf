import sys,sqlite3,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'app'))
from alchemy_search import chest_events,h_commands,search_alchemy
from natural_search import fallback,run,validate

class AlchemyTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  self.c=sqlite3.connect(':memory:');self.c.row_factory=sqlite3.Row;self.addCleanup(self.c.close)
  self.c.executescript('''CREATE TABLE entities(kind TEXT,entity_id INTEGER,name TEXT,details TEXT);
  CREATE TABLE turns(id INTEGER PRIMARY KEY,character_id INTEGER,character TEXT,turn_number INTEGER,source_path TEXT);
  CREATE TABLE blocks(id INTEGER PRIMARY KEY,turn_id INTEGER,seq INTEGER,content TEXT);''')
  self.c.executemany('INSERT INTO entities VALUES(?,?,?,?)', [('item',2487,'nerub dobónyíl',''),('item',341,'alkímiázó üst','')])
  html='''<html><body><table class="par"><tr><td>h 341 2487 28</td><td>használod a 341. tárgyat</td></tr></table>
  <p>Szerzeményed: 12 nerub dobónyíl [nerub dobónyíl ládikóba-> (582,79)-> 240 arany, -2 ÉP].</p></body></html>'''
  path=Path(self.tmp.name)/'turn.html';path.write_text(html)
  self.c.execute('INSERT INTO turns VALUES(1,2,"Teszt",101,?)',(str(path),))
  self.c.execute('INSERT INTO blocks VALUES(1,1,0,?)',('h 341 2487 28',))
  self.c.execute('INSERT INTO blocks VALUES(2,1,1,?)',('Szerzeményed: 12 nerub dobónyíl [nerub dobónyíl ládikóba-> (582,79)-> 240 arany, -2 ÉP].',))
 def test_chest(self):
  self.assertEqual(chest_events('Szerzeményed: 12 nerub dobónyíl [nerub dobónyíl ládikóba-> (582,79)-> 240 arany]', 'nerub dobónyíl'),[(32,12)])
  self.assertEqual(chest_events('Szerzeményed: 12 nerub dobónyíl [másik tárgy ládikóba->]', 'nerub dobónyíl'),[])
 def test_h_command(self):
  html='<table class="par"><tr><td>h 341 2487 28</td><td>használod a 341. tárgyat</td></tr></table><p>h 341 2487 999</p>'
  self.assertEqual(list(h_commands(html)),[(2487,28,'h 341 2487 28')])
 def test_two_events_and_quantity(self):
  rows=search_alchemy(self.c,2487)
  self.assertEqual((len(rows),rows[0]['count'],rows[0]['quantity_total'],rows[0]['quantity_known']),(1,2,40,True))
 def test_no_false_h_narrative(self):
  self.c.execute("UPDATE turns SET source_path=? WHERE id=1",(str(Path(self.tmp.name)/'fake.html'),))
  (Path(self.tmp.name)/'fake.html').write_text('<p>h 341 2487 28</p>')
  self.assertEqual(search_alchemy(self.c,2487)[0]['count'],1)
 def test_question(self):
  p=fallback('Hányszor alkímiáztam nerub dobónyilat az utolsó 100 fordulóban?',self.c)
  self.assertEqual((p['intent'],p['event'],p['last_n'],p['aggregate']),('item','Alkímiáztam',100,True))
  rows,answer=run(self.c,p)
  self.assertEqual(sum(x['count'] for x in rows),2)
  self.assertIn('2 esemény',answer)
 def test_quantity_question(self):
  p=fallback('Hány darab nerub dobónyilat alkímiáztam?',self.c)
  self.assertTrue(p['quantity_request'])
  rows,answer=run(self.c,p)
  self.assertIn('40 db',answer)
 def test_death_aggregation(self):
  p=fallback('Hányszor haltam meg az utolsó 100 fordulóban?',self.c)
  self.assertEqual((p['intent'],p['outcome'],p['last_n'],p['aggregate']),('battle','Halál',100,True))
