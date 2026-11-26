import re, os, html, email
from email import policy
from pathlib import Path
PRIORITY={'.mhtml':0,'.mht':1,'.html':2,'.htm':3}
def number(p):
    s=p.stem
    m=re.fullmatch(r'\d+_(\d+)(?:__\d+_\1)?',s)
    if m:return int(m[1])
    if s.isdecimal():return int(s)
    m=re.search(r'(?:fordul[oó]|round)[ _.-]*(\d+)',s,re.I)
    if m:return int(m[1])
    try:
        with p.open('rb') as f: raw=f.read(262144)
        if p.suffix.lower() in ('.mhtml','.mht'):
            msg=email.message_from_bytes(raw,policy=policy.default)
            part=msg.get_body(preferencelist=('html',))
            if part: raw=part.get_payload(decode=True) or raw
        for enc in ('utf-8','cp1250','iso8859-2'):
            t=html.unescape(re.sub(r'<[^>]*>',' ',raw.decode(enc,errors='replace')))
            m=re.search(r'(?:fordul[oó](?:sz[aá]m)?\s*[:=]?\s*(\d+)|(\d+)\s*\.\s*fordul[oó])',t,re.I)
            if m:return int(m[1] or m[2])
    except (OSError,ValueError,TypeError):pass
    return None
def scan(folder,recursive,cache):
    root=Path(os.path.expandvars(folder)).expanduser(); found={}; unknown=[]; live=set()
    if not folder or not root.is_dir():return [],0
    for p in (root.rglob('*') if recursive else root.iterdir()):
        if p.suffix.lower() not in PRIORITY:continue
        try:
            if not p.is_file():continue
            st=p.stat(); key=str(p.absolute()); live.add(key); sig=(st.st_mtime_ns,st.st_size)
            if key not in cache or cache[key][0]!=sig:cache[key]=(sig,number(p))
            n=cache[key][1]
            if n is None:unknown.append(p);continue
            rank=(PRIORITY[p.suffix.lower()],-st.st_mtime_ns,key)
            if n not in found or rank<found[n][0]:found[n]=(rank,p)
        except OSError:continue
    return [(n,found[n][1]) for n in sorted(found,reverse=True)],len(unknown)
