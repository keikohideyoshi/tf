"""Interactive, offline multi-turn report. All filtering runs locally in browser."""
import html
import json
from collections import defaultdict
from tf_parser import STYLE

BASICS = ['Erő', 'IQ', 'Ügyesség', 'Egészség', 'Szerencse']
COMBAT_ORDER = ['Támadás', 'Védekezés', 'Életpont', 'Varázspont', 'Pszi pont', 'Tudatpont']
EXCLUDED = {'Merészség','Agresszió','Menekülés','Jellem','Pénz','Halhatatlanság','Magasság','Testsúly','Életkor','Tul. pont','Kép. pont','EFejl'}

def report(conn, character):
    turns=[r[0] for r in conn.execute('SELECT turn FROM turns WHERE character=? ORDER BY turn',(character,))]
    if not turns:return ''
    stats=defaultdict(dict);skills=defaultdict(dict)
    for t,n,b,e in conn.execute('SELECT turn,name,base,effective FROM stats WHERE character=?',(character,)):
        if n not in EXCLUDED: stats[n][t]={'base':b,'effective':e}
    for t,n,g,l,p in conn.execute('SELECT turn,name,category,level,progress FROM skills WHERE character=?',(character,)):
        skills[n][t]={'group':g,'level':l,'progress':p}
    metrics={t:{'xp':xp,'kills':kills} for t,xp,kills in conn.execute('SELECT turn,xp,kills FROM turn_metrics WHERE character=?',(character,))}
    data={'turns':turns,'stats':stats,'skills':skills,'metrics':metrics,'basics':BASICS,'combatOrder':COMBAT_ORDER}
    # Prevent HTML/script injection through source-derived names.
    payload=json.dumps(data,ensure_ascii=False).replace('<','\\u003c').replace('>','\\u003e').replace('&','\\u0026')
    title=html.escape(character)
    css='''
    html{scroll-behavior:smooth;scroll-padding-top:105px}
    section{scroll-margin-top:105px}
    nav.tf-nav{position:sticky;top:0;z-index:20;display:flex;justify-content:center;align-items:center;flex-wrap:wrap;gap:6px;padding:10px 16px;background:rgba(17,26,43,.96);border-bottom:1px solid #34445c;box-shadow:0 8px 25px #0005;backdrop-filter:blur(14px)}
    nav.tf-nav a{display:inline-flex;align-items:center;gap:8px;padding:10px 13px;border-radius:11px;color:#cbd5e1;text-decoration:none;font-size:13px;font-weight:550;transition:background .15s,color .15s,transform .15s}
    nav.tf-nav a:hover{background:#263c5c;color:white;transform:translateY(-1px)}
    nav.tf-nav a.active,nav.tf-nav a[aria-current=location]{background:#355b92;color:#fff;box-shadow:inset 0 0 0 1px #658cc2}
    nav.tf-nav a svg{width:17px;height:17px;flex:none;stroke:currentColor;fill:none;stroke-width:1.9;stroke-linecap:round;stroke-linejoin:round}
    @media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}nav.tf-nav a{transition:none}}
    .toolbar{display:flex;align-items:end;gap:14px;flex-wrap:wrap}.toolbar label{display:flex;flex-direction:column;gap:6px;color:#b6c7df;font-size:13px}
    .toolbar select{min-width:145px}.chartbox{background:#111c2e;border:1px solid #31415b;border-radius:12px;padding:12px;margin:12px 0}
    .note{border-left:3px solid #72b6ff;background:#182335;padding:12px;margin:12px 0}
    .legend{display:flex;gap:14px;flex-wrap:wrap;margin:8px 0}.legend span{font-size:13px;color:#cbd9eb}
    .swatch{display:inline-block;width:11px;height:11px;border-radius:3px;margin-right:6px}
    .chartbox svg{display:block;width:100%;height:auto;max-height:330px}
    .filter{margin:8px 0}.muted{line-height:1.5}
    .empty{padding:14px;color:#b6c7df}.rowcontrols{display:flex;gap:12px;align-items:center;flex-wrap:wrap}
    .rowcontrols select{min-width:320px;max-width:100%}
    @media(max-width:620px){main{padding:14px}.toolbar{align-items:stretch}.toolbar label{flex:1}.rowcontrols select{min-width:0;width:100%}}
    '''
    body=r'''
    <nav class="tf-nav" aria-label="Jelentés navigáció">
    <a href="#top" class="active" aria-current="location"><svg viewBox="0 0 24 24"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg>Áttekintés</a>
    <a href="#levels"><svg viewBox="0 0 24 24"><path d="m3 17 6-6 4 4 8-9"/><path d="M16 6h5v5"/></svg>Szintlépések</a>
    <a href="#basics"><svg viewBox="0 0 24 24"><path d="M3 9v6m3-9v12m3-9v6m6-6v6m3-9v12m3-9v6M3 12h18"/></svg>Alaptulajdonságok</a>
    <a href="#other"><svg viewBox="0 0 24 24"><path d="m4 20 7-7m2-2 7-7M14 4l6 6M4 4l16 16"/></svg>Harci és egyéb</a>
    <a href="#skillchart"><svg viewBox="0 0 24 24"><path d="M4 20V12m5 8V7m5 13v-5m5 5V4"/></svg>Szakértelmek</a>
    <a href="#log"><svg viewBox="0 0 24 24"><path d="M3 12a9 9 0 1 0 3-7"/><path d="M3 3v5h5m4-1v5l4 2"/></svg>Változásnapló</a>
    </nav>
    <main id="top"><h1>__TITLE__ – fejlődéstörténet</h1><p class="muted">TF Character Analyzer 0.5.1 · Helyben működő interaktív jelentés</p>
    <section><h2>Vizsgálati időszak</h2><div class="panel toolbar"><label>Kezdő forduló<select id="from"></select></label><label>Záró forduló<select id="to"></select></label><button id="reset" type="button">Teljes időszak</button><span id="rangeinfo" class="muted" aria-live="polite"></span></div>
    <p class="muted">Az időszak módosítása az összes alábbi mutatót, grafikont és táblázatot azonnal újraszámolja. Az adatbázis változatlan marad.</p></section>
    <div class="cards" id="cards"></div>
    <section id="levels"><h2>Szintlépések alakulása</h2><p class="muted">Vízszintesen a fordulószám, függőlegesen a karakter szintje. A pontok a forduló végi állapotot jelzik.</p><div class="chartbox" id="levelchart"></div></section>
    <section id="basics"><h2>Alaptulajdonságok fejlődése</h2><p class="muted">Sorrend: Erő, IQ, Ügyesség, Egészség, Szerencse. A grafikon az alapértékeket mutatja, nem a felszerelés vagy hatások miatt módosított értékeket.</p><div class="chartbox" id="basicchart"></div><div class="panel tablewrap"><table><thead><tr><th>Alaptulajdonság</th><th>Első alapérték</th><th>Utolsó alapérték</th><th>Változás</th><th>Módosított érték változása</th></tr></thead><tbody id="basicrows"></tbody></table></div></section>
    <section id="other"><h2>Harci és egyéb értékek</h2><div class="panel tablewrap"><table><thead><tr><th>Mutató</th><th>Első alapérték</th><th>Utolsó alapérték</th><th>Változás</th><th>Módosított érték változása</th></tr></thead><tbody id="otherrows"></tbody></table></div></section>
    <section id="skillchart"><h2>Szakértelmek alakulása</h2><p class="note">Legfeljebb öt szakértelem választható. A grafikon minden sorozatot külön skáláz, ezért a görbék magassága nem alkalmas a különböző szakértelmek szintjeinek közvetlen összehasonlítására. A pontos érték az adatpont fölé húzott egérrel látható.</p>
    <div class="rowcontrols"><input id="skillsearch" type="search" placeholder="Szakértelem keresése…" aria-label="Szakértelem keresése"><button id="clearskills" type="button">Kijelölések törlése</button></div>
    <p class="small">Kattintással kijelölhető vagy eltávolítható egy szakértelem. A keresés a listát szűri, a kijelölést nem törli.</p><div class="rowcontrols"><select id="chosen" multiple size="8" aria-label="Szakértelmek kiválasztása"></select><span id="selectioninfo" class="muted"></span></div>
    <div class="legend" id="skilllegend"></div><div class="chartbox" id="skillgraph"></div></section>
    <section id="skills"><h2 id="skillstitle">Szakértelmek változása</h2><p class="muted">A perjel utáni érték különbségét csak változatlan szintnél számoljuk. Szintlépésnél nem tekintjük egyszerűen összeadható fejlődési pontnak.</p><input class="filter" id="skillfilter" placeholder="Szakértelem keresése…"><div class="panel tablewrap"><table><thead><tr><th>Szakértelem</th><th>Csoport</th><th>Első</th><th>Utolsó</th><th>Szintváltozás</th><th>Perjel utáni változás</th></tr></thead><tbody id="skillrows"></tbody></table></div></section>
    <section id="log"><h2>Szakértelem-változásnapló</h2><input class="filter" id="logfilter" placeholder="Forduló vagy szakértelem keresése…"><div class="panel tablewrap"><table><thead><tr><th>Fordulók</th><th>Szakértelem</th><th>Előtte</th><th>Utána</th><th>Szintkülönbség</th></tr></thead><tbody id="logrows"></tbody></table></div></section>
    <p class="muted">Forrás: importált karakterlapok és fordulószövegek. Hiányzó adatokból nem készül becslés. A változás két forduló végi állapot különbsége, az átlagok a kijelölt fordulók teljesítményéből készülnek.</p></main>
    '''
    js=r'''
    <script id="tfdata" type="application/json">__PAYLOAD__</script>
    <script>
    'use strict';
    const D=JSON.parse(document.getElementById('tfdata').textContent), turns=D.turns;
    const $=id=>document.getElementById(id);
    const colors=['#72b6ff','#77d7a0','#ffbd74','#d0a1ff','#f18d9e'];
    const nf=new Intl.NumberFormat('hu-HU',{maximumFractionDigits:2});
    const fmt=x=>x===null||x===undefined?'—':nf.format(x);
    const signed=x=>x===null||x===undefined?'—':(x>0?'+':'')+fmt(x);
    const el=(tag,txt)=>{const n=document.createElement(tag);n.textContent=txt;return n;};
    function rows(id,records){const body=$(id);body.replaceChildren();if(!records.length){const tr=el('tr',''),td=el('td','Nincs összehasonlítható adat a kiválasztott időszakban.');td.colSpan=8;tr.append(td);body.append(tr);return;}for(const record of records){const tr=document.createElement('tr');for(const value of record)tr.append(el('td',String(value)));body.append(tr);}}
    for(const t of turns){for(const id of ['from','to']){const o=el('option',String(t));o.value=String(t);$(id).append(o);}}
    $('from').value=String(turns[0]);$('to').value=String(turns.at(-1));
    let chosen=[];
    function selected(){const a=Number($('from').value),b=Number($('to').value);return turns.filter(t=>t>=a&&t<=b);}
    function getStat(n,t){return D.stats[n]?.[t]??null;}
    function getSkill(n,t){return D.skills[n]?.[t]??null;}
    function average(values){return values.length?values.reduce((a,b)=>a+b,0)/values.length:null;}
    function setCards(entries){$('cards').replaceChildren();for(const [name,value] of entries){const card=el('div','');card.className='card';const label=el('div',name),big=el('div',value);label.className='small';big.className='big';card.append(label,big);$('cards').append(card);}}
    function chart(id,series,ts,{shared=true,integer=false}={}){
      const root=$(id);root.replaceChildren();const valid=series.flatMap(s=>s.values.filter(x=>x!==null&&Number.isFinite(x)));
      if(!valid.length){root.append(el('p','Nincs ábrázolható adat.'));return;}
      const w=920,h=310,left=72,right=22,top=23,bottom=48;
      const svg=document.createElementNS('http://www.w3.org/2000/svg','svg');svg.setAttribute('viewBox',`0 0 ${w} ${h}`);svg.setAttribute('role','img');svg.setAttribute('aria-label',id==='levelchart'?'Szintfejlődés fordulószám szerint':'Fordulónkénti fejlődési grafikon');
      const add=(tag,attrs,content)=>{const n=document.createElementNS(svg.namespaceURI,tag);for(const [k,v] of Object.entries(attrs))n.setAttribute(k,String(v));if(content!==undefined)n.textContent=content;svg.append(n);return n;};
      const xrange=Math.max(1,ts.at(-1)-ts[0]),x=t=>left+(w-left-right)*(t-ts[0])/xrange;
      const allmin=Math.min(...valid),allmax=Math.max(...valid);
      let low=allmin,high=allmax;
      if(integer){low=Math.floor(allmin-0.5);high=Math.ceil(allmax+0.5);if(high<=low)high=low+1;}
      else{const pad=Math.max((high-low)*.12,1);low-=pad;high+=pad;}
      const y=v=>top+(h-top-bottom)*(high-v)/(high-low);
      for(let k=0;k<=4;k++){const val=low+(high-low)*k/4,py=y(val);add('line',{x1:left,y1:py,x2:w-right,y2:py,stroke:'#33435b','stroke-width':1});add('text',{x:left-9,y:py+4,'text-anchor':'end',fill:'#c2d1e5','font-size':12},integer?fmt(Math.round(val)):fmt(val));}
      const step=Math.max(1,Math.ceil(ts.length/12));ts.forEach((t,j)=>{if(j%step!==0&&j!==ts.length-1)return;add('text',{x:x(t),y:h-15,'text-anchor':'middle',fill:'#c2d1e5','font-size':12},String(t));});
      series.forEach((s,i)=>{const good=ts.map((t,j)=>({t,v:s.values[j]})).filter(p=>p.v!==null&&Number.isFinite(p.v));if(!good.length)return;
        let l=low,u=high;if(!shared){l=Math.min(...good.map(p=>p.v));u=Math.max(...good.map(p=>p.v));const pad=Math.max((u-l)*.12,1);l-=pad;u+=pad;}
        const sy=v=>top+(h-top-bottom)*(u-v)/(u-l);
        let segment=[];const flush=()=>{if(segment.length>1)add('polyline',{points:segment.join(' '),fill:'none',stroke:colors[i%colors.length],'stroke-width':2.7,'stroke-linejoin':'round'});segment=[];};
        for(const t of ts){const p=good.find(p=>p.t===t);if(!p){flush();continue;}const px=x(t),py=sy(p.v);segment.push(`${px},${py}`);const dot=add('circle',{cx:px,cy:py,r:4.2,fill:colors[i%colors.length]});const tip=document.createElementNS(svg.namespaceURI,'title');tip.textContent=`${s.name} · ${t}. forduló: ${fmt(p.v)}`;dot.append(tip);}flush();
      });
      root.append(svg);
      if(id==='basicchart'||id==='skillgraph'){const legend=id==='basicchart'?document.createElement('div'):$('skilllegend');legend.className='legend';legend.replaceChildren();series.forEach((s,i)=>{const span=el('span',s.name),swatch=el('i','');swatch.className='swatch';swatch.style.background=colors[i%colors.length];span.prepend(swatch);legend.append(span);});if(id==='basicchart')root.append(legend);}
    }
    function statTable(names,ts,id){const first=ts[0],last=ts.at(-1);const result=[];for(const name of names){const a=getStat(name,first),b=getStat(name,last);if(!a||!b||a.base===null||b.base===null)continue;result.push([name,fmt(a.base),fmt(b.base),signed(b.base-a.base),a.effective!==null&&b.effective!==null?signed(b.effective-a.effective):'—']);}rows(id,result);}
    function skillOptions(){const q=$('skillsearch').value.toLocaleLowerCase('hu');const opts=$('chosen');opts.replaceChildren();const names=Object.keys(D.skills).sort((a,b)=>a.localeCompare(b,'hu'));for(const n of names){if(!n.toLocaleLowerCase('hu').includes(q))continue;const o=el('option',n);o.value=n;o.selected=chosen.includes(n);opts.append(o);}$('selectioninfo').textContent=`${chosen.length}/5 kiválasztva`;}
    function skillChart(ts){const series=chosen.map(n=>({name:n,values:ts.map(t=>getSkill(n,t)?.level??null)}));chart('skillgraph',series,ts,{shared:false});}
    function update(){const ts=selected();if(!ts.length)return;const first=ts[0],last=ts.at(-1);
      $('rangeinfo').textContent=`${first}–${last} · ${ts.length} betöltött forduló`;
      const xp=ts.map(t=>D.metrics[t]?.xp).filter(v=>v!==null&&v!==undefined),kills=ts.map(t=>D.metrics[t]?.kills).filter(v=>v!==null&&v!==undefined);
      const levels=ts.map(t=>({t,level:getStat('Szint',t)?.base??null})).filter(p=>p.level!==null);
      const gain=levels.length>=2?levels.at(-1).level-levels[0].level:0;
      const pace=levels.length<2?'Nincs elegendő adat':gain<=0?'Nem történt szintlépés':fmt((levels.at(-1).t-levels[0].t)/gain)+' forduló/szint';
      setCards([['Fordulók',String(ts.length)],['Időszak',`${first}–${last}`],['Átlagos TP / forduló',fmt(average(xp))],['Átlagos szörnyölés / forduló',fmt(average(kills))],['Szintlépési sebesség',pace]]);
      chart('levelchart',[{name:'Szint',values:ts.map(t=>getStat('Szint',t)?.base??null)}],ts,{shared:true,integer:true});
      chart('basicchart',D.basics.map(n=>({name:n,values:ts.map(t=>getStat(n,t)?.base??null)})),ts,{shared:true});
      statTable(D.basics,ts,'basicrows');statTable(D.combatOrder.filter(n=>D.stats[n]),ts,'otherrows');
      $('skillstitle').textContent=`Szakértelmek: ${first} → ${last}`;
      const skillrecords=[];for(const n of Object.keys(D.skills)){const a=getSkill(n,first),b=getSkill(n,last);if(!a||!b)continue;const dl=b.level-a.level,dp=b.progress-a.progress;skillrecords.push({n,dl,dp,record:[n,b.group||a.group||'—',`${a.level}/${a.progress}`,`${b.level}/${b.progress}`,signed(dl),dl===0?signed(dp):'szintlépés – nem összegezhető']});}
      skillrecords.sort((a,b)=>b.dl-a.dl||b.dp-a.dp||a.n.localeCompare(b.n,'hu'));rows('skillrows',skillrecords.map(r=>r.record));
      const log=[];for(let i=1;i<ts.length;i++){const a=ts[i-1],b=ts[i];for(const n of Object.keys(D.skills)){const prev=getSkill(n,a),cur=getSkill(n,b);if(!prev||!cur||prev.level===cur.level&&prev.progress===cur.progress)continue;log.push([`${a} → ${b}`,n,`${prev.level}/${prev.progress}`,`${cur.level}/${cur.progress}`,signed(cur.level-prev.level)]);}}rows('logrows',log);
      for(const id of ['skillfilter','logfilter'])filterRows(id,id==='skillfilter'?'skillrows':'logrows');skillChart(ts);
    }
    function filterRows(inputId,bodyId){const q=$(inputId).value.toLocaleLowerCase('hu');for(const tr of $(bodyId).rows)tr.classList.toggle('hidden',!tr.textContent.toLocaleLowerCase('hu').includes(q));}
    $('from').addEventListener('change',()=>{if(Number($('from').value)>Number($('to').value))$('to').value=$('from').value;update();});
    $('to').addEventListener('change',()=>{if(Number($('to').value)<Number($('from').value))$('from').value=$('to').value;update();});
    $('reset').addEventListener('click',()=>{$('from').value=String(turns[0]);$('to').value=String(turns.at(-1));update();});
    $('skillsearch').addEventListener('input',skillOptions);
    $('chosen').addEventListener('change',()=>{const visible=[...$('chosen').selectedOptions].map(o=>o.value);const retained=chosen.filter(n=>![...$('chosen').options].some(o=>o.value===n));const next=[...retained,...visible];if(next.length>5){$('selectioninfo').textContent='Legfeljebb 5 szakértelem jelölhető ki.';skillOptions();return;}chosen=next;skillOptions();skillChart(selected());});
    $('clearskills').addEventListener('click',()=>{chosen=[];skillOptions();skillChart(selected());});
    for(const [id,target] of [['skillfilter','skillrows'],['logfilter','logrows']])$(id).addEventListener('input',()=>filterRows(id,target));
    const navlinks=[...document.querySelectorAll('.tf-nav a')];
    function setActiveNav(hash){navlinks.forEach(a=>{const active=a.getAttribute('href')===hash;a.classList.toggle('active',active);if(active)a.setAttribute('aria-current','location');else a.removeAttribute('aria-current');});}
    navlinks.forEach(a=>a.addEventListener('click',()=>setActiveNav(a.getAttribute('href'))));
    if('IntersectionObserver' in window){const obs=new IntersectionObserver(entries=>{const candidates=entries.filter(e=>e.isIntersecting).sort((a,b)=>a.boundingClientRect.top-b.boundingClientRect.top);if(candidates.length)setActiveNav('#'+candidates[0].target.id);},{rootMargin:'-110px 0px -55% 0px',threshold:0});['top','levels','basics','other','skillchart','log'].forEach(id=>obs.observe($(id)));}
    chosen=Object.keys(D.skills).sort((a,b)=>a.localeCompare(b,'hu')).slice(0,5);skillOptions();update();
    </script>
    '''
    return '<!doctype html><html lang="hu"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>TF – '+title+' – fejlődéstörténet</title><style>'+STYLE+css+'</style></head><body>'+body.replace('__TITLE__',title)+js.replace('__PAYLOAD__',payload)+'</body></html>'
