"""Conservative source-grounded TF event search. Item event implementation is independent."""
import re
from pathlib import Path
from bs4 import BeautifulSoup
from core import read_html, fold_hu
from battle_search import extract_battles

COMMAND=re.compile(r'(?:^|\b)(kld|be|vv|v)\s+(\d+)',re.I)
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
  header=cells[0].get_text(' ',strip=True)
  m=COMMAND.search(header)
  if not m:continue
  pieces=[];node=table.next_sibling
  while node is not None and (idx+1>=len(tables) or node is not tables[idx+1]):
   if getattr(node,'name',None)=='table' and 'par' in node.get('class',[]):break
   if hasattr(node,'get_text'):pieces.append(node.get_text(' ',strip=True))
   elif isinstance(node,str):pieces.append(node.strip())
   node=node.next_sibling
  # Keep the complete command parameters: VV can list several spell IDs.
  args=header[m.start():].strip()
  narrative=' '.join(' '.join(pieces).split())
  yield m.group(1).lower(),int(m.group(2)),args+' | '+narrative

def _spell_ids(cmd, body):
 """Read only the command interpretation, never the effect narrative."""
 header=body.split(' | ',1)[0]
 # The first number in the command is the first spell ID; VV has up to three.
 numbers=[int(x) for x in re.findall(r'\d+',header)]
 return numbers[:3 if cmd=='vv' else 1]


def _battle_candidate_turns(c, term):
 """FTS shortlist: do not decompress every cached battle for every query.

 Return None when FTS is absent or cannot safely express the query.
 """
 words=re.findall(r'[^\W_]+',term,flags=re.UNICODE)
 if not words:return None
 try:
  query=' AND '.join('"'+w.replace('"','')+'"' for w in words)
  return {r[0] for r in c.execute("""SELECT DISTINCT b.turn_id FROM block_fts f
   JOIN blocks b ON b.id=f.rowid WHERE block_fts MATCH ?""",(query,))}
 except Exception:return None


def _player_spell_sentences(text, norm):
 """Conservative combat detection; never count an opponent's spell."""
 result=[]
 for fragment in re.split(r'(?<=[.!?])\s+',text):
  if norm not in fold_hu(fragment):continue
  if not SPELL_CONTEXT.search(fragment):continue
  if re.search(r'^(?:ellenfeled|a szörny|a lény|csatapartnered|a másik)\b',fragment.strip(),re.I):continue
  if re.search(r'\b(?:lő rád|dob rád|dob rád a másik|irányodba|ellenfeled varázsol|semlegesíti a varázslatot)\b',fragment,re.I):continue
  if not re.search(r'\b(?:varázslatot|varázslattal|rúnát|rúna|varázsolsz|elmormolod|mormolsz)\b',fragment,re.I):continue
  result.append(fragment)
 return result


def search_structured(c,intent,term='',entity_id=None,character_id=None,last_n=None,command_id=None,mode=None):
 results=[];missing=0
 norm=fold_hu(term).strip()
 from spell_category import spell_route
 route=spell_route(c,entity_id) if intent=='spell' else None
 # Only combat spells need text/FTS matching. Command spells use the exact ID index.
 battle_candidates=_battle_candidate_turns(c,term) if intent=='spell' and route=='combat' and norm else None
 if intent=='spell' and route is None:
  return [],0  # Unknown encyclopedia ID: never guess a spell category.
 if intent=='spell' and route=='command':
  from spell_index import search_command
  return search_command(c,entity_id,character_id,last_n)
 rows=_rows(c,character_id,last_n)
 spell_matches={};spell_fallback=set()
 if intent=='spell' and route=='command':
  from spell_index import backfill,lookup
  spell_fallback=backfill(c)
  spell_matches=lookup(c,entity_id,{t['id'] for t in rows})
 for t in rows:
  path=Path(t['source_path'])
  if not path.is_file() and not (intent=='spell' and route=='command' and t['id'] in spell_matches) and not c.execute('SELECT 1 FROM tf_event_index WHERE turn_id=?',(t['id'],)).fetchone():missing+=1;continue
  try:
   from event_index import get
   html=None;matches=[]
   if intent=='spell':
    # Indexed V/VV commands: no per-turn cache decompression or HTML parsing.
    if route=='command':matches.extend(spell_matches.get(t['id'],()))
    # Legacy fallback for turns with no usable cached command index.
    if route=='command' and t['id'] in spell_fallback:
     commands=get(c,t['id'],'commands')
     if commands is None:
      html=read_html(path)
      commands=list(_commands(BeautifulSoup(html,'lxml')))
     for cmd,num,body in commands:
      if cmd not in ('v','vv') or entity_id is None:continue
      for position,spell_id in enumerate(_spell_ids(cmd,body),1):
       if spell_id==entity_id:
        matches.append(f'{cmd.upper()} parancs — {position}. varázslat (#{spell_id}): '+body[:450])
    # Combat spells have no V/VV header. FTS avoids loading unrelated battles.
    if route=='combat' and norm and (battle_candidates is None or t['id'] in battle_candidates):
     battles=get(c,t['id'],'battles')
     if battles is None:
      if html is None:html=read_html(path)
      battles=extract_battles(html)
     for battle in battles:
      text=battle.get('body','')
      # Fast rejection before the costly accent-insensitive normalization.
      if term.casefold() not in text.casefold() and norm not in fold_hu(text):continue
      for fragment in _player_spell_sentences(text,norm):
       matches.append(f'{battle["monster"]} — harci varázslat: {fragment[:450]}')
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
