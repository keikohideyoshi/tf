import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'app'))
from natural_search import fallback,reconcile_ai_plan,validate
class AIGuardTests(unittest.TestCase):
 def test_no_invented_filters(self):
  proposal={'intent':'battle','outcome':'Halál','term':'haltam meg csatában','first':True,'latest':True,'last_n':2,'rank':True}
  p=reconcile_ai_plan('Mikor haltam meg csatában?',proposal)
  self.assertEqual((p['intent'],p['outcome'],p['term'],p['first'],p['latest'],p['last_n'],p['rank']),('battle','Halál','',False,False,None,False))
 def test_explicit_time(self):
  proposal={'intent':'battle','outcome':'Győzelem','last_n':2,'first':True}
  p=reconcile_ai_plan('Mikor haltam meg az utolsó 100 fordulóban?',proposal)
  self.assertEqual((p['outcome'],p['last_n'],p['first']),('Halál',100,False))
 def test_latest(self):
  p=reconcile_ai_plan('Mikor haltam meg utoljára?',{'intent':'text','term':'valami'})
  self.assertTrue(p['latest']);self.assertFalse(p['first'])
 def test_invalid_fields(self):
  with self.assertRaises(ValueError):validate({'intent':'unknown'})
 def test_no_monster_no_term(self):
  p=validate({'intent':'battle','outcome':'Halál','term':'kitalált szörny','exclude_monster':True})
  self.assertEqual(p['term'],'');self.assertFalse(p['exclude_monster'])
