import sqlite3, re, hashlib, unicodedata, os, threading
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from bs4 import BeautifulSoup, NavigableString, Tag

ROOT=Path(__file__).resolve().parents[1]
DB=ROOT/'data'/'tudasbazis.sqlite3'
KINDS={'Szörnyek összefoglaló.html':'monster','Tárgyak összefoglaló.html':'item','Varázslatok összefoglaló.html':'spell'}

_schema_lock = threading.Lock()
_schema_ready = False

def conn():
 global _schema_ready
 DB.parent.mkdir(exist_ok=True,parents=True)
 c=sqlite3.connect(DB,timeout=60)
 c.row_factory=sqlite3.Row
 c.execute('PRAGMA busy_timeout=60000')
 c.execute('PRAGMA foreign_keys=ON')
 if _schema_ready:
  return c
 with _schema_lock:
  if _schema_ready:
   return c
  c.execute('PRAGMA journal_mode=WAL')
  c.executescript('''PRAGMA foreign_keys=ON;
 CREATE TABLE IF NOT EXISTS app_meta(key TEXT PRIMARY KEY,value TEXT NOT NULL);
 INSERT OR IGNORE INTO app_meta(key,value) VALUES('index_version','1');
 CREATE TABLE IF NOT EXISTS entities(kind TEXT NOT NULL, entity_id INTEGER NOT NULL,name TEXT NOT NULL,details TEXT NOT NULL,PRIMARY KEY(kind,entity_id));
 CREATE TABLE IF NOT EXISTS turns(id INTEGER PRIMARY KEY,character_id INTEGER NOT NULL,character TEXT NOT NULL,turn_number INTEGER NOT NULL,source_path TEXT NOT NULL UNIQUE,sha256 TEXT NOT NULL);
 CREATE TABLE IF NOT EXISTS blocks(id INTEGER PRIMARY KEY,turn_id INTEGER NOT NULL,seq INTEGER NOT NULL,section TEXT NOT NULL,content TEXT NOT NULL,FOREIGN KEY(turn_id) REFERENCES turns(id) ON DELETE CASCADE);
 CREATE INDEX IF NOT EXISTS idx_blocks_turn ON blocks(turn_id);
 CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY,turn_id INTEGER NOT NULL,block_id INTEGER,event_type TEXT NOT NULL,description TEXT NOT NULL,entity_id INTEGER,FOREIGN KEY(turn_id) REFERENCES turns(id) ON DELETE CASCADE);
 CREATE VIRTUAL TABLE IF NOT EXISTS block_fts USING fts5(content,content='blocks',content_rowid='id',tokenize='unicode61 remove_diacritics 2');
 CREATE TRIGGER IF NOT EXISTS blocks_ai AFTER INSERT ON blocks BEGIN INSERT INTO block_fts(rowid,content) VALUES(new.id,new.content);END;
 CREATE TRIGGER IF NOT EXISTS blocks_ad AFTER DELETE ON blocks BEGIN INSERT INTO block_fts(block_fts,rowid,content) VALUES('delete',old.id,old.content);END;
 ''')
  _schema_ready = True
 return c

def read_html(path):
 b=Path(path).read_bytes()
 for enc in ('utf-8','iso-8859-2','cp1250'):
  try:return b.decode(enc)
  except UnicodeDecodeError:continue
 return b.decode('iso-8859-2',errors='replace')

def import_references(c,folder=None):
 folder=Path(folder or ROOT/'data'/'reference');stats={}
 for filename,kind in KINDS.items():
  p=folder/filename
  if not p.exists():continue
  soup=BeautifulSoup(read_html(p),'lxml');tables=soup.find_all('table'); table=max(tables,key=lambda t:sum(bool(re.fullmatch(r'\d+',tr.find_all(['td','th'],recursive=False)[0].get_text(' ',strip=True))) for tr in t.find_all('tr') if tr.find_all(['td','th'],recursive=False)))
  count=0
  for tr in table.find_all('tr'):
   cells=[x.get_text(' ',strip=True) for x in tr.find_all(['td','th'],recursive=False)]
   if len(cells)<2 or not cells[0].isdigit() or not cells[1]:continue
   import json
   c.execute('INSERT OR REPLACE INTO entities VALUES(?,?,?,?)',(kind,int(cells[0]),cells[1],json.dumps(cells[2:],ensure_ascii=False)))
   count+=1
  stats[kind]=count
 c.commit();return stats

TITLE_RE=re.compile(r'^(.*?)\s+(\d+)\.\s*fordulója',re.I)
CHAR_RE=re.compile(r'KALANDOZÓ:\s*#\s*(\d+)',re.I)
SFR='használod a 211. tárgyat'

INDEX_VERSION=4

def visible_blocks(soup):
 """Walk visible text in document order; BR and block elements are boundaries.
 Inline formatting is joined, without duplicating nested element text.
 """
 root=soup.body or soup
 boundaries={'p','div','tr','td','th','table','h1','h2','h3','h4','h5','h6',
             'li','ul','ol','section','article','blockquote','pre','hr','br'}
 pieces=[]; current=[]
 def flush():
  if current:
   text=' '.join(''.join(current).split());current.clear()
   if len(text)>=3:
    # Long descriptions are chunked at word boundaries, not dropped.
    while len(text)>5000:
     cut=text.rfind(' ',0,5000)
     if cut<100:cut=5000
     pieces.append(text[:cut]);text=text[cut:].strip()
    if text:pieces.append(text)
 def walk(node):
  if isinstance(node,NavigableString):
   if node.parent and node.parent.name not in ('script','style','noscript','template'):
    current.append(str(node))
   return
  if not isinstance(node,Tag):return
  if node.name in ('script','style','noscript','template'):return
  if node.get('hidden') is not None:return
  if 'display:none' in str(node.get('style','')).replace(' ','').lower():return
  is_boundary=node.name in boundaries
  if is_boundary:flush()
  for child in node.children:walk(child)
  if is_boundary:flush()
 walk(root);flush()
 return pieces

def import_turn(c,path):
 p=Path(path).resolve();data=p.read_bytes();sha=hashlib.sha256(data).hexdigest()
 old=c.execute('SELECT sha256 FROM turns WHERE source_path=?',(str(p),)).fetchone()
 if old and old['sha256']==sha and c.execute("SELECT value FROM app_meta WHERE key='index_version'").fetchone()[0]==str(INDEX_VERSION):return 'unchanged'
 soup=BeautifulSoup(read_html(p),'lxml')
 title=soup.title.get_text(' ',strip=True) if soup.title else ''
 m=TITLE_RE.search(title);cm=CHAR_RE.search(soup.get_text(' ',strip=True)[:3000])
 if not m or not cm:raise ValueError('Nem azonosítható biztonságosan a karakter vagy forduló: '+p.name)
 name,turn=m.group(1).strip(),int(m.group(2));cid=int(cm.group(1))
 # Remove irrelevant scripts, styles, and menu widgets.
 for x in soup(['script','style','noscript']):x.decompose()
 for x in soup.select('[id^="cmimenu_"]'):x.decompose()
 # Index the entire visible body, including direct text between tables and BR tags.
 entries=visible_blocks(soup)
 # Explicit error spans not in a p/tr block are still captured.
 all_errors=[s.get_text(' ',strip=True) for s in soup.select('span.hiba')]
 with c:
  if old:c.execute('DELETE FROM turns WHERE source_path=?',(str(p),))
  cur=c.execute('INSERT INTO turns(character_id,character,turn_number,source_path,sha256) VALUES(?,?,?,?,?)',(cid,name,turn,str(p),sha));tid=cur.lastrowid
  for i,txt in enumerate(entries):
   bid=c.execute('INSERT INTO blocks(turn_id,seq,section,content) VALUES(?,?,?,?)',(tid,i,'forduló',txt)).lastrowid
   for _ in range(txt.lower().count(SFR)):
    c.execute('INSERT INTO events(turn_id,block_id,event_type,description,entity_id) VALUES(?,?,?,?,?)',(tid,bid,'safranypor_use','Sáfránypor (#211) használata: +5 TVP',211))
  # Index combat and KLD/BE/spell events in the same transaction.
  from event_index import index_turn
  index_turn(c,tid,read_html(p))
  # one event per actual HTML error span, regardless of the word 'sajnos'
  for err in all_errors:
   c.execute('INSERT INTO events(turn_id,block_id,event_type,description) VALUES(?,?,?,?)',(tid,None,'error',err))
 return f'imported: {name} #{cid}, {turn}. forduló, {len(entries)} blokk, {len(all_errors)} hiba'

def _parse_turn_worker(path):
 """CPU-heavy HTML processing in a separate process; no SQLite connections shared."""
 from battle_search import extract_battles
 from structured_search import _commands
 p=Path(path)
 data=p.read_bytes()
 sha=hashlib.sha256(data).hexdigest()
 html=None
 for encoding in ('utf-8','iso-8859-2','cp1250'):
  try:html=data.decode(encoding);break
  except UnicodeDecodeError:pass
 if html is None:html=data.decode('iso-8859-2',errors='replace')
 soup=BeautifulSoup(html,'lxml')
 title=soup.title.get_text(' ',strip=True) if soup.title else ''
 m=TITLE_RE.search(title)
 cm=CHAR_RE.search(soup.get_text(' ',strip=True)[:3000])
 if not m or not cm:raise ValueError('Nem azonosítható biztonságosan a karakter vagy forduló: '+p.name)
 name,turn=m.group(1).strip(),int(m.group(2))
 cid=int(cm.group(1))
 # The structured extractors operate on the original HTML semantics.
 battles=extract_battles(html)
 commands=[(cmd,num,body) for cmd,num,body in _commands(soup) if cmd in ('kld','be','vv','v')]
 for x in soup(['script','style','noscript']):x.decompose()
 for x in soup.select('[id^="cmimenu_"]'):x.decompose()
 entries=visible_blocks(soup)
 errors=[x.get_text(' ',strip=True) for x in soup.select('span.hiba')]
 return (str(p.resolve()),sha,cid,name,turn,entries,errors,battles,commands)


def _store_parsed_turn(c,parsed):
 """One SQLite writer, atomic per turn; FTS triggers and event data preserved."""
 from event_index import ensure,pack,VERSION
 path,sha,cid,name,turn,entries,errors,battles,commands=parsed
 with c:
  c.execute('DELETE FROM turns WHERE source_path=?',(path,))
  tid=c.execute('INSERT INTO turns(character_id,character,turn_number,source_path,sha256) VALUES(?,?,?,?,?)',
                (cid,name,turn,path,sha)).lastrowid
  c.executemany('INSERT INTO blocks(turn_id,seq,section,content) VALUES(?,?,?,?)',
                ((tid,i,'forduló',txt) for i,txt in enumerate(entries)))
  block_ids=[r[0] for r in c.execute('SELECT id FROM blocks WHERE turn_id=? ORDER BY seq',(tid,))]
  saffron=[(tid,block_ids[i],'safranypor_use','Sáfránypor (#211) használata: +5 TVP',211)
           for i,txt in enumerate(entries) for _ in range(txt.lower().count(SFR))]
  if saffron:c.executemany('INSERT INTO events(turn_id,block_id,event_type,description,entity_id) VALUES(?,?,?,?,?)',saffron)
  if errors:c.executemany('INSERT INTO events(turn_id,block_id,event_type,description) VALUES(?,?,?,?)',
                          ((tid,None,'error',err) for err in errors))
  ensure(c)
  c.execute('INSERT OR REPLACE INTO tf_event_index VALUES(?,?,?,?)',
            (tid,VERSION,pack(battles),pack(commands)))
  from spell_index import ensure as ensure_spells,store as store_spells
  ensure_spells(c)
  store_spells(c,tid,commands,VERSION)
 return f'imported: {name} #{cid}, {turn}. forduló, {len(entries)} blokk, {len(errors)} hiba'


def _worker_count():
 """Leave some capacity for desktop use; override with TF_IMPORT_WORKERS=1..N."""
 value=os.environ.get('TF_IMPORT_WORKERS','auto').strip().lower()
 if value not in ('','auto'):
  try:return max(1,min(32,int(value)))
  except ValueError:pass
 available=len(os.sched_getaffinity(0)) if hasattr(os,'sched_getaffinity') else (os.cpu_count() or 2)
 return max(1,min(6,available-1 if available>2 else available))


def _import_paths(c,paths,progress=None,force=False):
 """Bounded parallel parsing, serialized transactional writes, safe per-file errors."""
 from collections import deque
 from concurrent.futures import Future
 paths=[Path(p).resolve() for p in paths]
 total=len(paths)
 existing={r['source_path']:r['sha256'] for r in c.execute('SELECT source_path,sha256 FROM turns')}
 version_row=c.execute("SELECT value FROM app_meta WHERE key='index_version'").fetchone()
 version_ok=bool(version_row and version_row[0]==str(INDEX_VERSION))
 workers=_worker_count()
 results=[];errors=[]
 # Avoid putting thousands of parsed HTML trees in memory simultaneously.
 executor=ProcessPoolExecutor(max_workers=workers) if workers>1 and total>1 else None
 queue=deque()
 next_i=0
 def submit():
  nonlocal next_i
  while next_i<total and len(queue)<max(1,workers*2):
   p=paths[next_i];next_i+=1
   if not p.is_file():queue.append((p,None,'missing'));continue
   # SHA verification prevents skipping a changed file, even when size/mtime match.
   try:
    sha=hashlib.sha256(p.read_bytes()).hexdigest()
    if not force and version_ok and existing.get(str(p))==sha:
     queue.append((p,None,'unchanged'));continue
   except Exception as exc:
    queue.append((p,None,exc));continue
   queue.append((p,executor.submit(_parse_turn_worker,str(p)) if executor else None,'parse'))
 try:
  submit()
  while queue:
   p,future,status=queue.popleft()
   try:
    if status=='missing':
     message='HIÁNYZÓ FORRÁS – az eredeti index változatlan maradt'
     errors.append((str(p),message))
    elif status=='unchanged':message='unchanged'
    elif status=='parse':
     parsed=future.result() if future else _parse_turn_worker(str(p))
     message=_store_parsed_turn(c,parsed)
    else:raise status
   except Exception as exc:
    message='HIBA: '+str(exc)
    errors.append((str(p),str(exc)))
   results.append((p.name,message))
   if progress:progress(len(results),total,p.name)
   submit()
 finally:
  if executor:executor.shutdown(wait=True,cancel_futures=True)
 return results,errors


def reindex_all(c,progress=None):
 """Rebuild known turns using multiple CPU processes; preserve missing originals."""
 paths=[r['source_path'] for r in c.execute('SELECT source_path FROM turns ORDER BY id')]
 results,errors=_import_paths(c,paths,progress,force=True)
 if not errors:
  with c:c.execute("UPDATE app_meta SET value=? WHERE key='index_version'",(str(INDEX_VERSION),))
 return results,errors


def list_turn_files(folder):
 return [p for p in sorted(Path(folder).rglob('*')) if p.is_file() and p.suffix.lower() in ('.htm','.html') and 'összefoglaló' not in p.name.lower()]


def import_folder(c,folder,progress=None):
 files=list_turn_files(folder)
 result,errors=_import_paths(c,files,progress)
 if not errors:
  with c:c.execute("UPDATE app_meta SET value=? WHERE key='index_version'",(str(INDEX_VERSION),))
 return result

def search(c,query='',kind='all',character_id=None,limit=300):
 # Separate the encyclopedia from turn occurrences; use token matching for punctuation
 # such as bo'adhun and retain exact source context.
 q=query.strip();out=[]
 if kind in ('all','turns','events'):
  if kind!='events':
   sql='SELECT b.content,b.seq,t.character,t.character_id,t.turn_number,t.source_path FROM blocks b JOIN turns t ON b.turn_id=t.id WHERE 1=1';params=[]
   if character_id:sql+=' AND t.character_id=?';params.append(character_id)
   if q:
    terms=re.findall(r'[^\W_]+',q,flags=re.UNICODE)
    if terms:
     # FTS index supports Hungarian accents and punctuation-separated names.
     fts=' AND '.join('"'+term.replace('"','')+'"' for term in terms)
     sql+=' AND b.id IN (SELECT rowid FROM block_fts WHERE block_fts MATCH ?)';params.append(fts)
   sql+=' ORDER BY t.character_id,t.turn_number DESC,b.seq LIMIT ?';params.append(limit)
   for r in c.execute(sql,params):out.append(dict(r)|{'source':'turn'})
  sql='SELECT e.event_type,e.description,t.character,t.character_id,t.turn_number,t.source_path FROM events e JOIN turns t ON e.turn_id=t.id WHERE 1=1';params=[]
  if character_id:sql+=' AND t.character_id=?';params.append(character_id)
  if q:sql+=' AND (e.description LIKE ? OR e.event_type LIKE ?)';params+=['%'+q+'%','%'+q+'%']
  for r in c.execute(sql+' ORDER BY t.character_id,t.turn_number DESC LIMIT ?',params+[limit]):out.append(dict(r)|{'source':'event'})
 if kind in ('all','item','monster','spell'):
  sql='SELECT kind,entity_id,name,details FROM entities WHERE 1=1';params=[]
  if kind!='all':sql+=' AND kind=?';params.append(kind)
  if q:
   terms=re.findall(r'[^\W_]+',q,flags=re.UNICODE)
   if terms:
    for term in terms:
     sql+=' AND (name LIKE ? OR details LIKE ? OR CAST(entity_id AS TEXT)=?)';params+=['%'+term+'%','%'+term+'%',term.lstrip('#')]
  for r in c.execute(sql+' ORDER BY kind,entity_id LIMIT ?',params+[limit]):out.append(dict(r)|{'source':'encyclopedia'})
 return out[:limit]

def ask(c,question,character_id=None):
 # Strictly rule-based interpretation, not a general language model.
 q=question.lower().strip();latest=bool(re.search(r'utoljára|legutóbb',q))
 if not latest:return None
 if not re.search(r'esett|szerez|talált|kapott',q):return None
 # No confident loot-event parser in v1; explicitly say so rather than claiming mentions are drops.
 return {'message':'Az „utoljára esett/szereztem” kérdéshez bizonyított tárgyszerzési események szükségesek. Az 1.0 még nem ismeri fel megbízhatóan ezeket; az alábbiak szöveges előfordulások, NEM igazolt tárgyesések.','query':re.sub(r'(?i)\b(melyik|fordulóban|esett|utoljára|legutóbb|szereztem|szerezte|találtam|kapott|a|az|egy)\b','',question).strip(' ?!.')}

def stats(c):
 return {'entities':{r['kind']:r['n'] for r in c.execute('SELECT kind,count(*) n FROM entities GROUP BY kind')},'turns':c.execute('SELECT count(*) FROM turns').fetchone()[0],'blocks':c.execute('SELECT count(*) FROM blocks').fetchone()[0],'errors':c.execute("SELECT count(*) FROM events WHERE event_type='error'").fetchone()[0]}


# 1.2: A fordulókeresés csak a felhasználó által importált fordulókat vizsgálja.
# Egy találat = egy forduló; az összes előfordulást összeszámoljuk,
# de legfeljebb néhány szövegkörnyezeti példát jelenítünk meg.
def search_turns(c, query, character_id=None, sample_limit=3, turn_range=None):
 q=' '.join(query.split()).casefold()
 if not q:return []
 # Szóközök között rugalmas egyezés; az aposztróf nem tokenelési határ.
 pattern=re.compile(r'\s+'.join(re.escape(part) for part in q.split()),re.IGNORECASE)
 params=[]
 sql="""SELECT t.id,t.character_id,t.character,t.turn_number,t.source_path,
              b.seq,b.content FROM turns t JOIN blocks b ON b.turn_id=t.id"""
 if character_id is not None:
  sql+=' WHERE t.character_id=?';params.append(character_id)
 if turn_range is not None:
  sql+=(' AND ' if params else ' WHERE ')+'t.id BETWEEN ? AND ?';params.extend(turn_range)
 sql+=' ORDER BY t.character COLLATE NOCASE,t.turn_number DESC,b.seq'
 groups={}
 for row in c.execute(sql,params):
  txt=row['content']
  matches=list(pattern.finditer(txt))
  if not matches:continue
  tid=row['id']
  if tid not in groups:
   groups[tid]={'turn_id':tid,'character_id':row['character_id'],
    'character':row['character'],'turn_number':row['turn_number'],
    'source_path':row['source_path'],'count':0,'snippets':[]}
  item=groups[tid];item['count']+=len(matches)
  for m in matches:
   if len(item['snippets'])>=sample_limit:break
   left=max(0,m.start()-105);right=min(len(txt),m.end()+145)
   prefix='…' if left else '';suffix='…' if right<len(txt) else ''
   item['snippets'].append({'text':prefix+txt[left:right]+suffix,
     'seq':row['seq']})
 return list(groups.values())


# 1.3 – Szabad szavas keresés. A kifejezések fordulószinten kombinálódnak.
# Az ÉS/VAGY/NEM és az idézőjelek értelmezése offline, determinisztikus.
def fold_hu(text):
 text=text.casefold().replace('ő','o').replace('ű','u')
 return ''.join(ch for ch in unicodedata.normalize('NFKD',text) if not unicodedata.combining(ch))

def parse_advanced(query):
 """VAGY-csoportok, csoporton belül ÉS és NEM; idézett szöveg egy kifejezés."""
 tokens=re.findall(r'"[^"\n]+"|\S+',query)
 if not tokens:return []
 groups=[[]];negate=False
 for raw in tokens:
  word=fold_hu(raw)
  if word in ('vagy','or','||'):
   if groups[-1]:groups.append([])
   negate=False;continue
  if word in ('es','and','&&'):continue
  if word in ('nem','not','!'):
   negate=True;continue
  if raw.startswith('-') and len(raw)>1:
   raw=raw[1:];negate=True
  val=raw.strip('"').strip()
  if val:groups[-1].append((fold_hu(val),negate))
  negate=False
 return [g for g in groups if g and any(not n for _,n in g)]

def search_turns_advanced(c,query,character_id=None,sample_limit=3,turn_range=None):
 groups=parse_advanced(query)
 if not groups:return []
 # One DB scan for all expressions; each block is normalized only once.
 sql="SELECT t.id,t.character_id,t.character,t.turn_number,t.source_path, b.seq,b.content FROM turns t JOIN blocks b ON b.turn_id=t.id"
 params=[]
 if character_id is not None:
  sql+=' WHERE t.character_id=?';params.append(character_id)
 if turn_range is not None:
  sql+=(' AND ' if params else ' WHERE ')+'t.id BETWEEN ? AND ?';params.extend(turn_range)
 sql+=' ORDER BY t.character COLLATE NOCASE,t.turn_number DESC,b.seq'
 positives=list(dict.fromkeys(x for g in groups for x,n in g if not n))
 negatives=list(dict.fromkeys(x for g in groups for x,n in g if n))
 needles=positives+negatives
 results={}
 for row in c.execute(sql,params):
  normalized=fold_hu(row['content']);tid=row['id']
  found={x for x in needles if x in normalized}
  if not found:continue
  if tid not in results:
   results[tid]={'turn_id':tid,'character_id':row['character_id'],'character':row['character'],
   'turn_number':row['turn_number'],'source_path':row['source_path'],
   'count':0,'snippets':[],'_found':set()}
  item=results[tid];item['_found'].update(found)
  for needle in positives:
   if needle not in found:continue
   start=0
   while True:
    pos=normalized.find(needle,start)
    if pos<0:break
    item['count']+=1
    if len(item['snippets'])<sample_limit:
     left=max(0,pos-105);right=min(len(normalized),pos+len(needle)+145)
     item['snippets'].append({'text':('…' if left else '')+row['content'][left:right]+('…' if right<len(normalized) else ''),'seq':row['seq']})
    start=pos+len(needle)
 output=[]
 for item in results.values():
  found=item.pop('_found')
  if any(all((x not in found if neg else x in found) for x,neg in group) for group in groups):
   output.append(item)
 return output


# Optional multiprocess turn search. Each process opens its own read connection;
# independent turn-id intervals ensure results cannot be double counted.
def _search_partition(args):
 advanced,query,character_id,sample_limit,turn_range=args
 c=conn()
 try:
  fn=search_turns_advanced if advanced else search_turns
  return fn(c,query,character_id,sample_limit,turn_range)
 finally:c.close()

def search_text_parallel(c,query,character_id=None,advanced=False,workers=1):
 fn=search_turns_advanced if advanced else search_turns
 if workers<=1:return fn(c,query,character_id)
 bounds=c.execute('SELECT min(id),max(id),count(*) FROM turns').fetchone()
 low,high,n=bounds
 if not n or n<max(80,workers*20):return fn(c,query,character_id)
 workers=min(workers,8,n)
 step=max(1,(high-low+workers)//workers)
 parts=[(low+i*step,min(high,low+(i+1)*step-1)) for i in range(workers) if low+i*step<=high]
 args=[(advanced,query,character_id,3,r) for r in parts]
 with ProcessPoolExecutor(max_workers=len(args)) as pool:
  chunks=list(pool.map(_search_partition,args))
 return [row for chunk in chunks for row in chunk]
