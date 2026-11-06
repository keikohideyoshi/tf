"""Conservative combat extraction from the original TF turn text.
Only explicitly reported battle totals are authoritative. Attack/round estimates
are marked as estimates, never as verified game facts.
"""
import re
from collections import Counter

NUM=r'[-+]?\d[\d \u00a0]*'
STATS=re.compile(r'\{Csatastatisztika;\s*sebzés:\s*('+NUM+r')\s*,\s*sebződés:\s*('+NUM+r')\s*,\s*gyógyulás:\s*('+NUM+r')\s*,\s*összesen:\s*('+NUM+r')\s*ÉP(?:\s*,\s*összes\s+sebzés:\s*'+NUM+r'\s*,\s*összes\s+sebződés:\s*'+NUM+r')?\s*\}',re.I)
MONSTER=re.compile(r'\{támadása:\s*\d+\.?\}',re.I)
ATTACK=re.compile(r'\((\d+)\s+támadással\s+([\d ]+)\s+életpontot sebezve\.\)',re.I)
XP=re.compile(r'([\d ]+)\s+tapasztalati pontot kaptál\.',re.I)

def n(s): return int(re.sub(r'\s','',s))

def analyze_combat(text, turn=None):
    lines=[x.strip() for x in text.splitlines() if x.strip()]
    # TF formats the stats across several HTML text nodes, hence joining lines.
    markers=[i for i,l in enumerate(lines) if 'Csatastatisztika' in l]
    starts=[i for i,l in enumerate(lines) if MONSTER.search(l)]
    name_hint=re.compile(r'^\{(?:szintje|max\. életpontja|támadása| mentális varázslat)',re.I)
    def monster_name(begin,end):
        # A szörny neve többnyire külön HTML-szövegcsomópont; az előtte
        # álló mondatban „egy”, „csak egy”, „az utolsó szörny” szerepel.
        # A korábbi változat a következő csomópontot vizsgálta, és emiatt
        # gyakran nem a nevet, hanem a leíró mondatot adta vissza.
        segment=lines[begin:end]
        first_hit=next((j for j,v in enumerate(segment) if ATTACK.search(v)),len(segment))
        stop=min(len(segment),first_hit+1)
        candidates=[]
        for j in range(1,stop):
            candidate=segment[j].strip(' .,:;!')
            if not 2<=len(candidate)<=55 or not re.fullmatch(r"[\wÁÉÍÓÖŐÚÜŰáéíóöőúüű' -]+",candidate):
                continue
            prev=segment[j-1].strip().lower()
            nxt=segment[j+1].strip().lower() if j+1<len(segment) else ''
            # A név a bevezető mondat végén álló névelő után következik.
            intro=bool(re.search(r"(?:\b(?:egy|az|a|csak egy|szörny|ellenfél)\s*)$",prev))
            # Alternatíva: a név közvetlenül a szörny tulajdonságai előtt.
            stat=bool(re.match(r"^\{(?:támadása|szintje|mágikus sebezhetőség|fizikai sebezhetőség|védettsége|egyik sebzési módja)",nxt))
            if not (intro or stat):
                continue
            if candidate.lower() in {'ellenfeled','szörny','lény','teremtmény','társa','kincset','fegyver','csata','harc','támadás','nem jelenthet komoly veszélyt','jön feléd','lehet','közeledik'}:
                continue
            # Bevezetés és statisztikai blokk közelsége erős bizonyíték.
            score=(4 if intro else 0)+(2 if stat else 0)
            candidates.append((score,j,candidate))
        if not candidates:return 'Ismeretlen'
        # Az első ütéshez legközelebb eső, megfelelő bevezetésű név.
        candidates.sort(key=lambda x:(x[0],x[1]),reverse=True)
        return candidates[0][2]
    out=[]
    for k,idx in enumerate(markers):
        end=min(len(lines),idx+18)
        block=' '.join(lines[idx:end])
        stat=STATS.search(block)
        if not stat: continue
        previous=markers[k-1] if k else -1
        candidates=[i for i in starts if previous<i<idx]
        start=candidates[-1] if candidates else None
        # Do not assign a monster based on distant unrelated narrative.
        name=monster_name(previous+1,idx)
        region=lines[max(previous+1,idx-500):idx]
        xp=[n(m.group(1)) for line in region for m in XP.finditer(line)]
        attacks=[]
        for j,line in enumerate(region):
            match=ATTACK.search(line)
            if not match: continue
            # The game reports ranged attack counts in the same pattern.
            # Classify them conservatively from the immediately preceding narration.
            context=' '.join(region[max(0,j-2):j]).lower()
            ranged=any(t in context for t in ['dobónyil','lövedék','lőfegyver','távfegyver','nyilat küldesz','nyílvessző'])
            attacks.append({'hits':int(match.group(1)),'damage':n(match.group(2)), 'ranged':ranged,'evidence':line})
        melee=[a for a in attacks if not a['ranged']]
        # A right/left sequence is assumed only when an even number of melee
        # groups (at most 10) was detected; otherwise rounds remain unknown.
        rounds=None; last_right=None;last_left=None;max_right=None;max_left=None;reserve=None
        if 2<=len(melee)<=10 and len(melee)%2==0:
            rounds=len(melee)//2
            pairs=list(zip(melee[::2],melee[1::2]))
            max_right=max(x['hits'] for x,y in pairs)
            max_left=max(y['hits'] for x,y in pairs)
            last_right=pairs[-1][0]['hits'];last_left=pairs[-1][1]['hits']
            reserve=max(0,max_right-last_right)+max(0,max_left-last_left)
        dealt,taken,healed,net=map(n,stat.groups())
        out.append({'turn':turn,'monster':name,'dealt':dealt,'taken':taken,'healed':healed,
            'net':net,'calculated_net':healed-taken,'net_matches':net==healed-taken,
            'xp':xp[-1] if xp else None,'rounds_est':rounds,
            'last_right':last_right,'last_left':last_left,'max_right':max_right,
            'max_left':max_left,'reserve_est':reserve,'attack_groups':len(melee),
            'ranged_groups':len(attacks)-len(melee),'line':idx+1,
            'evidence':' '.join(lines[idx:min(len(lines),idx+10)])[:450],
            'attack_evidence':' | '.join(a['evidence'] for a in melee[-4:])[:600]})
    return out


def analyze_combat_html(html, text, turn=None):
    """Use source HTML a.encf1 anchors, ordered against the battle summary spans.

    A battle is delimited by consecutive Csatastatisztika spans. The FIRST
    encf1 anchor after the preceding summary is treated as the encounter's
    monster; additional anchors in that same interval are retained as audit
    data, rather than silently guessed. Existing text parser still extracts
    damage, healing, and provisional attack statistics.
    """
    from bs4 import BeautifulSoup
    soup=BeautifulSoup(html,'html.parser')
    names=[]; groups=[]
    for tag in soup.find_all(['a','span']):
        classes=tag.get('class',[])
        if tag.name=='a' and 'encf1' in classes:
            name=tag.get_text(' ',strip=True)
            if name: names.append(name)
        elif tag.name=='span' and 'stat' in classes and 'Csatastatisztika' in tag.get_text(' ',strip=True):
            groups.append(names)
            names=[]
    battles=analyze_combat(text,turn)
    # Never attach wrong names if a document layout differs unexpectedly.
    if len(groups)!=len(battles):
        for battle in battles:
            battle['monster']='Ismeretlen (HTML-szinkronhiba)'
            battle['name_source']='html_sync_error'
            battle['html_stats_count']=len(groups)
            battle['text_stats_count']=len(battles)
        return battles
    for battle, candidates in zip(battles,groups):
        chosen=candidates[0] if candidates else 'Ismeretlen'
        # TF sometimes marks the same creature again in an inflected form
        # (e.g. 'óriás hópárducot' then 'óriás hópárduc'). Prefer the
        # uninflected form only when another anchor clearly shares its stem.
        if len(candidates)>1:
            for candidate in candidates[1:]:
                if chosen.casefold().startswith(candidate.casefold()) and len(chosen)>len(candidate):
                    chosen=candidate
                    break
        battle['monster']=chosen
        battle['name_source']='encf1' if candidates else 'missing_encf1'
        battle['encf1_candidates']=' | '.join(candidates)
        battle['encf1_count']=len(candidates)
    return battles
