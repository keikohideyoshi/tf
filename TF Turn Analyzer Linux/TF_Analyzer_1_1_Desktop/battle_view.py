"""Combat presentation, independent of Qt for regression tests."""
import pandas as pd
METRICS={'Nettó ÉP-változás':'net','Kapott sebzés':'taken','Okozott sebzés':'dealt','Gyógyulás':'healed','Csaták száma':'count'}
LABELS={'turn':'Forduló','battle_no':'Csata','monster':'Szörny','taken':'Kapott sebzés','healed':'Gyógyulás','net':'Nettó ÉP','dealt':'Okozott sebzés','xp':'TP','rounds_est':'Becsült körök','reserve_est':'Becsült tartalék','line':'Sor','evidence':'Statisztika','attack_evidence':'Támadási részlet','calculated_net':'Számított nettó ÉP','net_matches':'Nettó egyezik','last_right':'Utolsó jobb kéz','last_left':'Utolsó bal kéz','max_right':'Max. jobb kéz','max_left':'Max. bal kéz','attack_groups':'Közelharci csoportok','ranged_groups':'Távolsági csoportok','name_source':'Név forrása','encf1_candidates':'Névjelöltek','encf1_count':'Névjelöltek száma'}
def fmt(v):
    if pd.isna(v): return 'Nincs adat'
    return f'{v:,.2f}'.rstrip('0').rstrip('.').replace(',',' ').replace('.',',') if v%1 else f'{int(v):,}'.replace(',',' ')
def aggregate(b):
    g=b.groupby('monster',dropna=False)
    s=g.size().to_frame('count')
    for c in ('net','taken','dealt','healed'):
        s[c]=g[c].sum(min_count=1); s[c+'_avg']=g[c].mean(); s[c+'_known']=g[c].count()
    return s.reset_index()
def ranking(s,metric,average):
    key=METRICS[metric]; col=key+'_avg' if average and key!='count' else key
    return s.assign(value=s[col]).dropna(subset=['value']).sort_values('value',ascending=key=='net')
def display_battles(b):
    return b.drop(columns=['source_hash','source_text'],errors='ignore').rename(columns=LABELS)
