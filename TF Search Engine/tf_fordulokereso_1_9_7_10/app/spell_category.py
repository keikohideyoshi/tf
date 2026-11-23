"""Spell search routing based exclusively on the encyclopedia's fifth (hatás) column."""
import json
from functools import lru_cache
from pathlib import Path
from bs4 import BeautifulSoup

COMBAT_EFFECTS={'támadó','védekező'}

@lru_cache(maxsize=1)
def _bundled_effects():
 from core import ROOT,read_html
 path=ROOT/'data'/'reference'/'Varázslatok összefoglaló.html'
 if not path.is_file():return {}
 soup=BeautifulSoup(read_html(path),'lxml')
 result={}
 for tr in soup.find_all('tr'):
  cells=tr.find_all(['td','th'],recursive=False)
  if len(cells)<5:continue
  sid=cells[0].get_text(' ',strip=True)
  if sid.isdigit():result[int(sid)]=cells[4].get_text(' ',strip=True).casefold()
 return result

def spell_route(c,spell_id):
 """Return 'combat' or 'command'; refuse to guess for unknown IDs."""
 if spell_id is None:return None
 row=c.execute("SELECT details FROM entities WHERE kind='spell' AND entity_id=?",(spell_id,)).fetchone() if _has_entities(c) else None
 if row:
  try:
   details=json.loads(row[0])
   if len(details)>=3:
    return 'combat' if details[2].strip().casefold() in COMBAT_EFFECTS else 'command'
  except (ValueError,TypeError,AttributeError):pass
 effect=_bundled_effects().get(int(spell_id))
 if effect is None:return None
 return 'combat' if effect in COMBAT_EFFECTS else 'command'

def _has_entities(c):
 return c.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='entities'").fetchone() is not None
