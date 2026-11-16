"""Conservative encyclopedia-backed turn search; never treats arbitrary numbers as IDs."""
import re
import unicodedata
from core import fold_hu, read_html
from pathlib import Path
from html import unescape
from search_diagnostics import Stage, count

KINDS={'item':'Tárgy','monster':'Szörny','spell':'Varázslat'}

def catalog(c, term='', kind=None, limit=100):
    """Lookup by name (accent insensitive) or #id; returned rows are not turn hits."""
    term=term.strip()
    if not term:return []
    rows=c.execute('SELECT kind,entity_id,name FROM entities'+(' WHERE kind=?' if kind else '')+' ORDER BY kind,name',([kind] if kind else [])).fetchall()
    norm=fold_hu(term).strip()
    number=re.fullmatch(r'#?(\d+)',term)
    if number:
        found=[dict(r) for r in rows if r['entity_id']==int(number.group(1))]
    else:
        found=[dict(r) for r in rows if norm in fold_hu(r['name'])]
        found.sort(key=lambda r:(fold_hu(r['name'])!=norm,not fold_hu(r['name']).startswith(norm),len(r['name']),r['name']))
    return found[:limit]

def _id_pattern(kind,entity_id):
    # Only explicit, typed object references; never plain numbers or generic #number.
    n=re.escape(str(entity_id))
    if kind=='item':
        return re.compile(r'(?<!\w)(?:a|az)?\s*'+n+r'\s*\.\s*tárgy(?:at|at|nak|ból|ban|ból|ról|ként|on|hoz|ak|akból)?\b',re.I)
    if kind=='spell':
        return re.compile(r'(?<!\w)(?:a|az)?\s*'+n+r'\s*\.\s*varázslat(?:ot|nak|tal|ból|ban|ként|ok|ot)?\b',re.I)
    # Monster numbers are frequently battle stats; require explicit typed label.
    return re.compile(r'(?<!\w)(?:szörny|lény)\s*#\s*'+n+r'\b',re.I)

def _name_pattern(name):
    """Match canonical names and a small set of attested Hungarian inflections.

    TF loot descriptions use accusative forms (skorpiókarom -> skorpiókarmot).
    Keep this conservative: never match a loose substring of an unrelated item.
    """
    needle=fold_hu(name).strip()
    variants={needle}
    if needle.endswith('karom'):
        variants.add(needle[:-5]+'karmot')
        variants.add(needle[:-5]+'karmok')
        variants.add(needle[:-5]+'karmokat')
    alternatives=[r'\s+'.join(re.escape(x) for x in v.split()) for v in sorted(variants,key=len,reverse=True)]
    return re.compile(r'(?<!\w)(?:'+'|'.join(alternatives)+r')(?!\w)',re.I)

# The original TF HTML contains typed links: Enc(0,N) => item #N+1,
# Enc(1,N) => monster #N+10. Use the link, not the inflected visible label.
ENC_ANCHOR=re.compile(r'<a\b[^>]*?href\s*=\s*[\"\']?\s*javascript\s*:\s*Enc\(\s*([01])\s*,\s*(\d+)\s*,[^>]*>(.*?)</a\s*>',re.I|re.S)
HTML_TAG=re.compile(r'<[^>]*>')

def _linked_occurrences(source,kind,entity_id,event=None):
 """Return exact linked mentions/events from the source HTML.

 An event requires an affirmative local action phrase before the link;
 inventory references and mere mentions are not acquisitions.
 """
 if not Path(source).is_file():return []
 with Stage("html_read_decode"):
  html=read_html(source)
 count("html_files_read")
 count("html_bytes_approx",len(html))
 target_type='0' if kind=='item' else '1'
 target_n=entity_id-(1 if kind=='item' else 10)
 results=[]
 for m in ENC_ANCHOR.finditer(html):
  if m.group(1)!=target_type or int(m.group(2))!=target_n:continue
  label=' '.join(unescape(HTML_TAG.sub(' ',m.group(3))).split())
  if event:
   # Action must precede the link in a short local text span. Do not
   # cross a sentence, command, paragraph or table boundary.
   before=html[max(0,m.start()-600):m.start()]
   before=re.split(r'<(?:table|p|tr|td|br)\b[^>]*>|[.!?;]',before,flags=re.I)[-1]
   before=' '.join(unescape(HTML_TAG.sub(' ',before)).split())[-180:]
   verbs=EVENT_PATTERNS[event]
   cues=re.compile(r'(?:szerzem[eé]nyed\s*:|l[aá]ssuk\s*,?\s*mire\s+bukkant[aá]l\s*:)',re.I) if event=='Megszereztem' else None
   hits=list(verbs.finditer(before))
   if cues:hits+=list(cues.finditer(before))
   hits=[v for v in hits if len(before)-v.end()<=120]
   if not hits:continue
   last=max(hits,key=lambda v:v.start())
   if NEGATION.search(before[max(0,last.start()-25):]):continue
  context=' '.join(unescape(HTML_TAG.sub(' ',html[max(0,m.start()-180):m.end()+100])).split())
  results.append({'text':context[-420:],'type':'Enc azonosító'})
 return results

def search_objects(c,kind,entity_id,character_id=None,sample_limit=3,include_ids=True):
    row=c.execute('SELECT name FROM entities WHERE kind=? AND entity_id=?',(kind,entity_id)).fetchone()
    if row is None:raise ValueError('A kiválasztott objektum nem található az enciklopédiában.')
    name=row['name'];name_re=_name_pattern(name);id_re=_id_pattern(kind,entity_id)
    sql='SELECT t.id,t.character_id,t.character,t.turn_number,t.source_path,b.seq,b.content FROM turns t JOIN blocks b ON b.turn_id=t.id'
    params=[]
    if character_id is not None:
        sql+=' WHERE t.character_id=?';params=[character_id]
    sql+=' ORDER BY t.character COLLATE NOCASE,t.turn_number DESC,b.seq'
    groups={}
    for r in c.execute(sql,params):
        content=r['content'];normalized=fold_hu(content)
        hits=[(m.start(),m.end(),'Név') for m in name_re.finditer(normalized)]
        if include_ids:
            for m in id_re.finditer(content):
                # If name and id overlap (e.g. encyclopedia-like headings), count once.
                if not any(a<m.end() and m.start()<b for a,b,_ in hits):
                    hits.append((m.start(),m.end(),'Azonosító'))
        if not hits:continue
        hits.sort()
        tid=r['id']
        if tid not in groups:
            groups[tid]={'turn_id':tid,'character_id':r['character_id'],'character':r['character'],
                         'turn_number':r['turn_number'],'source_path':r['source_path'],
                         'count':0,'snippets':[],'match_types':set(),'name_count':0,'id_count':0}
        item=groups[tid]
        for start,end,source in hits:
            item['count']+=1;item['match_types'].add(source)
            item['name_count' if source=='Név' else 'id_count']+=1
            if len(item['snippets'])<sample_limit:
                a=max(0,start-105);b=min(len(content),end+145)
                item['snippets'].append({'text':('…' if a else '')+content[a:b]+('…' if b<len(content) else ''),'seq':r['seq'],'type':source})
    # Prefer typed Enc links when present; avoid double counting plain text.
    sql_turns='SELECT id,character_id,character,turn_number,source_path FROM turns'
    args=[]
    if character_id is not None:sql_turns+=' WHERE character_id=?';args=[character_id]
    for t in c.execute(sql_turns,args):
        hits=_linked_occurrences(t['source_path'],kind,entity_id)
        if not hits:continue
        groups[t['id']]={'turn_id':t['id'],'character_id':t['character_id'],'character':t['character'],
          'turn_number':t['turn_number'],'source_path':t['source_path'],'count':len(hits),
          'snippets':[dict(h,seq=i) for i,h in enumerate(hits[:sample_limit])],
          'match_types':{'Enc azonosító'},'name_count':0,'id_count':len(hits)}
    for item in groups.values():item['match_types']=', '.join(sorted(item['match_types']))
    return list(groups.values())

# 1.6: only affirmative, explicit item events. This is deliberately NOT
# general semantic inference, and an item mention is not automatically an event.
EVENT_LABELS={'Megszereztem':'Szerzés','Használtam':'Használat','Leadtam':'Leadás'}
EVENT_PATTERNS={
 'Megszereztem':re.compile(r'\b(?:szerezt[eé]l|tal[aá]lt[aá]l|kapt[aá]l|begy[uű]jt[oö]tt[eé]l|zs[aá]km[aá]ny(?:od)?(?:\s+egy|\s+az)?)\b',re.I),
 'Használtam':re.compile(r'\b(?:haszn[aá]lod|haszn[aá]ltad|felhaszn[aá]lod|felhaszn[aá]ltad|elfogyasztod|megiszod|megeszed)\b',re.I),
 'Leadtam':re.compile(r'\b(?:leadod|leadtad|[aá]tadod|[aá]tadtad|beszolg[aá]ltatod|beszolg[aá]ltattad)\b',re.I),
}
NEGATION=re.compile(r'\b(?:nem|sikertelen|nincs|hi[aá]nyzik|megpr[oó]b[aá]lod|szeretn[eé]d|kellene|lehetne)\b',re.I)

def _item_candidate_turns(c, name, entity_id, character_id):
 """FTS5 shortlist. Return None when FTS cannot safely be used.

 A name's first token is searched as a prefix, covering common Hungarian
 suffixes on later words; numeric typed references are searched separately.
 All matches still pass through the original precise event recognizer.
 """
 tokens=re.findall(r'[^\W_]+',fold_hu(name),flags=re.UNICODE)
 if not tokens or len(tokens[0])<3:return None
 # Use a short prefix to accommodate inflection of a single-word name.
 prefix=tokens[0][:max(3,len(tokens[0])-3)]
 query='"'+prefix.replace('"','')+'"* OR "'+str(int(entity_id))+'"'
 try:
  sql=('SELECT DISTINCT b.turn_id FROM block_fts f '
       'JOIN blocks b ON b.id=f.rowid '
       'WHERE block_fts MATCH ?')
  args=[query]
  if character_id is not None:
   sql+=' AND EXISTS (SELECT 1 FROM turns t WHERE t.id=b.turn_id AND t.character_id=?)'
   args.append(character_id)
  return {r[0] for r in c.execute(sql,args)}
 except Exception:
  return None

def search_item_events(c,entity_id,event_mode,character_id=None,sample_limit=3):
 """High-precision item events, not every possible grammatical form.

 Matches typed item IDs or the encyclopedia name in the same short clause as
 a player-action verb. Negated and hypothetical clauses are excluded. Each
 explicit event is counted once; false negatives are preferable to inventions.
 """
 if event_mode not in EVENT_PATTERNS:raise ValueError('Ismeretlen tárgyesemény.')
 row=c.execute("SELECT name FROM entities WHERE kind='item' AND entity_id=?",(entity_id,)).fetchone()
 if row is None:raise ValueError('A tárgy nem található az enciklopédiában.')
 name_re=_name_pattern(row['name']);id_re=_id_pattern('item',entity_id)
 with Stage("fts_candidate_lookup"):
  candidates=_item_candidate_turns(c,row['name'],entity_id,character_id)
 count("candidate_turns",len(candidates) if candidates is not None else -1)
 verb_re=EVENT_PATTERNS[event_mode]
 # Explicit loot introductions in TF monster rewards. These are not generic mentions.
 loot_re=re.compile(r'(?:\bszerzem[eé]nyed\s*:|\bl[aá]ssuk\s*,?\s*mire\s+bukkant[aá]l\s*:)',re.I)
 sql='SELECT t.id,t.character_id,t.character,t.turn_number,t.source_path,b.seq,b.content FROM turns t JOIN blocks b ON b.turn_id=t.id'
 params=[]
 if character_id is not None:sql+=' WHERE t.character_id=?';params.append(character_id)
 sql+=' ORDER BY t.character COLLATE NOCASE,t.turn_number DESC,b.seq'
 groups={}
 if candidates is not None:
  # Materialize candidate IDs once, avoiding SQLite's parameter-count limit.
  with Stage('candidate_temp_table'):
   c.execute('CREATE TEMP TABLE IF NOT EXISTS tf_item_candidates(turn_id INTEGER PRIMARY KEY)')
  with Stage('candidate_temp_table'):
   c.execute('DELETE FROM tf_item_candidates')
   c.executemany('INSERT INTO tf_item_candidates VALUES(?)',((tid,) for tid in candidates))
  sql=sql.replace(' FROM turns t JOIN blocks b ON b.turn_id=t.id',
                  ' FROM turns t JOIN blocks b ON b.turn_id=t.id JOIN tf_item_candidates tc ON tc.turn_id=t.id')
 # Push the *exact same* action/loot regex predicate into SQLite so that
 # millions of irrelevant rows are never transferred to Python. The SQLite
 # user function is connection-local and does not change the database schema.
 # Keep the Python guard below as a defensive consistency check.
 scanned=[0]
 def has_item_action(content):
  scanned[0]+=1
  return int(bool(content and (verb_re.search(content) or
    (event_mode=='Megszereztem' and loot_re.search(content)))))
 c.create_function('tf_item_has_action',1,has_item_action)
 sql=sql.replace(' ORDER BY t.character COLLATE NOCASE,t.turn_number DESC,b.seq',
                 (' AND ' if ' WHERE ' in sql else ' WHERE ')+
                 'tf_item_has_action(b.content)=1 ORDER BY t.character COLLATE NOCASE,t.turn_number DESC,b.seq')
 with Stage("blocks_sqlite_execute"):
  cursor=c.execute(sql,params)
 with Stage("blocks_sqlite_fetch"):
  records=cursor.fetchall()
 count("blocks_scanned_in_sql",scanned[0])
 count("blocks_filtered_in_sql",scanned[0]-len(records))
 count("blocks_read",len(records))
 with Stage("item_event_recognition"):
  for r in records:
   content=r['content']
   # Fast reject: the original recognizer cannot accept a block without an
   # action verb or an explicit loot cue. This preserves its exact semantics
   # while avoiding Unicode normalization and clause scanning for most blocks.
   if not verb_re.search(content) and (event_mode!='Megszereztem' or not loot_re.search(content)):
    count("blocks_skipped_no_action")
    continue
   count("blocks_with_action")
   # Treat sentences and semicolon-separated commands as independent clauses.
   # Do not allow a verb from an unrelated sentence to qualify an object.
   for clause in re.finditer(r'[^!?;]+(?:[!?;]|$)',content):
    raw=clause.group()
    verbs=list(verb_re.finditer(raw))
    cues=list(loot_re.finditer(raw)) if event_mode=='Megszereztem' else []
    if not verbs and not cues:continue
    # Only normalize clauses that contain a qualifying action phrase.
    norm=fold_hu(raw)
    names=list(name_re.finditer(norm));ids=list(id_re.finditer(raw))
    if not names and not ids:continue
    for match,kind in [(m,'Név') for m in names]+[(m,'Azonosító') for m in ids if not any(n.start()<m.end() and m.start()<n.end() for n in names)]:
     # The action must precede the object, with a short distance.
     before=[v for v in verbs if v.end()<=match.start() and match.start()-v.end()<=95]
     # A named loot-introduction may precede a quantity and linked item name.
     # Do not let a cue from a previous sentence or a different item qualify it.
     loot_before=[v for v in cues if v.end()<=match.start() and match.start()-v.end()<=65]
     if loot_before:
      cue=loot_before[-1]
      between=raw[cue.end():match.start()]
      if not re.fullmatch(r'\s*(?:\d+[\s\xa0]*)?',between):continue
     else:
      if not before:continue
      verb=before[-1]
      if NEGATION.search(raw[max(0,verb.start()-22):match.start()]):continue
     tid=r['id']
     if tid not in groups:
      groups[tid]={'turn_id':tid,'character_id':r['character_id'],'character':r['character'],'turn_number':r['turn_number'],'source_path':r['source_path'],'count':0,'snippets':[],'match_types':EVENT_LABELS[event_mode],'name_count':0,'id_count':0}
     result=groups[tid];result['count']+=1;result['name_count' if kind=='Név' else 'id_count']+=1
     if len(result['snippets'])<sample_limit:
      result['snippets'].append({'text':(raw[max(0,cue.start()-45):min(len(raw),match.end()+100)].strip() if loot_before else raw[max(0,match.start()-130):min(len(raw),match.end()+130)].strip()),'seq':r['seq'],'type':kind})
 # For each turn, use exact linked events when available, preventing duplicates.
 sql_turns='SELECT id,character_id,character,turn_number,source_path FROM turns'
 args=[]
 if character_id is not None:sql_turns+=' WHERE character_id=?';args=[character_id]
 if candidates is not None:
  sql_turns+=' AND id IN (SELECT turn_id FROM tf_item_candidates)' if ' WHERE ' in sql_turns else ' WHERE id IN (SELECT turn_id FROM tf_item_candidates)'
 with Stage("turns_sqlite_fetch"):
  turns=c.execute(sql_turns,args).fetchall()
 count("turns_checked_for_links",len(turns))
 for t in turns:
  with Stage("html_link_recognition"):
   hits=_linked_occurrences(t['source_path'],'item',entity_id,event_mode)
  if not hits:continue
  groups[t['id']]={'turn_id':t['id'],'character_id':t['character_id'],'character':t['character'],
   'turn_number':t['turn_number'],'source_path':t['source_path'],'count':len(hits),
   'snippets':[dict(h,seq=i) for i,h in enumerate(hits[:sample_limit])],
   'match_types':EVENT_LABELS[event_mode]+' (Enc)','name_count':0,'id_count':len(hits)}
 return list(groups.values())
