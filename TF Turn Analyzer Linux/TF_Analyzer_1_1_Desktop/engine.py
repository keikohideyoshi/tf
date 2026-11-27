from collections import Counter
import pandas as pd
from tvp import analyze, analyze_html, movement_conditionals_html, conditional_healing_html
from combat import analyze_combat, analyze_combat_html

def report(turns, progress=lambda s:None):
    tvp=[]; battles=[]; cond=[]; overview=[]; commands=[]; errors=[]
    for i,x in enumerate(turns):
        progress(f'Elemzés: {i+1}/{len(turns)} – {x["turn"]}')
        h=x.get('_html'); t=x['turn']; text=x['text']
        r=analyze_html(h) if h else analyze(text)
        tvp.extend(dict(Forduló=t, **{'Típus':v['kind'],'TVP':v['amount'],'Kategória':v['category'],'KP':v['kp'],'Parancs':v['command'],'Egyenleg':v['balance'],'Ellenőrzés':v['quality'],'Sor':v['line'],'Bizonyíték':v['evidence'],'Környezet':v.get('context',''),'Módszer':v.get('method','')}) for v in r)
        c=movement_conditionals_html(h) if h else {}
        cond.append({'Forduló':t,'M összes TVP':-sum(v['amount'] for v in r if v['kind']=='Kiadás' and v['category']=='M'),'Feltételes kutatás':c.get('Feltételes kutatás'),'Feltételes mászás':c.get('Feltételes mászás'),'Feltételes gyógyítás':conditional_healing_html(h) if h else None})
        rows=analyze_combat_html(h,text,t) if h else analyze_combat(text,t)
        for j, battle in enumerate(rows,1):
            battle['battle_no']=j
            battle['source_hash']=x['hash']
        battles.extend(rows)
        overview.append({'Forduló':t,'Fájl':x['filename'],'Parancssorok':len(x['commands']),'Szövegsorok':x['lines'],'Hibajelzések':len(x['failures']),'HTML':'Igen' if h else 'Hiányzik'})
        commands.extend({'Forduló':t,'Parancs':v['command'],'Paraméterek':v['arguments'],'Sor':v['line'],'Környezet':v['context']} for v in x['commands'])
        errors.extend({'Forduló':t,'Sor':v['line'],'Részlet':v['text']} for v in x['failures'])
    d=pd.DataFrame(tvp); b=pd.DataFrame(battles); cmd=pd.DataFrame(commands)
    out={'Fordulók':pd.DataFrame(overview),'TVP események':d,'Feltételes események':pd.DataFrame(cond),'Összes csata':b,'Parancsok':cmd,'Hibajelzések':pd.DataFrame(errors)}
    if not d.empty:
        out['Bevételek']=d[d['Típus']=='Bevétel'].groupby('Kategória',as_index=False)['TVP'].sum().sort_values('TVP',ascending=False)
        out['Kiadások']=d[d['Típus']=='Kiadás'].assign(TVP=lambda x:-x.TVP).groupby('Kategória',as_index=False)['TVP'].sum().sort_values('TVP',ascending=False)
        out['Fordulónkénti TVP']=d[d['Típus'].isin(['Bevétel','Kiadás'])].groupby(['Forduló','Típus'],as_index=False)['TVP'].sum()
    if not b.empty:
        s=b.groupby('monster',as_index=False).agg(Harcok=('taken','size'),Átlag_sebzés=('taken','mean'),Átlag_gyógyulás=('healed','mean'),Átlag_nettó=('net','mean'),Max_sebzés=('taken','max'),Összes_sebzés=('taken','sum'),Becsült_kör=('rounds_est','mean'),Öt_körös=('rounds_est',lambda x:int((x==5).sum())),Tartalék=('reserve_est','mean'),Átlag_TP=('xp','mean'))
        s['Öt körös %']=100*s['Öt_körös']/s['Harcok']; out['Szörnyenként']=s.rename(columns={'monster':'Szörny'}).sort_values('Átlag_sebzés',ascending=False)
    if not cmd.empty: out['Parancsok összesítve']=cmd.groupby('Parancs').size().reset_index(name='Darab')
    return out
