"""Optional, private Ollama JSON planner. Only the user's question is sent locally."""
import json, re, urllib.request, urllib.error
from natural_search import validate
BASE='http://127.0.0.1:11434'
DEFAULT_MODEL='qwen3:1.7b'
PROMPT=(
 'Te a Túlélők Földje játék fordulókeresőjének keresésiterv-készítője vagy. '
 'Kizárólag egy JSON objektumot adj vissza, ne válaszold meg a kérdést! '
 'Mezők: intent (battle/item/text/spell/npc), term (szörny/tárgy/varázslat neve, '
 'vagy szöveges keresőkifejezés), outcome (battle: Halál/Menekülés/Győzelem/Összes harc), '
 'event (item: Megszereztem/Használtam/Összes említés), '
 'last_n (egész szám vagy null), latest (boolean), first (boolean), rank (boolean), '
 'exclude_monster (boolean). '
 'Ne találj ki enciklopédiai azonosítókat: monster_id, item_id, entity_id mindig null. '
 'A "legtöbbször" rank=true. Csak a kérdésben szereplő időkorlátot használd. '
 'Ha harcról vagy halálról kérdeznek: intent=battle. '
 'Ha tárgy megszerzéséről: intent=item és event=Megszereztem. '
 'Ha nem egyértelmű: intent=text és term a kérdés releváns kifejezése. '
 'A JSON-on kívül semmi mást ne írj.'
)
def request_json(path, payload=None, timeout=5):
 data=None if payload is None else json.dumps(payload,ensure_ascii=False).encode('utf-8')
 req=urllib.request.Request(BASE+path,data=data,headers={'Content-Type':'application/json'})
 with urllib.request.urlopen(req,timeout=timeout) as response:return json.load(response)
def models():
 return [m['name'] for m in request_json('/api/tags').get('models',[]) if m.get('name')]
def ready(model=DEFAULT_MODEL):
 try:return model in models()
 except (OSError,ValueError,KeyError):return False
def plan(question,model=DEFAULT_MODEL):
 if not ready(model):raise RuntimeError('Az Ollama vagy a kiválasztott modell nem érhető el.')
 payload={'model':model,'stream':False,'format':'json','think':False,
          'messages':[{'role':'system','content':PROMPT},{'role':'user','content':question}],
          'options':{'temperature':0,'num_predict':320}}
 data=request_json('/api/chat',payload,timeout=110)
 content=data['message']['content'].strip()
 if content.startswith('```'):content=re.sub(r'^```(?:json)?\s*|\s*```$','',content).strip()
 return validate(json.loads(content))
