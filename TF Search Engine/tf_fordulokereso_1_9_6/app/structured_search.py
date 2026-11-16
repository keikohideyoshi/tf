"""Conservative source-grounded TF event search. Item event implementation is independent."""
import re
from pathlib import Path
from bs4 import BeautifulSoup
from core import read_html, fold_hu
from battle_search import extract_battles

COMMAND=re.compile(r'^\s*(kld|be|vv|v)\s+(\d+)',re.I)
SPELL_CONTEXT=re.compile(r'\bvarázslat(?:ot|tal|ot|ot|nak|ot)?\b|\brún(?:a|át|avarázs)|\bpszit?\b',re.I)
BAD_SPELL=re.compile(r'nem ismered|nincs a birtokodban valamilyen komponens|nem sikerül|nem sikerült|sikertelen',re.I)


def _rows(c,character_id=None,last_n=None):
 sql='SELECT id,character_id,character,turn_number,source_path FROM turns';args=[]
 if character_id is not None:sql+=' WHERE character_id=?';args.append(character_id)
 sql+=' ORDER BY character_id,turn_number DESC'
 rows=c.execute(sql,args).fetchall()
 if last_n is not None:
  maxes={}
  for r in rows:maxes[r['character_id']]=max(maxes.get(r['character_id'],0),r['turn_number'])
  rows=[r for r in rows if r['turn_number']>=maxes[r['character_id']]-last_n+1]
 return rows

def _record(t,matches,kind):
 return {'turn_id':t['id'],'character_id':t['character_id'],'character':t['character'],'turn_number':t['turn_number'],'source_path':t['source_path'],'count':len(matches),'snippets':[{'text':s[:650],'seq':i,'type':kind} for i,s in enumerate(matches[:5])],'match_types':kind,'name_count':0,'id_count':0}

def _commands(soup):
 """Yield command with following visible narrative, bounded by next command table."""
 tables=soup.select('table.par')
 for idx,table in enumerate(tables):
  cells=table.select('td')
  if not cells:continue
  m=COMMAND.match(cells[0].get_text(' ',strip=True))
  if not m:continue
  pieces=[];node=table.next_sibling
  while node is not None and (idx+1>=len(tables) or node is not tables[idx+1]):
   if getattr(node,'name',None)=='table' and 'par' in node.get('class',[]):break
   if hasattr(node,'get_text'):pieces.append(node.get_text(' ',strip=True))
   elif isinstance(node,str):pieces.append(node.strip())
   node=node.next_sibling
  yield m.group(1).lower(),int(m.group(2)),' '.join(' '.join(pieces).split())

def search_structured(c,intent,term='',entity_id=None,character_id=None,last_n=None,command_id=None,mode=None):
 results=[];missing=0
 norm=fold_hu(term).strip()
 for t in _rows(c,character_id,last_n):
  path=Path(t['source_path'])
  if not path.is_file():missing+=1;continue
  try:
   from event_index import get
   html=None;matches=[]
   if intent=='spell':
    # The battle parser isolates each combat; a spell from another battle is not a match.
    battles=get(c,t['id'],'battles')
    if battles is None:
     html=read_html(path);battles=extract_battles(html)
    for battle in battles:
     if norm and norm not in fold_hu(battle.get('body','')):continue
     text=battle.get('body','')
     if not re.search(r'\bvarázslat|\brúna|\bpszit?\b',text,re.I):continue
     if norm:
      # A named spell must be used in a spell phrase, not merely mentioned in loot.
      fragments=re.split(r'(?<=[.!?])\s+',text)
      relevant=[f for f in fragments if norm in fold_hu(f) and SPELL_CONTEXT.search(f)
                and not re.search(r'^(?:ellenfeled|a szörny|a lény|csatapartnered)\b',f.strip(),re.I)
                and not re.search(r'\b(?:lő rád|köszönt csatapartnered|ellenfeled varázsol)\b',f,re.I)]
      if not relevant:continue
      text=' '.join(relevant[:2])
     matches.append(f'{battle["monster"]} — harci varázslat: {text[:450]}')
    # Outside combat, explicit spell IDs are reliable even if names are omitted.
    commands=get(c,t['id'],'commands')
    if commands is None:
     if html is None:html=read_html(path)
     commands=list(_commands(BeautifulSoup(html,'lxml')))
    for cmd,num,body in commands:
     if cmd not in ('vv','v'):continue
     if entity_id is not None:
      # vv has up to 3 numbered spells; inspect the command's parameter cells.
      pass
     if norm and norm not in fold_hu(body):continue
     if BAD_SPELL.search(body):continue
     if norm:matches.append('Varázslás (csatán kívül): '+body[:450])
   else:
    commands=get(c,t['id'],'commands')
    if commands is None:
     if html is None:html=read_html(path)
     commands=list(_commands(BeautifulSoup(html,'lxml')))
    for cmd,num,body in commands:
     if cmd not in ('kld','be'):continue
     if command_id is not None and num!=command_id:continue
     if norm and norm not in fold_hu(body):continue
     if mode=='speech' and not (re.search(r'\bmondja\b|\bmondott\b|\bközli\b|\bbeszél\b|\bismerteti\b|\büdvözöl\b|\bválaszolsz\b',body,re.I) or ' - ' in body):continue
     if mode=='complete' and not re.search(r'teljesítetted|teljesítve|sikeresen teljesít|megvan minden|átadod|leadod',body,re.I):continue
     matches.append(f'{cmd.upper()} {num}: {body[:520]}')
   if matches:results.append(_record(t,matches,'Varázslat' if intent=='spell' else 'KLD/BE'))
  except Exception:missing+=1
 return results,missing
