import re
from html.parser import HTMLParser
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from dataclasses import dataclass
from pathlib import Path

BASE='https://beholder.hu/'
KINDS=('Normál','Beállítási','Olimpiai','Mini olimpiai','Tesztcsata','Egyéb')
@dataclass(frozen=True)
class Turn:
    f:int; b:int; o:int; gf:int; tcs:int; t:int
    @property
    def kind(self):
        return 'Tesztcsata' if self.tcs else 'Egyéb' if self.gf else 'Mini olimpiai' if self.o and self.b else 'Olimpiai' if self.o else 'Beállítási' if self.b else 'Normál'
    @property
    def number(self): return self.o or self.f
    def url(self,c):
        q={'m':'tf','in':'fordulo20.php' if self.t==1 else 'fordulo.php','karakter':c,'fordulo':self.f}
        for k,v in [('bul',self.b),('oli',self.o),('gf',self.gf),('tcs',bool(self.tcs))]:
            if v:q[k]=int(v)
        return BASE+'?'+urlencode(q)
    def filename(self,c):
        suffix={'Normál':'','Beállítási':'_BUL','Olimpiai':'_OLI','Mini olimpiai':'_MINIOLI','Tesztcsata':'_TCS','Egyéb':'_GF'}[self.kind]
        extra=f'_f{self.f}_b{self.b}_o{self.o}_gf{self.gf}_tcs{self.tcs}' if self.gf or self.tcs or self.b>1 or (self.o and self.f) else ''
        return f'{c}_{self.number}{suffix}{extra}.html'
class Links(HTMLParser):
    def __init__(self):super().__init__();self.turns=[]
    def handle_starttag(self,tag,attrs):
        if tag!='a':return
        m=re.fullmatch(r'\s*javascript:\s*openurl\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)\s*;?\s*',dict(attrs).get('href','') or '',re.I)
        if m:self.turns.append(Turn(*map(int,m.groups())))
def parse(data):
    p=Links();p.feed(data.decode('utf-8',errors='replace'));return list(dict.fromkeys(p.turns))
def valid(data,c,turn):
    # Preserve original bytes; decode only for validation.
    for enc in ('utf-8','cp1250','iso8859-2'):
        s=data.decode(enc,errors='replace'); plain=re.sub(r'<[^>]*>',' ',s); plain=re.sub(r'\s+',' ',plain)
        if not re.search(r'TÚLÉLŐK FÖLDJE',plain,re.I):continue
        if not re.search(r'KALANDOZÓ\s*:\s*#?\s*'+re.escape(c[2:])+r'\b',plain,re.I):continue
        if turn.kind=='Normál' and not re.search(r'\b'+str(turn.f)+r'\.\s*FORDULÓD\b',plain,re.I):continue
        if turn.kind!='Normál' and not re.search(r'\b'+str(turn.number)+r'\.\s*(?:[\w-]+\s+){0,3}forduló',plain,re.I):continue
        if re.search(r'</html\s*>',s,re.I):return True
    return False
def fetch(url):
    with urlopen(Request(url,headers={'User-Agent':'TF-Forduloletolto/1.3 (personal archive)'}),timeout=35) as r:
        if r.geturl().split('/')[2].lower() not in ('beholder.hu','www.beholder.hu'):raise ValueError('Idegen szerverre irányított át.')
        data=r.read(40*1024*1024+1)
        if len(data)>40*1024*1024:raise ValueError('Túl nagy válasz.')
        return data

def download(c,p,kinds,lo,hi,stop,log,progress):
    turns=parse(fetch(BASE+'?'+urlencode({'m':'tf','in':'karakter.php','karakter':c})))
    if not turns:raise RuntimeError('Nincs felismerhető nyilvános forduló. Lehet, hogy bejelentkezés szükséges vagy változott az oldal.')
    selected=[t for t in turns if t.kind in kinds and lo<=t.number<=hi];log(f'Talált: {len(turns)}, kiválasztott: {len(selected)}')
    out=p/'HTML';out.mkdir(parents=True,exist_ok=True);ok=skip=bad=0
    for i,t in enumerate(selected):
        if stop.is_set():break
        dest=out/t.filename(c)
        if dest.exists():
            if valid(dest.read_bytes(),c,t):skip+=1;log('Meglévő: '+dest.name);progress(i+1,len(selected));continue
            log('Meglévő, de nem ellenőrizhető; megőrizve: '+dest.name);bad+=1;progress(i+1,len(selected));continue
        if stop.wait(2):break
        try:
            data=fetch(t.url(c))
            if not valid(data,c,t):raise ValueError('A válasz nem igazolható fordulóként.')
            if stop.is_set():break
            tmp=dest.with_suffix('.html.part');tmp.write_bytes(data);tmp.replace(dest);ok+=1;log('Letöltve: '+dest.name)
        except HTTPError as e:
            bad+=1;log(f'HTTP {e.code}: {dest.name}')
            if e.code in (401,403,429,503):raise RuntimeError('Szerverkorlátozás: a letöltés leállt. Később folytatható.') from e
        except Exception as e:bad+=1;log(f'Hiba: {dest.name}: {e}')
        progress(i+1,len(selected))
    log(f'Nyilvános: új {ok}, meglévő {skip}, hiba {bad}');return bad
