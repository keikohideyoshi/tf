import unittest,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'app'))
from battle_search import XP,extract_battles
class VictoryFormats(unittest.TestCase):
 def test_tp_only(self):self.assertIsNotNone(XP.search('24 008 tapasztalati pontot kaptál.'))
 def test_tp_and_development(self):self.assertIsNotNone(XP.search('24 008 tapasztalati pontot, és 1 fejlesztési pontot kaptál.'))
 def test_no_xp(self):self.assertIsNone(XP.search('1 fejlesztési pontot kaptál.'))
 def test_garmhuun_turn(self):
  p=Path('/mnt/data/2081_328__2081_328(2).htm')
  if not p.exists():self.skipTest('Külső tesztforduló nem része a kiadásnak')
  from core import read_html
  battles=[x for x in extract_battles(read_html(p)) if x['monster']=='Garmhuun familiáris']
  self.assertEqual(len(battles),4)
  self.assertTrue(all(x['outcome']=='Győzelem' for x in battles))
if __name__=='__main__':unittest.main()
