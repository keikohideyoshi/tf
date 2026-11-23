"""TF battle result search. Item search code is deliberately independent."""
import re
from pathlib import Path
from html import unescape
from core import read_html

STAT=re.compile(r'\{Csatastatisztika\s*;',re.I)
XP=re.compile(r'\b\d[\d\s\u00a0]*\s+tapasztalati pontot(?:\s*,\s*és\s+\d[\d\s\u00a0]*\s+fejlesztési pontot)?\s+kaptál\.',re.I)
DEATH=re.compile(r'minden elfeketedik.{0,150}a halál nyújtja feléd ölelő karjait',re.I|re.S)
ESCAPE=re.compile(r'(?:futsz, mint az őrült.{0,170}megúsztad|menekülésben mindig is profi voltál)',re.I|re.S)
ANCHOR=re.compile(r'<a\b[^>]*?Enc\(1,(\d+),[^>]*>(.*?)</a\s*>',re.I|re.S)
TAG=re.compile(r'<[^>]+>')
SPACE=re.compile(r'\s+')
POST_DEATH=re.compile(r'^\s*(?:<br\s*/?>\s*|</(?:p|div|span)>\s*)*<span\s+[^>]*class\s*=\s*[\"\']?valt1neg\b',re.I)

def plain(markup):
 return SPACE.sub(' ',unescape(TAG.sub(' ',markup))).strip()

BATTLE_P=re.compile(r'<p\s+class\s*=\s*["\']?csata["\']?[^>]*>(.*?)</p\s*>',re.I|re.S)
STAT_DAMAGE=re.compile(r'sebződés:\s*(?:<[^>]+>)*\s*([\d\s]+)',re.I)

def extract_battles(html):
 """Extract each encounter and its *immediate* post-combat result.

 TF prints the death/escape message (and often victory XP) AFTER </p>
 of the combat, not inside p.csata. Stop at the next encounter/command,
 so an unrelated battle cannot lend its result to this one.
 """
 result=[]
 matches=list(BATTLE_P.finditer(html))
 command_boundary=re.compile(r'<table\b[^>]*class\s*=\s*["\']?par\b',re.I)
 for i,match in enumerate(matches):
  body_html=match.group(1)
  stats=list(STAT.finditer(body_html))
  if not stats:continue
  prefix=html[max(0,match.start()-1100):match.start()]
  anchors=list(ANCHOR.finditer(prefix));monster_id=None;monster='Ismeretlen szörny'
  if anchors:
   anchor=anchors[-1];monster_id=int(anchor.group(1))+10;monster=plain(anchor.group(2)) or monster
  # Only text directly following this encounter, bounded by the next
  # combat, command table or paragraph boundary. A death immediately after
  # </p> belongs to this battle even if its <span> is outside the battle.
  next_start=matches[i+1].start() if i+1<len(matches) else len(html)
  tail=html[match.end():min(next_start,match.end()+2500)]
  boundary=command_boundary.search(tail)
  if boundary:tail=tail[:boundary.start()]
  # Paragraph separators can mark a different action; the immediate
  # outcome always precedes the first such separator.
  paragraph=re.search(r'<p\s*>',tail,re.I)
  if paragraph:tail=tail[:paragraph.start()]
  post=plain(tail)
  death_after_stats=bool(POST_DEATH.search(tail))
  full=plain(body_html)
  for st in stats:
   pre=plain(body_html[:st.start()])
   # Stats may occur more than once in a malformed record: only the final
   # stats block can own the text after the closing battle paragraph.
   immediate_post=post if st is stats[-1] else ''
   local=plain(body_html[st.end():])[:500] + ' ' + pre[-500:]
   if (st is stats[-1] and death_after_stats) or DEATH.search(immediate_post) or DEATH.search(local):outcome='Halál'
   elif ESCAPE.search(immediate_post) or ESCAPE.search(local):outcome='Menekülés'
   elif XP.search(immediate_post) or XP.search(pre[-1400:]) or re.search(r'\bMegölted!',pre,re.I):outcome='Győzelem'
   else:outcome='Ismeretlen'
   dmg=STAT_DAMAGE.search(body_html[st.start():st.start()+400])
   received=int(''.join(dmg.group(1).split())) if dmg else None
   snippet=f'{monster} — {outcome}. {pre[-130:]} {{Csatastatisztika; {immediate_post[:180]}'
   result.append({'monster':monster,'monster_id':monster_id,'outcome':outcome,'received':received,'body':full,'text':snippet[:650]})
 return result

def search_battles(c,outcome='Összes harc',character_id=None,last_n=None,monster_id=None,sample_limit=5,exclude_monster=False):
 where=[];args=[]
 if character_id is not None:where.append('character_id=?');args.append(character_id)
 sql='SELECT id,character_id,character,turn_number,source_path FROM turns'
 if where:sql+=' WHERE '+' AND '.join(where)
 sql+=' ORDER BY character_id,turn_number DESC'
 turns=c.execute(sql,args).fetchall()
 if last_n is not None:
  maxima={}
  for t in turns:maxima[t['character_id']]=max(maxima.get(t['character_id'],-1),t['turn_number'])
  turns=[t for t in turns if t['turn_number']>=maxima[t['character_id']]-last_n+1]
 rows=[];warnings=0
 for t in turns:
  if not Path(t['source_path']).is_file():warnings+=1;continue
  try:
   from event_index import get
   battles=get(c,t['id'],'battles')
   if battles is None:battles=extract_battles(read_html(t['source_path']))
  except Exception:warnings+=1;continue
  matches=[b for b in battles if (outcome=='Összes harc' or b['outcome']==outcome) and (monster_id is None or ((b['monster_id']!=monster_id) if exclude_monster else (b['monster_id']==monster_id)))]
  if not matches:continue
  snippets=[{'text':b['text'],'seq':i,'type':b['outcome']} for i,b in enumerate(matches[:sample_limit])]
  rows.append({'turn_id':t['id'],'character_id':t['character_id'],'character':t['character'],'turn_number':t['turn_number'],'source_path':t['source_path'],'count':len(matches),'snippets':snippets,'match_types':', '.join(sorted(set(b['outcome'] for b in matches))),'name_count':0,'id_count':0})
 return rows,warnings
