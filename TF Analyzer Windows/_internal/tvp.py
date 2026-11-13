"""TF Analyzer 0.5: TVP események a megőrzött HTML-ből.
A régi szöveges elemző csak HTML nélküli fordulókhoz használatos.
"""
import re
from bs4 import BeautifulSoup, NavigableString, Tag

GAIN_NUM = re.compile(r'\+\s*(\d+)\s*TVP\b|kaptál\s+(\d+)\s*TVP-t|előállítottál\s+(\d+)\s*TVP-t',re.I)
SPEND_NUM = re.compile(r'(\d+)\s*pontot használtál fel,\s*van még\s*(\d+)',re.I)
STASIS = re.compile(r'Termel\s+a\s+sztázisrelikvia\s*\(\s*\+\s*15\s*TVP\s*\)\s*\.', re.I)
SAFFRON = re.compile(r'Összemorzsolod\s+a\s+sáfránykövet\.\s*(\d+)\s*tevékenységpontot\s+kaptál',re.I)
KP = re.compile(r'^\*\s*(\d+)\.\s*KP:\s*(.*)$',re.I)
SAFFRON_POWDER = re.compile(r'használod\s+a\s+211\.\s+tárgyat',re.I)
PSI_MEDITATION = re.compile(r'Elmerülsz\s+egy\s+rövid\s+időre\s+agyad\s+legmélyebb\s+bugyraiban',re.I)
# 0.4.2: kizárólag forrás-besorolási minták; a HTML-ben szereplő összeg marad mérvadó.
MOA = re.compile(r'(?:moa\s+spekt(?:or|ro)szkópnak\s+köszönhetően\s+kapsz\s+10\s*tvp|a\s+moa\s+spektroszkóp\s+mintha\s+lelassítaná\s+az\s+idő\s+folyását)',re.I)
TIME_DISTORTION = re.compile(r'Bemetszést\s+végzel\s+az\s+idő\s+szövetén',re.I)
MIND_CONVERSION = re.compile('|'.join([
    r'Gyurmázni\s+kezded\s+az\s+összespórolt\s+tudati\s+energiát',
    r'Iszonyúan\s+koncentrálsz,?\s+ahogy\s+az\s+energiákat\s+transzformálod',
    r'Azt\s+a\s+tudati\s+energiát,?\s+amelyet\s+már\s+nem\s+tudsz\s+kezelni,?\s+a\s+Bugyor\s+felé\s+továbbítod',
    r'Átalakítod\s+a\s+nyers\s+tudati\s+energiát',
]),re.I)
ZAFORION = re.compile(r'Zaf[oó]rion',re.I)
REVERSAL = re.compile('|'.join([
    r'Az\s+idő\s+néhány\s+momentumig\s+visszafelé\s+halad',
    r'Az\s+idő\s+visszafordul',
    r'A\s+kronoérintést\s+most\s+pozitív\s+hatásként\s+éled\s+át',
    r'A\s+reverziós\s+prizma\s+visszafordítja\s+a\s+kronoöregedést',
    r'A\s+lény\s+érintése\s+felzavarja\s+körülötted\s+az\s+idő\s+szövetét',
    r'Pár\s+pillantással\s+visszább\s+kúsztok\s+az\s+időben',
]),re.I)

def source_from_nearby(context, amount):
    """Legutolsó konkrét szövegminta, legfeljebb 420 karakterrel a TVP előtt.
    Az egymás utáni TVP-események között nem örökítünk át régi forrást.
    """
    near=context[-420:]
    matches=[]
    for label,pattern,expected in (
        ('Sáfránypor (#211)',SAFFRON_POWDER,5),
        ('Pszi meditáció',PSI_MEDITATION,20),
        ('Moa spektroszkóp',MOA,10),
        ('Időtorzítás',TIME_DISTORTION,30),
        ('Tudatpont átváltás',MIND_CONVERSION,None),
        ('Reverziós prizma',REVERSAL,range(1,10)),
        ('Zafórion',ZAFORION,10),
    ):
        if expected is not None and (amount not in expected if isinstance(expected,range) else amount != expected):
            continue
        for m in pattern.finditer(near): matches.append((m.end(),label))
    return max(matches)[1] if matches else None

SPEND_COMMAND_TOKEN = re.compile(r"^[^\W\d_][^\s]*$", re.UNICODE)

def nearest_html_command(span):
    """Az esemény előtti legközelebbi <td width=250> parancssor; nem ugrik át hibás cellán."""
    cell=span.find_previous(lambda tag: isinstance(tag,Tag) and tag.name=="td" and str(tag.get("width","")).strip()=="250")
    if cell is None:
        return "Ismeretlen", "Ismeretlen"
    raw=cell.get_text(" ",strip=True)
    parts=raw.split()
    if not parts or not SPEND_COMMAND_TOKEN.fullmatch(parts[0]):
        return "Ismeretlen", raw or "Ismeretlen"
    return parts[0].upper(),raw

COMMAND = re.compile(r'^(vv|tf|mak|kld|sze|be|lm|h|e|v|p|k|gy|sz|ki|fel|le)\s+\d+',re.I)

def classify(context,kind,amount=None):
    if kind=='Bevétel':
        matched=source_from_nearby(context,amount)
        if matched:return matched
        if 'sáfrányk' in context[-190:].casefold():return 'Sáfránykő'
        return 'Egyéb / ellenőrizendő'
    s=context[-190:].casefold()
    if 'időtorzítás' in s:return 'Időtorzítás'
    if 'időt cserélsz' in s:return 'Időcsere'
    if 'meditál' in s:return 'Meditáció'
    if 'spektroszkóp' in s:return 'Moa spektroszkóp'
    if 'sztázisrelikvia' in s:return 'Sztázisrelikvia'
    return 'Parancs / tevékenység (ellenőrizendő)'

def analyze_html(html):
    """DOM sorrendben dolgozik; egy tvpkap/tvpkolt span pontosan egy esemény.
    A beágyazott vpkap nem TVP. A sáfránykő szöveges kivétel.
    """
    soup=BeautifulSoup(html,'html.parser')
    for t in soup(['script','style','noscript']):t.decompose()
    body=soup.body or soup
    records=[]; recent=[]; kp='Forduló eleje';command='Ismeretlen';previous_balance=None; since_gain=[]; zaforion_used=False; stasis_used=False
    # A p.parancs elején lévő táblázat első cellája az adott parancs.
    active_p=None
    def context():return ' '.join(since_gain)[-550:]
    def add(kind,amount,balance,evidence,method,ctx,spend_command=None):
        nonlocal previous_balance, zaforion_used
        quality='HTML jelölés' if method=='HTML' else 'Szöveges kivétel'
        if kind=='Kiadás' and previous_balance is not None and balance is not None:
            # A köztes TVP-bevételt is beleszámítjuk az egyenlegváltozásba.
            if previous_balance-(-amount)!=balance: quality+='; egyenleg ellenőrizendő'
        category=(spend_command[0] if kind=='Kiadás' and spend_command else ('Sztázisrelikvia' if method=='Sztázisrelikvia' else classify(ctx,kind,amount)))
        event_command=(spend_command[1] if kind=='Kiadás' and spend_command else command)
        if kind=='Kiadás' and category=='Ismeretlen': quality+='; nincs érvényes előző td[width=250] parancs'
        if kind=='Bevétel' and category=='Zafórion':
            if zaforion_used:
                category='Egyéb / ellenőrizendő'
                quality+='; ismételt Zafórion-jelölt'
            else:
                zaforion_used=True
        records.append(dict(line=None,kind=kind,amount=amount,balance=balance,
            category=category,kp=kp,command=event_command,quality=quality,
            evidence=evidence[:500],context=ctx[:550],method=method))
        if kind=='Bevétel': since_gain.clear()
        if balance is not None: previous_balance=balance
        elif kind=='Bevétel' and previous_balance is not None:previous_balance+=amount
    for node in body.descendants:
        if isinstance(node,Tag):
            if node.name=='p' and node is not active_p:
                active_p=node
                tbl=node.find('table',class_='par',recursive=False)
                if tbl:
                    cell=tbl.find('td')
                    if cell:
                        label=cell.get_text(' ',strip=True)
                        if COMMAND.match(label):command=label
            if node.name=='span':
                classes=node.get('class') or []
                if 'tvpkap' in classes:
                    value=GAIN_NUM.search(node.get_text(' ',strip=True))
                    if value:
                        amount=int(next(x for x in value.groups() if x is not None))
                        add('Bevétel',amount,None,node.get_text(' ',strip=True),'HTML',context())
                elif 'tvpkolt' in classes:
                    match=SPEND_NUM.search(node.get_text(' ',strip=True))
                    if match:
                        amount=int(match.group(1));balance=int(match.group(2))
                        add('Kiadás',-amount,balance,node.get_text(' ',strip=True),'HTML',context(),nearest_html_command(node))
        elif isinstance(node,NavigableString):
            # A span tartalmát nem tekintjük új TVP eseménynek.
            if node.find_parent('span',class_=['tvpkap','tvpkolt']):continue
            raw=str(node)
            if not raw.strip():continue
            if not stasis_used:
                m_stasis=STASIS.search(raw)
                if m_stasis:
                    add('Bevétel',15,None,m_stasis.group(0),'Sztázisrelikvia',context())
                    stasis_used=True
            for m in SAFFRON.finditer(raw):
                add('Bevétel',int(m.group(1)),None,m.group(0),'Szöveg',context()+' '+raw[max(0,m.start()-100):m.end()+80])
            clean=' '.join(raw.split())
            if clean:
                recent.append(clean)
                since_gain.append(clean)
                if len(recent)>25:recent=recent[-25:]
                if len(since_gain)>25:since_gain[:]=since_gain[-25:]
                k=KP.match(clean)
                if k:kp=f'{k.group(1)}. KP';command=k.group(2).strip()
    # Ha a szöveg HTML-elemek között szakadt meg, a teljes látható szövegben is ellenőrizzük.
    if not stasis_used:
        match=STASIS.search(body.get_text(' ',strip=True))
        if match:
            add('Bevétel',15,None,match.group(0),'Sztázisrelikvia','')
    return records

def analyze(text):
    """Régi szöveges tartalék feldolgozás, kizárólag hiányzó HTML esetére."""
    lines=[x.strip() for x in text.splitlines() if x.strip()]
    records=[];kp='Forduló eleje';command='Ismeretlen';stasis_used=False
    for i,line in enumerate(lines):
        k=KP.match(line)
        if k:kp=f'{k.group(1)}. KP';command=k.group(2).strip()
        elif COMMAND.match(line):command=line
        if not stasis_used:
            m_stasis=STASIS.search(line)
            if m_stasis:
                records.append(dict(line=i+1,kind='Bevétel',amount=15,balance=None,category='Sztázisrelikvia',kp=kp,command=command,quality='Szöveges kivétel',evidence=m_stasis.group(0),context=line[:500],method='Szöveg'))
                stasis_used=True
        for m in SPEND_NUM.finditer(line):
            records.append(dict(line=i+1,kind='Kiadás',amount=-int(m.group(1)),balance=int(m.group(2)),category='Szöveges (ellenőrizendő)',kp=kp,command=command,quality='HTML hiányzik',evidence=line[:500],context=line[:500],method='Szöveg'))
        for m in GAIN_NUM.finditer(line):
            # A sztázisrelikvia +15 TVP-je már külön szöveges esemény; ne számoljuk kétszer.
            if stasis_used and STASIS.search(line) and any(a <= m.start() < b for a,b in [z.span() for z in STASIS.finditer(line)]):
                continue
            records.append(dict(line=i+1,kind='Bevétel',amount=int(next(x for x in m.groups() if x)),balance=None,category=classify(' '.join(lines[max(0,i-5):i+1]),'Bevétel',int(next(x for x in m.groups() if x))),kp=kp,command=command,quality='HTML hiányzik',evidence=line[:500],context=line[:500],method='Szöveg'))
        for m in SAFFRON.finditer(line):
            records.append(dict(line=i+1,kind='Bevétel',amount=int(m.group(1)),balance=None,category='Sáfránykő',kp=kp,command=command,quality='Szöveges kivétel',evidence=line[:500],context=line[:500],method='Szöveg'))
    return records


def movement_conditionals_html(html):
    """Feltételes események darabszáma kizárólag az M parancs alatt.

    Nem rendelünk hozzájuk külön TVP-t: a költség az M parancsban marad.
    """
    soup=BeautifulSoup(html,'html.parser')
    result={'Feltételes kutatás':0,'Feltételes mászás':0}
    for span in soup.select('span.felt'):
        label=' '.join(span.get_text(' ',strip=True).split()).casefold()
        if re.fullmatch(r'\(\s*feltételes\s+kutatás\s*:\s*\)',label):
            event='Feltételes kutatás'
        elif re.fullmatch(r'\(\s*feltételes\s+mászás\s*:\s*\)',label):
            event='Feltételes mászás'
        else:
            continue
        cmd,_=nearest_html_command(span)
        if cmd=='M':result[event]+=1
    return result


def conditional_healing_html(html):
    """Feltételes gyógyítások száma; TVP-költséget nem rendelünk hozzájuk."""
    soup=BeautifulSoup(html,'html.parser')
    return sum(1 for span in soup.select('span.felt')
               if re.fullmatch(r'\(\s*feltételes\s+gyógyítás\s*:\s*\)',
                               ' '.join(span.get_text(' ',strip=True).split()),re.I))
