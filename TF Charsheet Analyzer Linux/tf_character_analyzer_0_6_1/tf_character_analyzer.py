#!/usr/bin/env python3
"""TF Character Analyzer 0.6.1 — local multi-turn archive and skill trends."""
import webbrowser
import argparse, html, json, re, sqlite3, sys
from pathlib import Path
from datetime import datetime, timezone
from collections import defaultdict
from tf_parser import extract, parse, dashboard, original_html, STYLE, get_html
from bs4 import BeautifulSoup
from tf_report import report as interactive_report

def init(conn):
    conn.executescript('''PRAGMA foreign_keys=ON;
    CREATE TABLE IF NOT EXISTS turns(character TEXT NOT NULL, turn INTEGER NOT NULL, source TEXT NOT NULL, imported_at TEXT NOT NULL, PRIMARY KEY(character,turn));
    CREATE TABLE IF NOT EXISTS stats(character TEXT NOT NULL,turn INTEGER NOT NULL,name TEXT NOT NULL,base REAL,effective REAL,raw TEXT,PRIMARY KEY(character,turn,name),FOREIGN KEY(character,turn) REFERENCES turns(character,turn) ON DELETE CASCADE);
    CREATE TABLE IF NOT EXISTS skills(character TEXT NOT NULL,turn INTEGER NOT NULL,name TEXT NOT NULL,category TEXT,level INTEGER,progress INTEGER,raw TEXT,PRIMARY KEY(character,turn,name),FOREIGN KEY(character,turn) REFERENCES turns(character,turn) ON DELETE CASCADE);
    CREATE TABLE IF NOT EXISTS items(character TEXT NOT NULL,turn INTEGER NOT NULL,place TEXT NOT NULL,item_id TEXT NOT NULL,name TEXT,quantity TEXT,description TEXT,PRIMARY KEY(character,turn,place,item_id),FOREIGN KEY(character,turn) REFERENCES turns(character,turn) ON DELETE CASCADE);
    CREATE TABLE IF NOT EXISTS turn_metrics(character TEXT NOT NULL,turn INTEGER NOT NULL,xp INTEGER,kills INTEGER,total_xp INTEGER,total_kills INTEGER,PRIMARY KEY(character,turn));
    ''')

EXCLUDED = {'Merészség','Agresszió','Menekülés','Jellem','Pénz','Halhatatlanság','Magasság','Testsúly','Életkor','Tul. pont','Kép. pont','EFejl'}

def metrics(path):
    text=BeautifulSoup(get_html(path),'html.parser').get_text(' ',strip=True)
    patterns={'xp':r'Ebben a fordulóban\s+([\d ]+)\s+TP-t kaptál', 'kills':r'összesen\s+[\d ]+\s+szörnyet\s*\(([\d ]+)\s+ebben a körben\)', 'total_xp':r'Jelenleg\s+([\d ]+)\s+TP-d van', 'total_kills':r'Eddig összesen\s+([\d ]+)\s+szörnyet'}
    result={}
    for key,pattern in patterns.items():
        m=re.search(pattern,text,re.I);result[key]=int(m.group(1).replace(' ','')) if m else None
    return result

def import_turn(conn,path,out):
    doc=extract(path)
    if doc['turn'] is None: raise ValueError('Nem található a fordulószám; az import megszakadt.')
    parsed=parse(doc); c=doc['character']; t=doc['turn']; met=metrics(path)
    with conn:
        conn.execute('INSERT INTO turns VALUES (?,?,?,?) ON CONFLICT(character,turn) DO UPDATE SET source=excluded.source, imported_at=excluded.imported_at',(c,t,Path(path).name,datetime.now(timezone.utc).isoformat()))
        for table in ('stats','skills','items'):conn.execute(f'DELETE FROM {table} WHERE character=? AND turn=?',(c,t))
        conn.execute('INSERT OR REPLACE INTO turn_metrics VALUES (?,?,?,?,?,?)',(c,t,met['xp'],met['kills'],met['total_xp'],met['total_kills']))
        conn.executemany('INSERT INTO stats VALUES (?,?,?,?,?,?)',[(c,t,k,v['base'],v['effective'],v['raw']) for k,v in parsed['stats'].items() if k not in EXCLUDED])
        conn.executemany('INSERT INTO skills VALUES (?,?,?,?,?,?,?)',[(c,t,k,v['group'],v['level'],v['progress'],v['raw']) for k,v in parsed['skills'].items()])
        conn.executemany('INSERT INTO items VALUES (?,?,?,?,?,?,?)',[(c,t,place,ident,v['name'],v['quantity'],v['description']) for place,items in parsed['items'].items() for ident,v in items.items()])
    stem=re.sub(r'[^\w-]+','_',c)+'_'+str(t)
    (out/(stem+'_elemzes.html')).write_text(dashboard(doc),encoding='utf-8')
    (out/(stem+'_eredeti.html')).write_text(original_html(doc),encoding='utf-8')
    return c,t,len(parsed['skills'])

def svg_lines(points,labels,width=800,height=220):
    # Independent series scaled to their own range; label this explicitly.
    if not points:return ''
    colors=['#72b6ff','#77d7a0','#ffbd74','#d0a1ff','#f18d9e']
    chunks=[f'<svg viewBox="0 0 {width} {height}" role="img" aria-label="Fejlődési grafikon" style="width:100%;max-width:{width}px">']
    for i,(name,values) in enumerate(points.items()):
        valid=[(j,v) for j,v in enumerate(values) if v is not None]
        if not valid:continue
        lo=min(v for _,v in valid);hi=max(v for _,v in valid);pad=max((hi-lo)*.12,1)
        lo-=pad;hi+=pad
        coords=[(44+(width-70)*j/max(1,len(labels)-1),15+(height-50)*(hi-v)/(hi-lo)) for j,v in valid]
        chunks.append(f'<polyline fill="none" stroke="{colors[i%len(colors)]}" stroke-width="2.5" points="'+ ' '.join(f'{x:.1f},{y:.1f}' for x,y in coords)+'"/>')
        for (x,y),(j,v) in zip(coords,valid):chunks.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4" fill="{colors[i%len(colors)]}"><title>{html.escape(name)} · {labels[j]}: {v:g}</title></circle>')
    for j,label in enumerate(labels):
        x=44+(width-70)*j/max(1,len(labels)-1)
        chunks.append(f'<text x="{x:.1f}" y="{height-6}" fill="#b6c7df" font-size="12" text-anchor="middle">{label}</text>')
    chunks.append('</svg>')
    return ''.join(chunks)

def report(conn,character):
    esc=html.escape
    turns=[r[0] for r in conn.execute('SELECT turn FROM turns WHERE character=? ORDER BY turn',(character,))]
    if not turns:return ''
    stats=defaultdict(dict);skills=defaultdict(dict)
    for t,n,b,e in conn.execute('SELECT turn,name,base,effective FROM stats WHERE character=?',(character,)):stats[n][t]=(b,e)
    for t,n,g,l,p in conn.execute('SELECT turn,name,category,level,progress FROM skills WHERE character=?',(character,)):skills[n][t]=(g,l,p)
    first,last=turns[0],turns[-1]
    metric_rows=conn.execute('SELECT turn,xp,kills FROM turn_metrics WHERE character=? ORDER BY turn',(character,)).fetchall()
    xp_values=[x for _,x,_ in metric_rows if x is not None]
    kill_values=[x for _,_,x in metric_rows if x is not None]
    level_values=[(t,int(stats['Szint'][t][0])) for t in turns if t in stats.get('Szint',{})]
    level_gain=sum(max(0,b[1]-a[1]) for a,b in zip(level_values,level_values[1:]))
    elapsed=(level_values[-1][0]-level_values[0][0]) if len(level_values)>1 else 0
    pace=f'{elapsed/level_gain:.2f} forduló/szint' if level_gain and elapsed else 'Még nem mérhető'
    cards=[('Fordulók',str(len(turns))),('Időszak',f'{first}–{last}'),('Szint',str(level_values[-1][1]) if level_values else '—'),('Átlagos TP / forduló',f'{sum(xp_values)/len(xp_values):,.0f}'.replace(',',' ') if xp_values else '—'),('Átlagos megölt szörny / forduló',f'{sum(kill_values)/len(kill_values):.1f}'.replace('.',',') if kill_values else '—'),('Szintlépési sebesség',pace)]
    card_html=''.join(f'<div class="card"><div class="small">{esc(a)}</div><div class="big">{esc(b)}</div></div>' for a,b in cards)
    statrows=[]
    for n,vals in sorted(stats.items()):
        if n in EXCLUDED:continue
        old=vals.get(first);new=vals.get(last)
        if not old or not new:continue
        delta=new[0]-old[0];effective_delta=(new[1]-old[1]) if new[1] is not None and old[1] is not None else None
        statrows.append(f'<tr><td>{esc(n)}</td><td>{old[0]:g}</td><td>{new[0]:g}</td><td>{delta:+g}</td><td>{effective_delta:+g} ' if effective_delta is not None else f'<tr><td>{esc(n)}</td><td>{old[0]:g}</td><td>{new[0]:g}</td><td>{delta:+g}</td><td>—')
        statrows[-1]+='</td></tr>'
    skillrows=[];increases=[]
    for n,vals in skills.items():
        old=vals.get(first);new=vals.get(last)
        if not old or not new:continue
        dl=new[1]-old[1];dp=new[2]-old[2]
        if dl>0:increases.append((n,dl))
        # Progress after a level-up can wrap; do not combine it with level into arbitrary points.
        progress_note=f'{dp:+d}' if dl==0 else 'szintlépés – nem összegezhető'
        skillrows.append((dl,dp,n,f'<tr><td>{esc(n)}</td><td>{esc(new[0])}</td><td>{old[1]}/{old[2]}</td><td>{new[1]}/{new[2]}</td><td>{dl:+d}</td><td>{esc(progress_note)}</td></tr>'))
    skillrows.sort(key=lambda x:(-x[0],-x[1],x[2]))
    change_rows=[]
    for a,b in zip(turns,turns[1:]):
        for n,vals in skills.items():
            if a not in vals or b not in vals:continue
            prev,cur=vals[a],vals[b]
            if prev[1:]!=cur[1:]:
                change_rows.append(f'<tr><td>{a} → {b}</td><td>{esc(n)}</td><td>{prev[1]}/{prev[2]}</td><td>{cur[1]}/{cur[2]}</td><td>{cur[1]-prev[1]:+d}</td></tr>')
    select_names=[n for n,v in skills.items() if len(v)>=2]
    select_names.sort(key=lambda n:(-(skills[n].get(last,(None,0,0))[1]-skills[n].get(first,(None,0,0))[1]),n))
    default=select_names[:5]
    datasets={n:[skills[n].get(t,(None,None,None))[1] for t in turns] for n in select_names}
    chart=svg_lines({n:datasets[n] for n in default},turns)
    options=''.join(f'<option value="{esc(n,quote=True)}" {"selected" if n in default else ""}>{esc(n)}</option>' for n in select_names)
    # chart client redraw only when selecting skills; static SVG remains useful without JS.
    js='''<script>
const turns=__TURNS__, data=__DATA__;
const colors=['#72b6ff','#77d7a0','#ffbd74','#d0a1ff','#f18d9e'];
function redraw(){let names=[...document.querySelector('#chosen').selectedOptions].map(o=>o.value).slice(0,5);let w=800,h=220,svg=`<svg viewBox="0 0 ${w} ${h}" style="width:100%;max-width:800px" role="img" aria-label="Szakértelem szintgrafikon">`;
names.forEach((n,i)=>{let v=data[n],good=v.map((x,j)=>[x,j]).filter(a=>a[0]!==null);if(!good.length)return;let min=Math.min(...good.map(x=>x[0])),max=Math.max(...good.map(x=>x[0])),pad=Math.max((max-min)*.12,1);min-=pad;max+=pad;let coords=good.map(([val,j])=>[44+(w-70)*j/Math.max(1,turns.length-1),15+(h-50)*(max-val)/(max-min),val,j]);svg+=`<polyline fill="none" stroke="${colors[i]}" stroke-width="2.5" points="${coords.map(([x,y])=>x+','+y).join(' ')}"/>`;coords.forEach(([x,y,val,j])=>svg+=`<circle cx="${x}" cy="${y}" r="4" fill="${colors[i]}"><title>${n} · ${turns[j]}: ${val}</title></circle>`)});turns.forEach((t,j)=>svg+=`<text x="${44+(w-70)*j/Math.max(1,turns.length-1)}" y="${h-6}" fill="#b6c7df" font-size="12" text-anchor="middle">${t}</text>`);document.querySelector('#chart').innerHTML=svg+'</svg>';document.querySelector('#legend').textContent=names.join(' · ')}
document.querySelector('#chosen').addEventListener('change',redraw);
document.querySelector('#skillsearch').addEventListener('input',function(){let q=this.value.toLocaleLowerCase('hu'), sel=document.querySelector('#chosen');for(let o of sel.options){o.hidden=!o.textContent.toLocaleLowerCase('hu').includes(q);o.style.display=o.hidden?'none':'';}});
document.querySelectorAll('.filter').forEach(inp=>inp.addEventListener('input',()=>{let q=inp.value.toLocaleLowerCase('hu');document.querySelectorAll('#'+inp.dataset.target+' tbody tr').forEach(tr=>tr.classList.toggle('hidden',!tr.textContent.toLocaleLowerCase('hu').includes(q)))}));
</script>'''.replace('__TURNS__',json.dumps(turns)).replace('__DATA__',json.dumps(datasets,ensure_ascii=False))
    return f'''<!doctype html><html lang="hu"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>TF – {esc(character)} – fejlődéstörténet</title><style>{STYLE}select{{width:100%;max-width:580px}}.note{{padding:12px;border-left:3px solid #72b6ff;background:#182335}}.chartbox{{padding:15px;background:#182335;border:1px solid #31415b;border-radius:12px}}</style></head><body><nav><a href="#top">Áttekintés</a><a href="#chartsection">Grafikon</a><a href="#skills">Szakértelmek</a><a href="#stats">Tulajdonságok</a><a href="#log">Változásnapló</a></nav><main id="top"><h1>{esc(character)} – fejlődéstörténet</h1><p class="muted">TF Character Analyzer 0.5 · SQLite-alapú, helyi archívum</p><div class="cards">{card_html}</div><section id="chartsection"><h2>Szakértelmek alakulása</h2><p class="note">Legfeljebb öt szakértelem választható (Ctrl+kattintás). A grafikon minden sorozatot külön skáláz, ezért a görbék magassága nem alkalmas különböző szakértelmek szintjének közvetlen összehasonlítására. A pontos érték az adatpont fölé húzott egérrel látható.</p><input id="skillsearch" type="search" placeholder="Szakértelem szűrése név szerint…" aria-label="Szakértelmek szűrése"><p class="small">A keresés szűkíti a választható szakértelmeket. Ctrl+kattintással több is kijelölhető.</p><select id="chosen" multiple size="8">{options}</select><p class="small" id="legend">{esc(' · '.join(default))}</p><div class="chartbox" id="chart">{chart}</div></section><section id="skills"><h2>Szakértelmek: {first} → {last}</h2><p class="muted">A perjel utáni érték változását csak változatlan szint esetén számoljuk különbségként. Szintlépésnél az érték visszaállhat, ezért nem kezeljük összeadható fejlődési pontként.</p><input class="filter" data-target="skills-table" placeholder="Szakértelem keresése…"><div class="panel tablewrap"><table id="skills-table"><thead><tr><th>Szakértelem</th><th>Csoport</th><th>Első</th><th>Utolsó</th><th>Szintváltozás</th><th>Perjel utáni változás</th></tr></thead><tbody>{''.join(x[3] for x in skillrows)}</tbody></table></div></section><section id="stats"><h2>Tulajdonságok és harci értékek</h2><div class="panel tablewrap"><table><thead><tr><th>Mutató</th><th>Alap {first}</th><th>Alap {last}</th><th>Alap változás</th><th>Módosított változás</th></tr></thead><tbody>{''.join(statrows)}</tbody></table></div></section><section id="log"><h2>Szakértelem-változásnapló</h2><input class="filter" data-target="log-table" placeholder="Forduló vagy szakértelem keresése…"><div class="panel tablewrap"><table id="log-table"><thead><tr><th>Fordulók</th><th>Szakértelem</th><th>Előtte</th><th>Utána</th><th>Szintkülönbség</th></tr></thead><tbody>{''.join(change_rows)}</tbody></table></div></section><p class="muted">Forrás: importált TF karakterlapok. A hiányzó fordulókat nem becsüljük. Az eredeti HTML-ek külön exportálhatók.</p></main>{js}</body></html>'''

def main():
    p=argparse.ArgumentParser(description='TF Character Analyzer 0.6.1 – HTML/MHTML import, SQLite, fejlődéskövetés')
    p.add_argument('files',nargs='*');p.add_argument('-o','--output',default='tf_karakterlapok');args=p.parse_args()
    if not args.files:
        try:
            from tf_picker import choose_turns
            args.files=choose_turns()
        except Exception as exc:p.error('Nem sikerült megnyitni a fájlválasztót: '+str(exc))
    out=Path(args.output);out.mkdir(parents=True,exist_ok=True)
    conn=sqlite3.connect(out/'tf_karakterek.sqlite3');init(conn)
    errors=[];characters=set()
    for path in args.files:
        try:
            c,t,n=import_turn(conn,path,out);characters.add(c);print(f'Importálva: {c} – {t}. forduló – {n} szakértelem')
        except Exception as exc:errors.append((path,str(exc)));print('HIBA:',path,exc,file=sys.stderr)
    if not characters:characters={r[0] for r in conn.execute('SELECT DISTINCT character FROM turns')}
    reports=[]
    for c in sorted(characters):
        target=out/(re.sub(r'[^\w-]+','_',c)+'_fejlodestortenet.html')
        target.write_text(interactive_report(conn,c),encoding='utf-8');print('Fejlődéstörténet:',target);reports.append(target.resolve())
    conn.close();print('Adatbázis:',out/'tf_karakterek.sqlite3')
    if reports:
        try:
            for target in reports:
                if not webbrowser.open(target.as_uri(),new=2):
                    print('A böngésző nem nyílt meg automatikusan. Jelentés:',target,file=sys.stderr)
        except Exception as exc:
            print('A böngésző megnyitása nem sikerült:',exc,file=sys.stderr)
    if errors:raise SystemExit(f'{len(errors)} import sikertelen.')
if __name__=='__main__':main()
