"""Conservative natural-language query planner. No turn contents leave the machine."""
import json, os, re, urllib.request, urllib.error
from pathlib import Path
from core import fold_hu
from structured_search import search_structured
from collections import Counter
from core import search_turns, search_turns_advanced
from object_search import catalog, search_objects, search_item_events
from battle_search import search_battles

ALLOWED={'battle','item','text','spell','npc'}
DICTIONARY=json.loads((Path(__file__).with_name('tf_dictionary.json')).read_text(encoding='utf-8'))
OUTCOMES={'Halál','Menekülés','Győzelem','Összes harc'}
EVENTS={'Megszereztem','Használtam','Alkímiáztam','Összes említés'}

def _has(q,key):
 """Use the actual dictionary entries, accent-insensitively and at word boundaries."""
 q=fold_hu(q)
 return any(re.search(r'(?<!\w)'+re.escape(fold_hu(w))+r'(?!\w)',q) for w in DICTIONARY.get(key,()))

def _has_action(q,key):
 """Recognize dictionary forms, including common person/tense variations."""
 if _has(q,key):return True
 q=fold_hu(q)
 stems={
  'spell_use':('varazsol','mormol','elsutott','elsut','elmondtam'),
  'item_acquire':('szerez','talal','kapta','kaptam','zsakmanyol'),
  'item_use':('hasznal','alkalmaz','elhasznal','felhasznal'),
  'npc_speech':('beszel','kozolt','mondott','megbiz','feladatot kapt'),
 }
 return any(re.search(r'(?<!\w)'+re.escape(stem)+r'\w*',q) for stem in stems.get(key,()))

def _remove_actions(q,keys):
 """Remove known question framing and recognized action tokens before object lookup."""
 q=fold_hu(q)
 for key in keys:
  for phrase in sorted(DICTIONARY.get(key,()),key=len,reverse=True):
   q=re.sub(r'(?<!\w)'+re.escape(fold_hu(phrase))+r'(?!\w)',' ',q)
 q=re.sub(r'\b(?:mikor|melyik|mely|hol|hanyszor|hanyadik|forduloban|fordulokban|fordulomban|utoljara|legutobb|eloszor|legelso|a|az|egy|en|eddig|targyat|targy|varazslatot|varazslat)\b',' ',q)
 q=re.sub(r'\b(?:utolso|elmult|legutobbi)\s+(?:\d+|husz|tiz|otven|szaz|ot)\s+fordulo\w*',' ',q)
 return ' '.join(re.sub(r'[?!.,„”"“]',' ',q).split())

def _inflected_entity_match(question, name):
 """Conservative Hungarian -val/-vel assimilation on final word.

 familiáris -> familiárissal; skorpió -> skorpióval.
 """
 if not name:return False
 words=name.split()
 last=words[-1]
 forms=[]
 if last[-1] in 'bcdfghjklmnpqrstvwxyz':
  forms.extend((last+last[-1]+'al',last+last[-1]+'el'))
 else:
  forms.extend((last+'val',last+'vel'))
 prefix=' '.join(words[:-1])
 return any(re.search(r'(?<!\w)'+re.escape((prefix+' ' if prefix else '')+f)+r'(?!\w)',question) for f in forms)

def _entity_from_question(c,question,kind):
 """Longest encyclopedia-name match with Hungarian suffixes, never fuzzy substring."""
 q=fold_hu(question)
 rows=c.execute('SELECT entity_id,name FROM entities WHERE kind=?',(kind,)).fetchall()
 matches=[]
 suffix=r'(?:et|ot|at|öt|t|tol|től|nak|nek|val|vel|ban|ben|bol|ből|hoz|hez|höz|rol|ről|ra|re|on|en|ön)?'
 for r in rows:
  name=fold_hu(r['name'])
  # Hungarian case endings can be attached to the final word.
  pattern=r'(?<!\w)'+re.escape(name)+suffix+r'(?!\w)'
  if re.search(pattern,q) or _inflected_entity_match(q,name):matches.append((len(name),r['entity_id'],r['name']))
 if not matches:return None
 matches.sort(reverse=True)
 if len(matches)>1 and matches[0][0]==matches[1][0]:raise ValueError('Több azonos nevű objektum; pontosítsd a kérdést.')
 return {'id':matches[0][1],'name':matches[0][2]}

def fallback(question,c=None):
 q=question.strip();low=q.casefold()
 if not q:raise ValueError('Írj be egy kérdést.')
 last=re.search(r'(?:utolsó|elmúlt|legutóbbi)\s+(\d+)\s+fordul',low)
 words={'húsz':20,'tíz':10,'ötven':50,'száz':100,'öt':5}
 n=int(last.group(1)) if last else next((v for w,v in words.items() if re.search(r'(?:utolsó|elmúlt|legutóbbi)\s+'+w+r'\s+fordul',low)),None)
 latest=bool(re.search(r'utoljára|legutóbb|legutolsó|legelső|először',low));first=bool(re.search(r'legelső|először',low))
 base={'last_n':n,'latest':latest,'first':first,'rank':bool(re.search(r'legtöbbször|leggyakrabban|melyik három|top\s*\d+',low)), 'aggregate':bool(re.search(r'\b(?:hányszor|hány alkalommal|hány darab|hány db|mennyi|összesen)\b',low)), 'quantity_request':bool(re.search(r'\b(?:hány darab|hány db|mennyi darab|mennyi db)\b',low))}
 # Resolve typed encyclopedia objects first; shared verbs such as "használtam"
 # must be interpreted using the object type, not the verb alone.
 spell=_entity_from_question(c,low,'spell') if c else None
 item=_entity_from_question(c,low,'item') if c else None
 spell_action=_has_action(low,'spell_use')
 item_acquire=_has_action(low,'item_acquire')
 item_use=_has_action(low,'item_use')
 item_alchemy=bool(re.search(r'alkímiáz|alkimiz|ládikóba|üstbe dob',low))
 if spell and (spell_action or (item_use and not item)):
  return dict(base,intent='spell',term=spell['name'],entity_id=spell['id'])
 if item and (item_acquire or item_use or item_alchemy):
  return dict(base,intent='item',term=item['name'],item_id=item['id'],event='Alkímiáztam' if item_alchemy else 'Megszereztem' if item_acquire else 'Használtam')
 # Explicit spell action with an unrecognized object must not silently become
 # a full-question text search. Shared generic verbs alone are not enough.
 if spell_action and not item and not spell and not item_use:
  raise ValueError('Varázslást ismertem fel, de a varázslat neve nem azonosítható az enciklopédiában.')
 # Explicit NPC/building/quest requests.
 command=re.search(r'\b(kld|be)\s*#?\s*(\d+)\b',low)
 npc=bool(re.search(r'\b(npc|küldetés|feladat|épület|főraktár|menazséria|prrankkh|prrantrox|ewgbert|chrrrox)\w*',low)) or (_has_action(low,'npc_speech') and not (spell or item) and not re.search(r'\b(talalkoztam|harc|csata|szorny)\w*',fold_hu(low)))
 if npc or command:
  name=next((w for w in ('prrankkh','prrantrox','ewgbert','chrrrox') if w in low),'')
  mode='complete' if re.search(r'teljesítettem|sikeresen teljesít',low) else 'speech' if _has_action(low,'npc_speech') else ''
  return dict(base,intent='npc',term=name,command_id=int(command.group(2)) if command else None,mode=mode)
 battle=bool(re.search(r'\b(harc|csata|csatában|szörny|ellenfél|megölt|öltek|ölt|meghalt|haltam|halál|menekül|győz|legyőz|vesztett|káosznanda)\w*',low)) or any(_has(low,k) for k in ('battle_death','battle_victory','battle_escape','battle_generic'))
 monster=_entity_from_question(c,low,'monster') if c else None
 if battle or monster:
  outcome='Halál' if _has(low,'battle_death') or re.search(r'\b(meghalt|haltam|halál|ölt\s+meg|megölt)\w*',low) else 'Menekülés' if _has(low,'battle_escape') or 'menekül' in low else 'Győzelem' if _has(low,'battle_victory') or re.search(r'győz|legyőz',low) else 'Összes harc'
  indefinite=_has(low,'indefinite')
  if not monster and not indefinite and re.search(r'(?:\bellen\b|\bmegölt\b|\bölt meg\b|\blegyőztem\b|\bgyőztem\b)',low):
   residue=re.sub(r'\b(mikor|melyik|hányadik|fordulóban|fordulómban|fordulókban|találkoztam|utoljára|legutóbb|először|hányszor|harcoltam|győztem|legyőztem|megölt|ölt|meg|le|engem|ellen|a|az|egy|szörny|szörnyet|valamilyen|bármilyen|eddig)\b',' ',low)
   if re.search(r'[a-záéíóöőúüű]{3,}',residue):raise ValueError('Nem tudtam biztosan azonosítani a megnevezett szörnyet az enciklopédiában: '+residue.strip())
  # "nem vámpír őrszem" excludes this enemy; no filter for indefinite.
  exclude=bool(monster and re.search(r'\bnem\s+(?:a\s+|az\s+|egy\s+)?'+re.escape(monster['name'].casefold()),low))
  return dict(base,intent='battle',outcome=outcome,term=monster['name'] if monster and not indefinite else '',monster_id=monster['id'] if monster and not indefinite else None,exclude_monster=exclude)
 if item_acquire or item_use or item_alchemy or re.search(r'\btargy\w*',fold_hu(low)):
  action='Alkímiáztam' if item_alchemy else 'Megszereztem' if item_acquire else 'Használtam' if item_use else 'Összes említés'
  cleaned=_remove_actions(low,('item_acquire','item_use'))
  cleaned=re.sub(r'\balk[ií]mi[aá]z\w*\b|\balkimiz\w*\b|\bl[aá]dik[oó]ba\b|\b[uü]stbe\s+dob\w*\b',' ',cleaned)
  # Strip inflected action variants not explicitly listed in the JSON.
  cleaned=re.sub(r'\b(?:megszerez\w*|szerez\w*|talal\w*|kapta\w*|zsakmanyol\w*|hasznal\w*|alkalmaz\w*|elhasznal\w*|felhasznal\w*)\b',' ',cleaned)
  cleaned=' '.join(cleaned.split())
  if not cleaned:raise ValueError('Nem tudtam egyértelműen felismerni a tárgy nevét.')
  return dict(base,intent='item',term=cleaned,event=action)
 m=re.search(r'(?:szerepel|találkoztam|említik|említés|keresd|keress|fordulóban|fordulókban)\s+(?:a|az|egy)?\s*[„"]?(.+?)[”"]?\s*\??$',low)
 term=(m.group(1) if m else re.sub(r'^(melyik|milyen|hol|mikor)\s+fordulókban?\s+','',low)).strip(' „”"?.')
 if not term:raise ValueError('Nem tudtam értelmezni a kérdést.')
 return dict(base,intent='text',term=term)

def validate(p):
 if not isinstance(p,dict) or p.get('intent') not in ALLOWED:raise ValueError('Ismeretlen AI-keresési terv.')
 result={'intent':p['intent'],'term':str(p.get('term') or '').strip()[:160], 'latest':p.get('latest') is True,'first':p.get('first') is True,'rank':p.get('rank') is True,'aggregate':p.get('aggregate') is True,'quantity_request':p.get('quantity_request') is True}
 if result['first']:result['latest']=True
 n=p.get('last_n');result['last_n']=int(n) if isinstance(n,int) and not isinstance(n,bool) and 1<=n<=100000 else None
 if result['intent']=='battle':
  if p.get('outcome') not in OUTCOMES:raise ValueError('Ismeretlen harci eredmény.')
  result['outcome']=p['outcome']
  result['monster_id']=p.get('monster_id') if isinstance(p.get('monster_id'),int) and not isinstance(p.get('monster_id'),bool) else None
  result['exclude_monster']=p.get('exclude_monster') is True
  if result['monster_id'] is None:result['term']='';result['exclude_monster']=False
 if result['intent'] in ('spell','npc'):
  result['entity_id']=p.get('entity_id') if isinstance(p.get('entity_id'),int) else None
  result['command_id']=p.get('command_id') if isinstance(p.get('command_id'),int) else None
  result['mode']=p.get('mode') if p.get('mode') in ('speech','complete') else ''
 if result['intent']=='item':
  if p.get('event') not in EVENTS or (not result['term'] and not isinstance(p.get('item_id'),int)):raise ValueError('Hiányzó vagy érvénytelen tárgyfeltétel.')
  result['item_id']=p.get('item_id') if isinstance(p.get('item_id'),int) and not isinstance(p.get('item_id'),bool) else None
  result['event']=p['event']
 if result['intent']=='text' and not result['term']:raise ValueError('Hiányzó keresőkifejezés.')
 return result

def reconcile_ai_plan(question, ai_plan, c=None):
 """Ground an LLM proposal in explicit question wording and local entities.

 The model may propose an intent but cannot invent time bounds, chronology,
 encyclopedia IDs or an object name. Unsupported filters are discarded.
 """
 ai=validate(ai_plan)
 low=fold_hu(question)
 # Deterministic grammar is the only authority for time/ranking directives.
 explicit=fallback(question,c)
 for key in ('last_n','latest','first','rank','aggregate','quantity_request'):
  ai[key]=explicit.get(key) if key=='last_n' else bool(explicit.get(key))
 if ai['first']:
  ai['latest']=True
 # Explicit structured questions and encyclopedia entities take precedence.
 if explicit['intent'] in ('battle','spell','npc'):
  return validate(explicit)
 if explicit['intent']=='item':
  # The local parser handles inflected item names and action verbs.
  return validate(explicit)
 # Only plain text questions may use AI-proposed text search phrases.
 # Do not allow the AI to silently reinterpret a text request as a battle.
 if ai['intent']!='text':
  return validate(explicit)
 ai['term']=explicit['term']
 return validate(ai)

def online_plan(question,key,model):
 """Only the question is transmitted; no DB, snippets or character data."""
 if not key or not model or not model.endswith(':free'):
  raise ValueError('Ingyenes OpenRouter modell (:free végződéssel) és API-kulcs szükséges.')
 prompt=('A Túlélők Földje fordulókereső kérdését alakítsd át kizárólag JSON objektummá. '
         'Ne válaszolj a kérdésre, ne találj ki adatokat. Mezők: intent (battle/item/text/spell/npc), '
         'outcome (Halál/Menekülés/Győzelem/Összes harc) csak battle esetén, '
         'event (Megszereztem/Használtam/Alkímiáztam/Összes említés) csak item esetén, '
         'term (item: pontos tárgynév ragozás nélkül; text: keresett szöveg), '
         'monster_id (egész szám vagy null, csak biztos enciklopédiai azonosító esetén), exclude_monster (boolean), '
         'last_n (egész szám vagy null, csak ha konkrétan szerepel a kérdésben), '
         'latest (boolean), first (boolean), rank (boolean, ha legtöbbször/leggyakrabban). '
         'Ha a kérdés harci eseményekről szól, intent=battle. '
         'A legutóbbi/első kérdéseknél latest/first megfelelően igaz. '
         'Ne küldj markdown-t, csak JSON-t.')
 body=json.dumps({'model':model,'messages':[{'role':'system','content':prompt},{'role':'user','content':question}], 'temperature':0,'max_tokens':250},ensure_ascii=False).encode()
 req=urllib.request.Request('https://openrouter.ai/api/v1/chat/completions',data=body,headers={'Authorization':'Bearer '+key,'Content-Type':'application/json','HTTP-Referer':'https://localhost','X-Title':'TF Fordulokereso'})
 with urllib.request.urlopen(req,timeout=12) as response:data=json.load(response)
 content=data['choices'][0]['message']['content'].strip()
 if content.startswith('```'):content=re.sub(r'^```(?:json)?\s*|\s*```$','',content).strip()
 return validate(json.loads(content))

def apply_selected_object(plan,selected):
 """The user-selected typed encyclopedia object overrides AI/local name guesses.

 Keep time constraints and event/outcome, even if the question parser fails
 to recognize the object. A battle-vs-item conflict is resolved by the
 selected object type, not by guessing from its name.
 """
 p=dict(plan)
 kind=selected['kind'];eid=int(selected['entity_id']);name=selected['name']
 if kind=='monster':
  p['intent']='battle';p['monster_id']=eid;p['term']=name
  p['outcome']=p.get('outcome') if p.get('outcome') in OUTCOMES else 'Összes harc'
  p['exclude_monster']=False
 elif kind=='item':
  p['intent']='item';p['item_id']=eid;p['term']=name
  p['event']=p.get('event') if p.get('event') in EVENTS else ('Megszereztem' if re.search(r'szerez|talált|kapt',fold_hu(str(plan.get('term','')))) else 'Összes említés')
 else:raise ValueError('Csak tárgy vagy szörny szúrható be a kérdésbe.')
 return validate(p)

def run(c,plan,character_id=None):
 p=validate(plan);intent=p['intent'];warning='';missing=0
 if intent=='battle':
  rows,missing=search_battles(c,p['outcome'],character_id,p['last_n'],monster_id=p['monster_id'],exclude_monster=p['exclude_monster'],sample_limit=100000 if p['rank'] else 5)
  label={'Halál':'halálos','Menekülés':'meneküléses','Győzelem':'győztes','Összes harc':'összes'}[p['outcome']]
  count=sum(r['count'] for r in rows)
  answer=f'{count} {label} csata, {len(rows)} fordulóban.'
  if p['rank'] and rows:
   counter=Counter()
   for row in rows:
    for sn in row['snippets']:
     monster=sn['text'].split(' — ',1)[0].strip()
     counter[monster]+=1
   answer+=' Leggyakoribb ellenfelek (a feldolgozott csaták alapján): '+', '.join(f'{name}: {num}' for name,num in counter.most_common(3))+'.'

  if missing:answer+=f' Figyelem: {missing} forrásfájl hiányzott vagy nem volt olvasható; az eredmény nem teljes.'
 elif intent in ('spell','npc'):
  rows,missing=search_structured(c,intent,p['term'],p.get('entity_id'),character_id,p['last_n'],p.get('command_id'),p.get('mode'))
  answer=f'{sum(r["count"] for r in rows)} {"varázslási" if intent=="spell" else "KLD/BE"} esemény, {len(rows)} fordulóban.'
  if missing:answer+=f' {missing} forrásfájl hiányzott vagy nem volt olvasható.'
 elif intent=='item':
  term=p['term'];found=catalog(c,'#'+str(p['item_id']) if p.get('item_id') else term,'item',limit=100)
  exact=[x for x in found if (p.get('item_id') and x['entity_id']==p['item_id']) or x['name'].casefold()==term.casefold() or str(x['entity_id'])==term.lstrip('#')]
  if not exact and not found:
   # Magyar tárgyragok: -t/-ot/-et/-öt/-at, -val/-vel stb.
   for suffix in ('val','vel','ban','ben','ból','ből','hoz','hez','höz','nak','nek','ot','et','öt','at','t'):
    if term.endswith(suffix) and len(term)>len(suffix)+3:
     found=catalog(c,term[:-len(suffix)],'item',limit=100)
     if found:break
  if not exact and len(found)==1:exact=found
  if len(exact)!=1:
   names=', '.join(x['name'] for x in found[:8]);raise ValueError('A tárgy nem azonosítható egyértelműen: '+term+'. '+('Lehetséges találatok: '+names if names else 'Nincs ilyen tárgy az enciklopédiában.'))
  obj=exact[0]
  rows=search_item_events(c,obj['entity_id'],p['event'],character_id) if p['event']!='Összes említés' else search_objects(c,'item',obj['entity_id'],character_id,include_ids=True)
  answer=f'{obj["name"]} (#{obj["entity_id"]}), {p["event"].lower()}: {sum(r["count"] for r in rows)} esemény, {len(rows)} fordulóban.'
  if p['quantity_request']:
   if p['event']=='Alkímiáztam' and rows and all(r.get('quantity_known',False) for r in rows):
    answer+=f' Összesen {sum(r["quantity_total"] for r in rows)} db alkímiázott tárgy.'
   else:answer+=' A teljes darabszám nem állapítható meg megbízhatóan a jelenlegi eseményadatokból.'
 else:
  rows=search_turns_advanced(c,p['term'],character_id)
  answer=f'„{p["term"]}”: {sum(r["count"] for r in rows)} előfordulás, {len(rows)} fordulóban.'
 if p['last_n'] is not None and intent!='battle':
  maxima={}
  for r in c.execute('SELECT character_id,MAX(turn_number) mx FROM turns GROUP BY character_id'):maxima[r['character_id']]=r['mx']
  rows=[r for r in rows if r['turn_number']>=maxima[r['character_id']]-p['last_n']+1]
  answer=f'Az utolsó {p["last_n"]} fordulóban: {sum(r["count"] for r in rows)} esemény, {len(rows)} fordulóban.'
  if p['quantity_request'] and intent=='item':
   if p['event']=='Alkímiáztam' and rows and all(r.get('quantity_known',False) for r in rows):answer+=f' Összesen {sum(r["quantity_total"] for r in rows)} db.'
   else:answer+=' A teljes darabszám nem állapítható meg megbízhatóan.'
 if p['latest'] or p['first']:
  if rows:
   rows=sorted(rows,key=lambda r:r['turn_number'],reverse=not p['first'])
   # Multiple characters: show one extreme per character, never claim a global chronology.
   chosen={}
   for r in rows:chosen.setdefault(r['character_id'],r)
   rows=list(chosen.values())
   answer='; '.join(f'{r["character"]}: {r["turn_number"]}. forduló' for r in rows)+'.'
  else:answer='Nincs megfelelő találat az importált fordulókban.'
 if not rows and not (p['latest'] or p['first']):answer+=' Nincs megfelelő találat.'
 return rows,answer
