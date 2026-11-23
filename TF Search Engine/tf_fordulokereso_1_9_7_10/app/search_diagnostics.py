"""Opt-in, thread-local search timing; no turn text or question is logged."""
import json, os, threading, time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
LOG=ROOT/'logs'/'search_performance.log'
_tls=threading.local()
_write_lock=threading.Lock()

class SearchTrace:
 def __init__(self, mode, intent='', entity_id=None, event='', enabled=False):
  self.enabled=enabled
  self.record={'timestamp':time.strftime('%Y-%m-%dT%H:%M:%S%z'), 'mode':mode, 'intent':intent,
               'entity_id':entity_id, 'event':event, 'stages':{}, 'counts':{}, 'status':'ok'}
  self.start_wall=time.perf_counter();self.start_cpu=time.thread_time()
 def __enter__(self):
  if self.enabled:_tls.trace=self
  return self
 def __exit__(self,exc_type,exc,tb):
  if self.enabled:
   self.record['wall_seconds']=round(time.perf_counter()-self.start_wall,5)
   self.record['thread_cpu_seconds']=round(time.thread_time()-self.start_cpu,5)
   if exc_type:self.record['status']='error';self.record['error_type']=exc_type.__name__
   try:
    LOG.parent.mkdir(parents=True,exist_ok=True)
    with _write_lock:
     with LOG.open('a',encoding='utf-8') as f:f.write(json.dumps(self.record,ensure_ascii=False)+'\n')
   except OSError:pass
   if getattr(_tls,'trace',None) is self:del _tls.trace
  return False

def active():return getattr(_tls,'trace',None)
def count(key,n=1):
 t=active()
 if t:t.record['counts'][key]=t.record['counts'].get(key,0)+n
class Stage:
 def __init__(self,name):self.name=name
 def __enter__(self):
  self.t=active()
  if self.t:self.start=time.perf_counter();self.cpu=time.thread_time()
  return self
 def __exit__(self,*args):
  if self.t:
   d=self.t.record['stages'].setdefault(self.name,{'wall_seconds':0.,'thread_cpu_seconds':0.,'calls':0})
   d['wall_seconds']=round(d['wall_seconds']+time.perf_counter()-self.start,5)
   d['thread_cpu_seconds']=round(d['thread_cpu_seconds']+time.thread_time()-self.cpu,5)
   d['calls']+=1
