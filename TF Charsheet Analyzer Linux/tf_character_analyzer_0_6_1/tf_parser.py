#!/usr/bin/env python3
"""TF Character Analyzer 0.2: HTML/MHTML import, semantic dashboard and comparisons."""
import argparse, email, html, json, re
from collections import defaultdict
from email import policy
from pathlib import Path
from bs4 import BeautifulSoup

STYLE='''*{box-sizing:border-box}body{background:#0d131e;color:#e8edf6;font:15px system-ui,sans-serif;margin:0}main{max-width:1300px;margin:auto;padding:24px}h1{font-size:27px;margin-bottom:5px}h2{font-size:20px;margin:24px 0 12px}a{color:#a4c9ff}nav{position:sticky;top:0;background:#192439;padding:12px;z-index:3;display:flex;gap:14px;flex-wrap:wrap}nav a{text-decoration:none}.muted{color:#a9b8cc}.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px}.card,.panel{background:#182335;border:1px solid #31415b;border-radius:12px;padding:16px}.big{font-size:27px;font-weight:750}.small{font-size:12px;color:#b6c7df}.positive{color:#78e2a4}.negative{color:#ff9d9d}table{width:100%;border-collapse:collapse}th,td{border-bottom:1px solid #35445a;padding:9px;text-align:left;vertical-align:top}th{background:#23324a;position:sticky;top:0}input,select{background:#101c2d;color:white;border:1px solid #516482;border-radius:8px;padding:11px;max-width:100%}input{width:420px}section{scroll-margin-top:20px}.tablewrap{max-height:550px;overflow:auto}.bar{background:#344257;border-radius:9px;height:9px;overflow:hidden}.bar span{display:block;background:#79adfa;height:100%}.hidden{display:none!important}.tag{background:#263951;padding:4px 8px;border-radius:7px}details{margin:10px 0}summary{cursor:pointer;padding:10px;background:#23334b;border-radius:7px}.original{overflow:auto}.original table{width:auto}.original td{border:1px solid #34455e;padding:5px}'''

def decode_bytes(data,enc=None):
    for codec in (enc,'utf-8-sig','utf-8','windows-1250','iso-8859-2'):
        if not codec:continue
        try:return data.decode(codec)
        except (UnicodeError,LookupError):pass
    return data.decode('utf-8',errors='replace')

def get_html(path):
    raw=Path(path).read_bytes()
    # MIME inspection, not extension alone: supports renamed files too.
    if b'MIME-Version:' in raw[:3000] or b'Content-Type: multipart/' in raw[:3000]:
        msg=email.message_from_bytes(raw,policy=policy.default)
        for part in msg.walk():
            if part.get_content_type()=='text/html':
                payload=part.get_payload(decode=True)
                if payload:return decode_bytes(payload,part.get_content_charset())
        if Path(path).suffix.lower() in ('.mhtml','.mht'):
            raise ValueError('Az MHTML-ben nem található text/html rész.')
    match=re.search(br'<meta[^>]*charset\s*=\s*["\']?([\w-]+)',raw[:12000],re.I)
    return decode_bytes(raw,match.group(1).decode('ascii') if match else None)

def extract(path):
    soup=BeautifulSoup(get_html(path),'html.parser')
    title=soup.find(lambda t:t.name in ('h1','h2','h3') and t.get_text(' ',strip=True).upper()=='KARAKTERLAP')
    if not title and soup.select_one('div.klap'):
        title=soup.select_one('div.klap')
        # Already extracted standalone HTML: include the first klap as well.
        standalone=True
    else:
        standalone=False
    if not title:raise ValueError('A KARAKTERLAP cím nem található.')
    blocks=[]
    # Collect only top-level klap elements following the heading.
    for node in ([title] if standalone else []) + list(title.next_elements):
        if getattr(node,'name',None)=='div' and 'klap' in node.get('class',[]):
            if not any(parent in blocks for parent in node.parents):blocks.append(node)
    if not blocks:raise ValueError('Nem találhatók a klap blokkok.')
    sections=[]
    for block in blocks:
        for table in block.find_all('table'):
            headings=[tr.get_text(' ',strip=True) for tr in table.select('tr.tfej')]
            rows=[]
            for tr in table.find_all('tr'):
                if 'tfej' in tr.get('class',[]):continue
                cells=[x.get_text(' ',strip=True) for x in tr.find_all(['td','th'],recursive=False)]
                if any(cells):rows.append(cells)
            sections.append({'name':headings[0] if headings else 'Általános adatok','rows':rows})
    fulltext=' '.join(b.get_text(' ',strip=True) for b in blocks)
    turn=re.search(r'Ez az\s+(\d+)\.\s+fordulód',fulltext)
    first=blocks[-1].get_text(' ',strip=True)
    name=first.split(',')[0] if ',' in first else Path(path).stem
    if standalone:
        heading=soup.find('h1')
        if heading and '·' in heading.get_text():name=heading.get_text(' ',strip=True).split('·')[0].strip()
        if not turn:
            m=re.search(r'(\d+)\.\s*forduló',soup.get_text(' ',strip=True))
            if m:turn=m
    return {'character':name,'turn':int(turn.group(1)) if turn else None,'source':Path(path).name,'sections':sections,'blocks_html':'\n'.join(str(x) for x in blocks)}

def numeric(s):
    m=re.match(r'^\s*(-?\d+(?:[.,]\d+)?)\s*(?:\(\s*(-?\d+(?:[.,]\d+)?)\s*\))?',s)
    if not m:return None
    return {'base':float(m.group(1).replace(',','.')),'effective':float(m.group(2).replace(',','.')) if m.group(2) else None,'raw':s}

def parse(doc):
    stats={};skills={};other={};items=defaultdict(dict)
    for idx,sec in enumerate(doc['sections']):
        title=sec['name']
        if idx==1:
            for row in sec['rows']:
                for j in range(0,len(row)-1,2):
                    key=row[j].rstrip(':').strip();val=row[j+1]
                    if key and (v:=numeric(val)) is not None:stats[key]=v
        if title in ('HARCI ISMERETEK','EGYÉB ISMERETEK'):
            group='Harci' if title=='HARCI ISMERETEK' else 'Egyéb'
            for row in sec['rows']:
                for j in range(0,len(row)-1,2):
                    key=re.sub(r'^\d+\.\s*','',row[j].rstrip(':').strip());val=row[j+1]
                    m=re.match(r'\s*(\d+)\s*/\s*(\d+)',val)
                    if m:skills[key]={'level':int(m.group(1)),'progress':int(m.group(2)),'raw':val,'group':group}
        if title=='FEJLESZTÉSI PONTOK':
            for row in sec['rows']:
                for c in row:
                    m=re.search(r'Felhasználatlan fejlesztési pont:\s*(\d+)',c)
                    if m:other['fejlesztesi_pont']=int(m.group(1))
        if title.startswith(('NÁLAD LÉVŐ TÁRGYAK','TÁRGYAID A BANK','TÁRGYAK A KT')):
            for row in sec['rows']:
                # TF item tables typically repeat quantity, marker, description triplets.
                for j in range(0,len(row)-2,3):
                    qty,marker,desc=row[j:j+3]
                    match=re.search(r'([#$])(\d+)\s*\)',desc)
                    if not match:continue
                    ident=match.group(1)+match.group(2)
                    items[title][ident]={'name':re.split(r'\s*\([#$]\d+',desc)[0].strip(),'quantity':qty.strip(),'marker':marker,'description':desc}
    return {'stats':stats,'skills':skills,'other':other,'items':dict(items)}

def changes(a,b):
    result=[]
    for typ,key in [('stats','base'),('skills','level')]:
        aa=a.get(typ,{});bb=b.get(typ,{})
        for name in sorted(set(aa)|set(bb)):
            old=aa.get(name,{}).get(key);new=bb.get(name,{}).get(key)
            if old!=new:
                result.append({'category':typ,'name':name,'before':old,'after':new,'delta':new-old if old is not None and new is not None else None})
    for place in sorted(set(a.get('items',{}))|set(b.get('items',{}))):
        aa=a.get('items',{}).get(place,{});bb=b.get('items',{}).get(place,{})
        for ident in sorted(set(aa)|set(bb)):
            old=aa.get(ident,{}).get('quantity');new=bb.get(ident,{}).get('quantity')
            if old!=new:result.append({'category':'items','place':place,'name':bb.get(ident,aa.get(ident))['name'],'id':ident,'before':old,'after':new,'delta':None})
    return result

def dashboard(doc):
    data=parse(doc);stats=data['stats'];skills=data['skills'];other=data['other']
    esc=html.escape
    cards=[]
    for label,value in [('Szint',str(int(stats['Szint']['base'])) if 'Szint' in stats else '—'),('Fejlesztési pont',str(other.get('fejlesztesi_pont','—'))),('Tárgytípusok (helyenként)',str(sum(len(x) for x in data['items'].values())))]:
        cards.append(f'<div class="card"><div class="small">{esc(label)}</div><div class="big">{esc(value)}</div></div>')
    statrows=''.join(f'<tr><td>{esc(k)}</td><td>{v["base"]:g}</td><td>' + (f'{v["effective"]:g} <span class="positive">(+{v["effective"]-v["base"]:g})</span>' if v['effective'] is not None and v['effective']>=v['base'] else f'{v["effective"]:g}' if v['effective'] is not None else '—') + '</td></tr>' for k,v in stats.items())
    skillrows=''.join(f'<tr><td>{esc(k)}</td><td>{esc(v["group"])}</td><td data-sort="{v["level"]}">{v["level"]}</td><td>{v["progress"]}</td><td>{esc(v["raw"])}</td></tr>' for k,v in sorted(skills.items(),key=lambda t:-t[1]['level']))
    inventory=[]
    for place,entries in data['items'].items():
        for ident,v in entries.items():inventory.append(f'<tr><td>{esc(v["name"])}</td><td>{esc(ident)}</td><td>{esc(v["quantity"])}</td><td>{esc(place)}</td><td>{esc(v["description"])}</td></tr>')
    nav='<nav><a href="#overview">Áttekintés</a><a href="#stats">Tulajdonságok</a><a href="#skills">Szakértelmek</a><a href="#items">Tárgyak</a><a href="#other">Eredeti adatok</a></nav>'
    raw=[]
    for i,s in enumerate(doc['sections']):
        rows=''.join('<tr>'+''.join('<td>'+esc(c)+'</td>' for c in row)+'</tr>' for row in s['rows'])
        raw.append(f'<details><summary>{esc(s["name"])} · {len(s["rows"])} sor</summary><div class="tablewrap"><table>{rows}</table></div></details>')
    body=f'''<section id="overview"><h2>Áttekintés</h2><div class="cards">{''.join(cards)}</div><p class="muted">A zárójelben szereplő módosított értékeket külön mutatjuk. Nem következtetünk automatikusan a módosítás okára.</p></section>
    <section id="stats"><h2>Tulajdonságok és harci értékek</h2><div class="panel tablewrap"><table><thead><tr><th>Mutató</th><th>Alapérték</th><th>Módosított érték</th></tr></thead><tbody>{statrows}</tbody></table></div></section>
    <section id="skills"><h2>Szakértelmek</h2><p class="muted">Szint szerint csökkenő sorrendben; a perjel utáni értéket külön kezeljük.</p><input class="filter" data-target="skills-table" placeholder="Szakértelem keresése…"><div class="panel tablewrap"><table id="skills-table"><thead><tr><th>Név</th><th>Csoport</th><th>Szint</th><th>Perjel utáni érték</th><th>Eredeti adat</th></tr></thead><tbody>{skillrows}</tbody></table></div></section>
    <section id="items"><h2>Tárgyak és tárolási helyek</h2><p class="muted">Az azonosítók alapján azonos tárgyak több helyen is megtalálhatók. A darabszámok szövegesen megőrzöttek (például a $ jelzés is).</p><input class="filter" data-target="items-table" placeholder="Tárgy neve vagy azonosítója…"><div class="panel tablewrap"><table id="items-table"><thead><tr><th>Tárgy</th><th>Azonosító</th><th>Mennyiség</th><th>Hely</th><th>Eredeti leírás</th></tr></thead><tbody>{''.join(inventory)}</tbody></table></div></section>
    <section id="other"><h2>Összes eredeti adatsor</h2><p class="muted">A még nem strukturált részek is hozzáférhetők, információvesztés nélkül.</p>{''.join(raw)}</section>'''
    js='''<script>document.querySelectorAll('.filter').forEach(inp=>inp.addEventListener('input',()=>{let q=inp.value.toLocaleLowerCase('hu');document.querySelectorAll('#'+inp.dataset.target+' tbody tr').forEach(tr=>tr.classList.toggle('hidden',!tr.textContent.toLocaleLowerCase('hu').includes(q)))}));</script>'''
    return f'<!doctype html><html lang="hu"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>TF – {esc(doc["character"])} – {doc["turn"]}</title><style>{STYLE}</style>{nav}<main><h1>{esc(doc["character"])} · {doc["turn"] or "?"}. forduló</h1><p class="muted">TF Character Analyzer 0.2 · Elemző karakterprofil</p>{body}</main>{js}</html>'

def original_html(doc):
    return f'<!doctype html><html lang="hu"><meta charset="utf-8"><title>TF karakterlap</title><style>{STYLE}</style><main><h1>{html.escape(doc["character"])} · {doc["turn"] or "?"}. forduló</h1><div class="original">{doc["blocks_html"]}</div></main></html>'

def comparison_html(a,b,rows):
    esc=html.escape
    groups=defaultdict(list)
    for r in rows:groups[r['category']].append(r)
    content=''
    for group,label in [('stats','Tulajdonságok'),('skills','Szakértelmek'),('items','Tárgyak (helyenként)')]:
        rr=groups[group]
        body=''.join(f'<tr><td>{esc(r["name"])}</td><td>{esc(str(r["before"]))}</td><td>{esc(str(r["after"]))}</td><td class="{"positive" if (r["delta"] or 0)>0 else "negative" if (r["delta"] or 0)<0 else ""}">{"%+g"%r["delta"] if r["delta"] is not None else "—"}</td><td>{esc(r.get("place",""))}</td></tr>' for r in rr)
        content+=f'<section><h2>{label} · {len(rr)} változás</h2><div class="panel tablewrap"><table><thead><tr><th>Név</th><th>Korábban</th><th>Most</th><th>Változás</th><th>Hely</th></tr></thead><tbody>{body}</tbody></table></div></section>'
    return f'<!doctype html><html lang="hu"><meta charset="utf-8"><title>TF változások</title><style>{STYLE}</style><main><h1>{a["turn"]} → {b["turn"]}. forduló</h1><p class="muted">Az értékek összehasonlítása nem azonos a fejlődés okának megállapításával.</p>{content}</main></html>'

def main():
    ap=argparse.ArgumentParser(description='TF Character Analyzer 0.2 – HTML/MHTML karakterlapok és fejlődéskövetés')
    ap.add_argument('files',nargs='*',help='HTML, HTM, MHTML vagy MHT fordulók')
    ap.add_argument('-o','--output',default='tf_karakterlapok',help='Kimeneti mappa')
    args=ap.parse_args()
    if not args.files:
        try:
            from tkinter import Tk,filedialog
            root=Tk();root.withdraw()
            args.files=list(filedialog.askopenfilenames(title='TF fordulók kiválasztása',filetypes=[('TF fordulók','*.html *.htm *.mhtml *.mht'),('Minden fájl','*.*')]))
            root.destroy()
        except Exception as e:ap.error('Adj meg HTML/MHTML fájlokat: '+str(e))
    if not args.files:return
    out=Path(args.output);out.mkdir(parents=True,exist_ok=True)
    docs=[];failures=[]
    for path in args.files:
        try:
            doc=extract(path);docs.append(doc)
            stem=re.sub(r'[^\w-]+','_',doc['character'])+'_'+str(doc['turn'] or 'ismeretlen')
            (out/(stem+'.json')).write_text(json.dumps({'character':doc['character'],'turn':doc['turn'],'source':doc['source'],'parsed':parse(doc),'sections':doc['sections']},ensure_ascii=False,indent=2),encoding='utf-8')
            (out/(stem+'_elemzes.html')).write_text(dashboard(doc),encoding='utf-8')
            (out/(stem+'_eredeti.html')).write_text(original_html(doc),encoding='utf-8')
            print('Exportálva:',stem)
        except Exception as e:
            failures.append(f'{path}: {e}');print('HIBA:',failures[-1])
    docs.sort(key=lambda d:d['turn'] or 0)
    for a,b in zip(docs,docs[1:]):
        if a['character']!=b['character']:
            print('Eltérő karakterek, összehasonlítás kihagyva:',a['character'],b['character']);continue
        diff=changes(parse(a),parse(b));stem=f'valtozasok_{a["turn"]}_{b["turn"]}'
        (out/(stem+'.json')).write_text(json.dumps(diff,ensure_ascii=False,indent=2),encoding='utf-8')
        (out/(stem+'.html')).write_text(comparison_html(a,b,diff),encoding='utf-8')
        print('Összehasonlítás:',stem)
    print('Kimeneti mappa:',out.resolve())
    if failures:raise SystemExit(f'{len(failures)} fájl feldolgozása sikertelen.')
if __name__=='__main__':main()
