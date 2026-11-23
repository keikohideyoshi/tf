"""Persistent exact V/VV spell occurrence index; backfilled from existing compressed caches."""
from event_index import get

SCHEMA = '''
CREATE TABLE IF NOT EXISTS tf_spell_index_state(
 turn_id INTEGER PRIMARY KEY REFERENCES turns(id) ON DELETE CASCADE,
 source_version INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS tf_spell_cast(
 turn_id INTEGER NOT NULL REFERENCES turns(id) ON DELETE CASCADE,
 command_seq INTEGER NOT NULL, position INTEGER NOT NULL,
 spell_id INTEGER NOT NULL, command TEXT NOT NULL, excerpt TEXT NOT NULL,
 PRIMARY KEY(turn_id,command_seq,position));
CREATE INDEX IF NOT EXISTS idx_tf_spell_cast_lookup ON tf_spell_cast(spell_id,turn_id);
'''

def ensure(c):
 for statement in SCHEMA.split(";"):
  if statement.strip():c.execute(statement)

def _cast_rows(turn_id,commands):
 from structured_search import _spell_ids
 for seq,(cmd,_,body) in enumerate(commands):
  if cmd not in ('v','vv'):continue
  for pos,spell_id in enumerate(_spell_ids(cmd,body),1):
   yield (turn_id,seq,pos,spell_id,cmd.upper(),body[:450])

def store(c,turn_id,commands,version):
 """Call in an import transaction after the turn was inserted."""
 c.execute('DELETE FROM tf_spell_cast WHERE turn_id=?',(turn_id,))
 c.executemany('INSERT INTO tf_spell_cast VALUES(?,?,?,?,?,?)',_cast_rows(turn_id,commands))
 c.execute('INSERT OR REPLACE INTO tf_spell_index_state VALUES(?,?)',(turn_id,version))

def backfill(c):
 '''Build a persistent index once, using the compressed command cache.

 Missing cache entries are parsed from HTML once, not on every search.
 Unavailable files remain pending so a later restored file can be indexed.
 '''
 from event_index import VERSION, unpack
 from core import read_html
 from pathlib import Path
 from bs4 import BeautifulSoup
 from structured_search import _commands
 from search_diagnostics import Stage, count
 with Stage('spell_index_schema'):
  ensure(c)
 # Stream pending rows, avoiding one SQLite lookup and decompression of battles per turn.
 with Stage('spell_index_pending_lookup'):
  pending=c.execute('''SELECT t.id,t.source_path,e.commands,e.version
   FROM turns t LEFT JOIN tf_spell_index_state s ON s.turn_id=t.id
   LEFT JOIN tf_event_index e ON e.turn_id=t.id
   WHERE s.turn_id IS NULL OR s.source_version!=?''',(VERSION,)).fetchall()
 count('spell_index_pending_turns',len(pending))
 fallback=set()
 for tid,path,blob,version in pending:
  commands=None
  if version==VERSION and blob is not None:
   try:
    with Stage('spell_index_cache_decode'):
     commands=unpack(blob)
   except (ValueError,TypeError,Exception):
    commands=None
  if commands is None:
   if not Path(path).is_file():
    fallback.add(tid)
    continue
   try:
    with Stage('spell_index_html_fallback'):
     commands=list(_commands(BeautifulSoup(read_html(path),'lxml')))
    count('spell_index_html_files_read')
   except (OSError,ValueError):
    fallback.add(tid)
    continue
  with Stage('spell_index_store'):
   store(c,tid,commands,VERSION)
  count('spell_index_turns_built')
 with Stage('spell_index_commit'):
  c.commit()
 return fallback


def lookup(c,spell_id,allowed_ids):
 '''Compatibility API for existing integrations; indexed by spell ID.'''
 if spell_id is None or not allowed_ids:return {}
 results={}
 for tid,cmd,pos,sid,body in c.execute('''SELECT turn_id,command,position,spell_id,excerpt
  FROM tf_spell_cast WHERE spell_id=? ORDER BY turn_id,command_seq,position''',(spell_id,)):
  if tid in allowed_ids:
   results.setdefault(tid,[]).append(f'{cmd} parancs — {pos}. varázslat (#{sid}): '+body)
 return results


def search_command(c,spell_id,character_id=None,last_n=None):
 '''Direct SQL spell lookup: no full-turn loop, cache or HTML read.'''
 from search_diagnostics import Stage, count
 from structured_search import _record
 from event_index import VERSION
 with Stage('spell_command_index_backfill'):
  fallback=backfill(c)
 # Narrow the scope in SQL, and retrieve only indexed matches.
 sql='''SELECT t.id,t.character_id,t.character,t.turn_number,t.source_path,
   s.command,s.position,s.excerpt
   FROM tf_spell_cast s JOIN turns t ON t.id=s.turn_id
   WHERE s.spell_id=?'''
 args=[spell_id]
 if character_id is not None:
  sql+=' AND t.character_id=?';args.append(character_id)
 if last_n is not None:
  sql+=' AND t.turn_number >= (SELECT MAX(t2.turn_number) FROM turns t2 WHERE t2.character_id=t.character_id)-?'
  args.append(last_n-1)
 sql+=' ORDER BY t.character_id,t.turn_number DESC,s.command_seq,s.position'
 with Stage('spell_command_index_sql'):
  matches=c.execute(sql,args).fetchall()
 count('spell_command_index_rows',len(matches))
 grouped={}
 with Stage('spell_command_results'):
  for r in matches:
   tid=r['id']
   if tid not in grouped:grouped[tid]=[r,[]]
   grouped[tid][1].append(f'{r["command"]} parancs — {r["position"]}. varázslat (#{spell_id}): '+r['excerpt'])
  results=[_record(t,found,'Varázslat') for t,found in grouped.values()]
 # Unindexed files that could not be read are reported as missing.
 missing=len(fallback)
 count('spell_command_result_turns',len(results))
 count('spell_command_result_events',sum(r['count'] for r in results))
 return results,missing
