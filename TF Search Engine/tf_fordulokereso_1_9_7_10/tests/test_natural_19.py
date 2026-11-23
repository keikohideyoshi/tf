"""Run: python -m unittest discover -s tests -v"""
import unittest,sqlite3,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'app'))
from natural_search import fallback
from battle_search import extract_battles

class NaturalTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.c=sqlite3.connect(':memory:');cls.c.row_factory=sqlite3.Row
  cls.c.execute('CREATE TABLE entities(kind TEXT,entity_id INTEGER,name TEXT,details TEXT)')
  cls.c.executemany('INSERT INTO entities VALUES(?,?,?,?)', [('monster',7057,'vámpír őrszem',''),('monster',859,'mutáns hegyitroll',''),('spell',490,'harci ösztönök','')])
 def test_named_death(self):
  p=fallback('Mikor ölt meg vámpír őrszem?',self.c)
  self.assertEqual((p['outcome'],p['monster_id']),('Halál',7057))
 def test_named_victory(self):
  p=fallback('Mikor győztem le vámpír őrszemet?',self.c)
  self.assertEqual((p['outcome'],p['monster_id']),('Győzelem',7057))
 def test_indefinite(self):
  p=fallback('Mikor győztem le bármilyen szörnyet?',self.c)
  self.assertIsNone(p['monster_id'])
 def test_inflection(self):
  p=fallback('Mikor haltam meg vámpír őrszemtől?',self.c)
  self.assertEqual(p['monster_id'],7057)
 def test_unknown_monster_not_all(self):
  with self.assertRaises(ValueError):fallback('Mikor győztem le kitalált szörnyet?',self.c)
 def test_spell(self):
  p=fallback('Melyik ellenfelek ellen alkalmaztam harci ösztönöket?',self.c)
  self.assertEqual(p['intent'],'spell')
 def test_item_unchanged(self):
  p=fallback('Mikor használtam gernim balzsamot?',self.c)
  self.assertEqual((p['intent'],p['term']),('item','gernim balzsamot'))
 def test_battle_local(self):
  html='''<a href="JavaScript:Enc(1,7047,\"x\");">vámpír őrszem</a>
  <p class=csata>Meghaltál. <span class=stat>{Csatastatisztika; sebzés: 2, sebződés: 5}</span>
  Minden elfeketedik, a halál nyújtja feléd ölelő karjait.</p>
  <a href="JavaScript:Enc(1,849,\"x\");">mutáns hegyitroll</a>
  <p class=csata><span class=tp>10 tapasztalati pontot kaptál.</span>
  <span class=stat>{Csatastatisztika; sebzés: 20, sebződés: 1}</span></p>'''
  battles=extract_battles(html)
  self.assertEqual([(b['monster_id'],b['outcome']) for b in battles],[(7057,'Halál'),(859,'Győzelem')])
if __name__=='__main__':unittest.main()

class PostCombatRegression(unittest.TestCase):
 def test_death_after_closing_combat_paragraph(self):
  html='''<a href='JavaScript:Enc(1,7047,"x");'><b>vámpír őrszem</b></a>
  <p class=csata>A vámpír őrszem átharapja a torkodat!
  <span class=stat>{Csatastatisztika; sebzés: <span>200</span>, sebződés: <span>900</span>}</span></p>
  <span class=valt1neg>Minden elfeketedik, mintha egy feneketlen kútba zuhannál.</span>
  A halál nyújtja feléd ölelő karjait.<br>
  <a href='JavaScript:Enc(1,849,"x");'>mutáns hegyitroll</a>
  <p class=csata>Megölted!<span class=stat>{Csatastatisztika; sebzés: 50, sebződés: 0}</span></p>'''
  battles=extract_battles(html)
  self.assertEqual([(b['monster_id'],b['outcome']) for b in battles],[(7057,'Halál'),(859,'Győzelem')])
 def test_real_turn_if_available(self):
  source=Path('/mnt/data/2081_289__2081_289.htm')
  if not source.exists():self.skipTest('A felhasználó tesztfordulója nincs telepítve')
  from core import read_html
  battles=extract_battles(read_html(source))
  self.assertEqual(sum(b['outcome']=='Halál' and b['monster_id']==7057 for b in battles),3)
