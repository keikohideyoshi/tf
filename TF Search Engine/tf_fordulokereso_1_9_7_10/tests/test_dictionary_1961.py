import sqlite3,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'app'))
from natural_search import fallback,reconcile_ai_plan

class DictionaryRegression(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.c=sqlite3.connect(':memory:');cls.c.row_factory=sqlite3.Row
  cls.c.execute('CREATE TABLE entities(kind TEXT,entity_id INTEGER,name TEXT)')
  cls.c.executemany('INSERT INTO entities VALUES(?,?,?)', [('spell',483,'savzuhatag'),('item',211,'sáfránypor'),('monster',8041,'káosznanda')])
 def test_spell_forms(self):
  for verb in ('varázsoltam','elmormoltam','elsütöttem','alkalmaztam','használtam'):
   with self.subTest(verb=verb):
    p=fallback(f'Mikor {verb} savzuhatagot?',self.c)
    self.assertEqual((p['intent'],p['term'],p['entity_id']),('spell','savzuhatag',483))
 def test_item_forms(self):
  for verb,event in [('zsákmányoltam','Megszereztem'),('szereztem','Megszereztem'),('alkalmaztam','Használtam'),('elhasználtam','Használtam'),('használtam','Használtam')]:
   with self.subTest(verb=verb):
    p=fallback(f'Mikor {verb} sáfrányport?',self.c)
    self.assertEqual((p['intent'],p['term'],p['event']),('item','sáfránypor',event))
 def test_unknown_spell(self):
  with self.assertRaisesRegex(ValueError,'Varázslást'):
   fallback('Mikor varázsoltam nemlétezővarázslatot?',self.c)
 def test_npc(self):
  p=fallback('Mikor beszéltem Prrankkh-val?',self.c)
  self.assertEqual((p['intent'],p['mode']),('npc','speech'))
 def test_battle(self):
  p=fallback('Mikor megfutamodtam a káosznandától?',self.c)
  self.assertEqual((p['intent'],p['outcome'],p['monster_id']),('battle','Menekülés',8041))
 def test_ai_guard(self):
  p=reconcile_ai_plan('Mikor varázsoltam savzuhatagot?',{'intent':'text','term':'Mikor varázsoltam savzuhatagot?'},self.c)
  self.assertEqual((p['intent'],p['term']),('spell','savzuhatag'))
