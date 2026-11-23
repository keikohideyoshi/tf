"""TF 1.9.7.9: independent, conservative alchemy event recognizer.

Chest acquisitions remain acquisitions; alchemy is an additional event.
"""
import re
from pathlib import Path
from bs4 import BeautifulSoup
from core import fold_hu, read_html
from object_search import _name_pattern
from search_diagnostics import Stage

CHEST = re.compile(r'\[\s*(?P<item>[^\[\]\r\n]{1,150}?)\s+ládikóba\s*->', re.I)
ACQUIRE = re.compile(r'Szerzeményed\s*:\s*(?P<quantity>\d[\d\s]*)\s+(?P<item>[^\[\]\r\n]{1,150}?)\s*\[', re.I)
H_COMMAND = re.compile(r'^\s*h\s+341\s+(?P<item>\d+)\s+(?P<quantity>\d+)(?!\d)', re.I)

def chest_events(text, name):
    """Only the bracketed 'item ládikóba->' form; optional acquisition quantity."""
    wanted=fold_hu(name).strip()
    hits=[]
    for m in CHEST.finditer(text):
        if fold_hu(m.group('item')).strip()!=wanted:continue
        before=text[max(0,m.start()-230):m.start()]
        acquisitions=list(ACQUIRE.finditer(before+'['))
        qty=None
        if acquisitions:
            a=acquisitions[-1]
            if a.end()==len(before)+1 and fold_hu(a.group('item')).strip()==wanted:
                qty=int(''.join(a.group('quantity').split()))
        hits.append((m.start(),qty))
    return hits

def h_commands(html):
    """Only actual command tables, never narrative text containing 'h 341'."""
    soup=BeautifulSoup(html,'lxml')
    for table in soup.select('table.par'):
        cells=table.select('td')
        if not cells:continue
        header=cells[0].get_text(' ',strip=True)
        m=H_COMMAND.match(header)
        if m:yield int(m.group('item')),int(m.group('quantity')),header

def search_alchemy(c, entity_id, character_id=None, sample_limit=3):
    item=c.execute("SELECT name FROM entities WHERE kind='item' AND entity_id=?",(entity_id,)).fetchone()
    if item is None:raise ValueError('A tárgy nem található az enciklopédiában.')
    name=item['name'];groups={}
    def add(r,method,quantity,snippet,seq=0):
        tid=r['id']
        if tid not in groups:
            groups[tid]={'turn_id':tid,'character_id':r['character_id'],'character':r['character'],
                'turn_number':r['turn_number'],'source_path':r['source_path'],'count':0,
                'snippets':[],'match_types':'Alkímiázás','name_count':0,'id_count':0,
                'quantity_total':0,'quantity_known':True}
        g=groups[tid];g['count']+=1
        if quantity is None:g['quantity_known']=False
        else:g['quantity_total']+=quantity
        if len(g['snippets'])<sample_limit:
            g['snippets'].append({'text':f'{method}: {snippet[:520]}'+(f' [mennyiség: {quantity} db]' if quantity is not None else ''),'seq':seq,'type':method})
    sql=('SELECT t.id,t.character_id,t.character,t.turn_number,t.source_path,b.seq,b.content '
         'FROM blocks b JOIN turns t ON t.id=b.turn_id WHERE b.content LIKE ?')
    args=['%ládikóba%']
    if character_id is not None:sql+=' AND t.character_id=?';args.append(character_id)
    with Stage('alchemy_chest_lookup'):
        for r in c.execute(sql,args):
            for pos,qty in chest_events(r['content'],name):
                add(r,'Aranytermő ládikó',qty,r['content'][max(0,pos-105):pos+140],r['seq'])
    # The H command is verified against the original HTML table.par structure.
    # A cheap block prefilter avoids reading unrelated HTML files.
    sql=('SELECT DISTINCT t.id,t.character_id,t.character,t.turn_number,t.source_path '
         'FROM blocks b JOIN turns t ON t.id=b.turn_id '
         "WHERE (lower(b.content) LIKE '%h 341%' OR lower(b.content) LIKE '%h\t341%')")
    args=[]
    if character_id is not None:sql+=' AND t.character_id=?';args.append(character_id)
    with Stage('alchemy_cauldron_lookup'):
        for r in c.execute(sql,args):
            if not Path(r['source_path']).is_file():continue
            for eid,qty,header in h_commands(read_html(r['source_path'])):
                if eid==entity_id:add(r,'Alkímiázó üst',qty,header)
    return sorted(groups.values(),key=lambda r:(r['character'].casefold(),-r['turn_number']))
