import unittest,sys,sqlite3,tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'app'))
from structured_search import search_structured,_spell_ids
from event_index import index_turn

class TestSpellPrecision(unittest.TestCase):
 def test_ids(self):
  self.assertEqual(_spell_ids('vv','vv 109 75 365 | elmormolod a 109. varázslatot a 75. varázslatot a 365. varázslatot'),[109,75,365])
  self.assertEqual(_spell_ids('vv','vv 171 171 171 | Gyorsvarázsolsz!'),[171]*3)
 def test_false_positive_and_repeated_casts(self):
  html='''<html><table class="par"><tr><td>vv 171 171 171</td><td>elmormolod a 171. varázslatot a 171. varázslatot a 171. varázslatot</td></tr></table>
  Ez mágiafeloldás szó egy leírásban. <table class="par"><tr><td>vv 75 75 109</td><td>elmormolod a 75. varázslatot a 75. varázslatot a 109. varázslatot</td></tr></table>
  <span class="hiba">Hiányzik egy komponens.</span></html>'''
  with tempfile.TemporaryDirectory() as d:
   path=Path(d)/'t.htm';path.write_text(html)
   c=sqlite3.connect(':memory:');c.row_factory=sqlite3.Row
   c.execute('CREATE TABLE turns(id INTEGER PRIMARY KEY,character_id INTEGER,character TEXT,turn_number INTEGER,source_path TEXT)')
   c.execute('INSERT INTO turns VALUES(1,1,\'T\',1,?)',(str(path),))
   index_turn(c,1,html)
   rows,missing=search_structured(c,'spell','mágiafeloldás',75)
   self.assertEqual((len(rows),rows[0]['count'],missing),(1,2,0))
   rows,_=search_structured(c,'spell','mágiafeloldás',171)
   self.assertEqual(rows[0]['count'],3)
if __name__=='__main__':unittest.main()
