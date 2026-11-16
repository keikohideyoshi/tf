"""Versioned, local compressed event index. Source HTML remains authoritative."""
import json,zlib
from bs4 import BeautifulSoup
from battle_search import extract_battles

VERSION=3

def ensure(c):
 c.execute('''CREATE TABLE IF NOT EXISTS tf_event_index(
 turn_id INTEGER PRIMARY KEY, version INTEGER NOT NULL,
 battles BLOB NOT NULL, commands BLOB NOT NULL,
 FOREIGN KEY(turn_id) REFERENCES turns(id) ON DELETE CASCADE)''')

def pack(obj):return zlib.compress(json.dumps(obj,ensure_ascii=False).encode('utf-8'),6)
def unpack(blob):return json.loads(zlib.decompress(blob).decode('utf-8'))

def index_turn(c,turn_id,html):
 from structured_search import _commands
 ensure(c)
 battles=extract_battles(html)
 commands=[(cmd,num,body) for cmd,num,body in _commands(BeautifulSoup(html,'lxml')) if cmd in ('kld','be','vv','v')]
 c.execute('INSERT OR REPLACE INTO tf_event_index VALUES(?,?,?,?)',(turn_id,VERSION,pack(battles),pack(commands)))

def get(c,turn_id,field):
 try:
  row=c.execute('SELECT version,battles,commands FROM tf_event_index WHERE turn_id=?',(turn_id,)).fetchone()
  if row and row['version']==VERSION:return unpack(row[field])
 except Exception:pass
 return None
