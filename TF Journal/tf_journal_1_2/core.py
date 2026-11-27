import re,json,sqlite3,zipfile,datetime
from pathlib import Path
from email import policy
from email.parser import BytesParser
from html import unescape
ROOT=Path(__file__).resolve().parent
EXT={'.html','.htm','.mhtml','.mht','.zip'}
UNKNOWN='Ismeretlen terület'
def clean(s): return ' '.join(unescape(re.sub(r'<[^>]*>',' ',s)).split())
def decode(b,charset=None):
    m=re.search(rb'charset\s*=\s*["\']?([\w-]+)',b[:8192],re.I)
    for c in [charset,m.group(1).decode() if m else None,'utf-8-sig','iso8859-2']:
        if c:
            try:return b.decode(c)
            except (UnicodeError,LookupError):pass
    return b.decode('iso8859-2')
def parse(b,source):
    if Path(source).suffix.lower() in ('.mht','.mhtml'):
        msg=BytesParser(policy=policy.default).parsebytes(b)
        parts=[p for p in msg.walk() if p.get_content_type()=='text/html']
        if not parts:raise ValueError('Nincs HTML rész az MHTML-ben')
        s=decode(parts[0].get_payload(decode=True),parts[0].get_content_charset())
    else:s=decode(b)
    title=re.search(r'<title\b[^>]*>(.*?)</title>',s,re.I|re.S)
    t=re.search(r'(.+?)\s+(\d+)\.\s*fordulója',clean(title[1]) if title else '',re.I)
    kl=re.search(r'<div\b[^>]*class\s*=\s*["\']?klap\b[^>]*>',s,re.I)
    section=s[kl.end():] if kl else s
    text=clean(section); header=clean(s[:kl.start()] if kl else s[:20000])
    cid=re.search(r'KALANDOZÓ\s*:\s*#\s*(\d+)',header,re.I)
    if not t:
        t=re.search(r'^(.+?),.*?Ez (?:a|az) (\d+)\. fordulód',text,re.I)
    if not t or not cid:raise ValueError('Nem azonosítható karakter vagy forduló')
    matches=re.findall(r'(\d+)\s*,\s*(\d+)\s+mezőn\s+táborozol',text,re.I)
    
    if len(set(matches))>1:raise ValueError('Több eltérő táborozási koordináta')
    x,y=map(int,matches[0]) if matches else (None,None); date=''
    d=re.search(r'Betáplálva:\s*(\d{4})\.\s*([\w]+)\.?\s*(\d{1,2})',header,re.I)
    months=['jan','feb','márc','ápr','máj','jún','júl','aug','szept','okt','nov','dec']
    if d:
        try:date=datetime.date(int(d[1]),next(i+1 for i,m in enumerate(months) if d[2].lower().startswith(m)),int(d[3])).isoformat()
        except (ValueError,StopIteration):pass
    clock=re.search(r"Betáplálva:\s*\d{4}\.\s*\w+\.?\s*\d{1,2}\.?\s*(\d{1,2})h:\s*(\d{2})",header,re.I)
    time=f"{int(clock[1]):02d}:{clock[2]}" if clock and int(clock[1])<24 and int(clock[2])<60 else None
    lv=re.findall(r"\bSzint\s*:\s*(\d+)\s+Merészség\s*:",text,re.I)
    level=int(lv[0]) if lv and len(set(lv))==1 else None
    lab=re.search(r'mezőn\s+táborozol\s*,\s*a\s+(\d+)\.\s*labirintusban\s*,\s*(\d+)\.\s*szinten\s*,\s*(\d+)\.\s*ponton',text,re.I)
    start=re.search(r"letáboroztál\s+a\s+\[(\d+)\s*,\s*(\d+)\]\s+koordinátán",header,re.I)
    moves=re.findall(r"\(Továbbmész\.\.\.\)\s*\[(\d+)\s*,\s*(\d+)\]",clean(s[:kl.start()] if kl else s),re.I)
    return (int(cid[1]),t[1].strip(),int(t[2]),date,x,y, f'{lab[1]}. labirintus, {lab[2]}. szint, {lab[3]}. pont' if lab else '',source, x,y, *(map(int,start.groups()) if start else (None,None)), *(map(int,moves[-1]) if moves else (None,None)),time,level)
def records(path):
    p=Path(path)
    if p.suffix.lower()=='.zip':
        with zipfile.ZipFile(p) as z:
            for n in z.namelist():
                if Path(n).suffix.lower() in EXT-{'.zip'}:
                    yield z.read(n),str(p)+'::'+n
    else:yield p.read_bytes(),str(p)
def validate(zones):
    names=set()
    for i,z in enumerate(zones):
        n,a,b,c,d=z
        if not n.strip() or n in names or min(a,c)<0 or a>b or c>d:raise ValueError('Érvénytelen terület: '+n)
        names.add(n)
        for m,e,f,g,h in zones[:i]:
            if max(a,e)<=min(b,f) and max(c,g)<=min(d,h):raise ValueError(f'Átfedés: {n} / {m}')
def load_zones():
    z=json.loads((ROOT/'zones.json').read_text());validate(z);return z
def zone(x,y,zones):return next((n for n,a,b,c,d in zones if x is not None and y is not None and a<=x<=b and c<=y<=d),UNKNOWN)
def connect(path):
    db=sqlite3.connect(path);db.execute('CREATE TABLE IF NOT EXISTS rounds(cid INTEGER,name TEXT,turn INTEGER,date TEXT,x INTEGER,y INTEGER,lab TEXT,source TEXT,PRIMARY KEY(cid,turn))')
    cols={r[1] for r in db.execute('PRAGMA table_info(rounds)')}
    if 'direct_x' not in cols:
        for c in ('direct_x','direct_y','start_x','start_y','move_x','move_y'):db.execute('ALTER TABLE rounds ADD COLUMN '+c+' INTEGER')
        db.execute("ALTER TABLE rounds ADD COLUMN method TEXT DEFAULT 'Karakterlap'")
        db.execute('UPDATE rounds SET direct_x=x,direct_y=y');db.commit()
    for c,typ in [("time","TEXT"),("level","INTEGER")]:
        if c not in cols:db.execute(f"ALTER TABLE rounds ADD COLUMN {c} {typ}")
    db.commit()
    return db
def resolve(db):
    for (cid,) in db.execute('SELECT DISTINCT cid FROM rounds').fetchall():
        rr=db.execute('SELECT turn,direct_x,direct_y,start_x,start_y,move_x,move_y FROM rounds WHERE cid=? ORDER BY turn',(cid,)).fetchall(); lookup={r[0]:r for r in rr};prev=(None,None)
        for t,dx,dy,sx,sy,mx,my in rr:
            nxt=lookup.get(t+1); candidates=[((dx,dy),'Karakterlap'),(tuple(nxt[3:5]) if nxt else (None,None),'Következő forduló'),((mx,my),'Utolsó mozgás'),(prev,'Korábbi táborhely')]
            pos,method=next(((p,m) for p,m in candidates if None not in p),((None,None),'Ismeretlen'));db.execute('UPDATE rounds SET x=?,y=?,method=? WHERE cid=? AND turn=?',(*pos,method,cid,t));prev=pos
def spans(rows):
    out=[]
    for r in rows:
        t,z=r[0],r[4]
        if out and out[-1][0]==z and out[-1][2]+1==t:out[-1][2]=t;out[-1][3]+=1
        else:out.append([z,t,t,1])
    return out
