import sys,re,csv,json,zipfile,sqlite3,html
from functools import cmp_to_key
from pathlib import Path
from collections import defaultdict
from bs4 import BeautifulSoup
from PySide6.QtCore import Qt,QUrl,QCollator,QLocale
from PySide6.QtWidgets import (QApplication,QMainWindow,QWidget,QVBoxLayout,QHBoxLayout,QPushButton,QLabel,QTabWidget,QTableWidget,QTableWidgetItem,QFileDialog,QMessageBox,QLineEdit,QHeaderView,QTextEdit,QSplitter,QComboBox,QGridLayout)
from PySide6.QtWebEngineWidgets import QWebEngineView

ROOT=Path(__file__).resolve().parent
DB=ROOT/'vagyon.sqlite3'
BUNDLED_PRICES=ROOT/'hyper_arlista.csv'
def load_bundled_prices(c):
 if not BUNDLED_PRICES.exists():return
 with BUNDLED_PRICES.open(encoding='utf-8-sig',newline='') as f:
  for row in csv.DictReader(f,delimiter=';'):
   c.execute('INSERT OR REPLACE INTO prices VALUES(?,?,?,?)',(int(row['id']),row['name'],int(row['price']),'Hyper EA/VE (rögzített)'))
 c.commit()
def conn():
 c=sqlite3.connect(DB);c.execute('CREATE TABLE IF NOT EXISTS prices(id INTEGER PRIMARY KEY,name TEXT,price INTEGER,source TEXT)');c.execute('CREATE TABLE IF NOT EXISTS turns(turn INTEGER PRIMARY KEY,name TEXT,gold INTEGER,items TEXT)');return c

def decode(b):
 for encoding in ('iso-8859-2','utf-8','windows-1250'):
  try:return b.decode(encoding)
  except UnicodeDecodeError:pass
 return b.decode('iso-8859-2',errors='replace')
def parse_html(raw):
 soup=BeautifulSoup(decode(raw),'html.parser'); title=soup.title.get_text(' ',strip=True) if soup.title else ''
 m=re.search(r'(\d+)\.\s*forduló',title,re.I)
 if not m:raise ValueError('Nem található fordulószám a HTML címében')
 turn=int(m.group(1)); name=title.split(str(turn)+'.')[0].strip()
 gold=None
 for td in soup.find_all('td'):
  if td.get_text(' ',strip=True).casefold()=='pénz:':
   next_td=td.find_next_sibling('td')
   if next_td:
    z=re.search(r'([\d\s]+)\s*arany',next_td.get_text(' ',strip=True),re.I)
    if z:gold=int(re.sub(r'\s','',z.group(1)));break
 if gold is None:raise ValueError('Nem található a fordulóvégi Pénz mező')
 items={}; sections={'inventory':'NÁLAD LÉVŐ TÁRGYAK','bank':'TÁRGYAID A BANK SZÉFJÉBEN'}
 for table in soup.find_all('table'):
  head=table.find('tr');header=head.get_text(' ',strip=True).upper() if head else ''
  section=next((k for k,v in sections.items() if header.startswith(v)),None)
  if not section:continue
  table_rows=table.find_all('tr')
  # A bankszéf régi HTML-je hibás: a tárgycellák közvetlenül a table alatt vannak.
  table_rows.append(table)
  for tr in table_rows:
   cells=tr.find_all('td',recursive=False)
   for j in range(0,len(cells)-2,3):
    qty_text=cells[j].get_text(' ',strip=True).replace(' ','')
    a=cells[j+2].find('a')
    if not a or not re.fullmatch(r'\d+',qty_text):continue
    txt=cells[j+2].get_text(' ',strip=True)
    mid=re.search(r'\([#$](\d+)\)',txt)
    if not mid:continue
    ident=int(mid.group(1));item_name=a.get_text(' ',strip=True)
    key=f'{section}:{ident}'
    if key in items:items[key]['qty']+=int(qty_text)
    else:items[key]={'id':ident,'name':item_name,'qty':int(qty_text),'section':section}
 if not items:raise ValueError('Nem található a saját tárgylista / bankszéf')
 return turn,name,gold,items

def import_file(path):
 p=Path(path);res=[]
 if p.suffix.lower()=='.zip':
  with zipfile.ZipFile(p) as z:
   for n in z.namelist():
    if n.lower().endswith(('.htm','.html')):res.append(parse_html(z.read(n)))
 else:res.append(parse_html(p.read_bytes()))
 return res

def parse_price(value):
 # EA/VE: az első szám a 'kérjek' előtt; nem becsülünk hiányzó adatot.
 left=re.split('kérjek',str(value),flags=re.I)[0]
 m=re.search(r'(?<!\d)(\d[\d\s]*)(?!\d)',left)
 return int(re.sub(r'\s','',m.group(1))) if m else None

class Window(QMainWindow):
 def __init__(self):
  super().__init__();self.setWindowTitle('TF Vagyonanalizátor 1.2.2');self.resize(1450,900)
  self.db=conn();load_bundled_prices(self.db);self.selected=None
  outer=QWidget();self.setCentralWidget(outer);layout=QVBoxLayout(outer);layout.setContentsMargins(24,20,24,20);layout.setSpacing(14)
  header=QHBoxLayout();logo=QLabel('◆  TF VAGYONANALIZÁTOR');logo.setObjectName('brand');header.addWidget(logo);header.addStretch()
  for label,fn in [('Fordulók importálása',self.import_turns),('Árlista frissítése',self.import_prices),('Hiányzó árak exportja',self.export_missing),('CSV export',self.export_csv)]:
   b=QPushButton(label);b.clicked.connect(fn);header.addWidget(b)
  layout.addLayout(header)
  self.info=QLabel('A Hyper EA/VE árlista beépítve. Importálj fordulókat a kimutatáshoz.');self.info.setObjectName('sub');layout.addWidget(self.info)
  self.tabs=QTabWidget();layout.addWidget(self.tabs)
  self.overview=QWidget();v=QVBoxLayout(self.overview)
  self.summary=QLabel();self.summary.setObjectName('summary');v.addWidget(self.summary)
  self.latest=QLabel();self.latest.setObjectName('latest');v.addWidget(self.latest)
  self.graph=QWebEngineView();v.addWidget(self.graph,1);self.tabs.addTab(self.overview,'Áttekintés és grafikon')
  self.detail_tab=QWidget();self.tabs.addTab(self.detail_tab,'Tárgyak és bankszéf');self.detail=QTableWidget(self.detail_tab)
  self.changes=QTableWidget();self.tabs.addTab(self.changes,'Fordulók közötti változások')
  self.turntable=QTableWidget();self.tabs.addTab(self.turntable,'Fordulók')
  self.turntable.cellClicked.connect(self.choose_turn)
  self.detail_rows=[]
  self.search=QLineEdit();self.search.setPlaceholderText('Tárgynév vagy azonosító…')
  v2=QVBoxLayout(self.detail_tab)
  panel=QGridLayout();v2.addLayout(panel)
  self.location=QComboBox();self.location.addItems(['Minden hely','Karakternél','Saját bankszéf','Mindkét helyen'])
  self.price_filter=QComboBox();self.price_filter.addItems(['Minden ár','Pozitív érték','Nulla érték','Hiányzó ár'])
  self.delta_filter=QComboBox();self.delta_filter.addItems(['Minden változás','Növekedés','Csökkenés','Változatlan','Nincs előzmény'])
  for col,(label,w) in enumerate([('Keresés',self.search),('Hely',self.location),('Ár',self.price_filter),('Készletváltozás',self.delta_filter)]):
   panel.addWidget(QLabel(label),0,col);panel.addWidget(w,1,col)
  self.bounds=[]
  for col,label in enumerate(['Teljes darabszám','Egységérték','Összérték']):
   lo=QLineEdit();hi=QLineEdit();lo.setPlaceholderText('Minimum');hi.setPlaceholderText('Maximum')
   from PySide6.QtGui import QRegularExpressionValidator
   from PySide6.QtCore import QRegularExpression
   for w in (lo,hi):w.setValidator(QRegularExpressionValidator(QRegularExpression('[0-9]{0,18}'),w))
   pair=QHBoxLayout();pair.addWidget(lo);pair.addWidget(hi);panel.addWidget(QLabel(label),2,col);panel.addLayout(pair,3,col);self.bounds.append((lo,hi))
  actions=QHBoxLayout();apply=QPushButton('Szűrés alkalmazása');apply.clicked.connect(self.filter_items);actions.addWidget(apply);reset=QPushButton('Szűrők törlése');reset.clicked.connect(self.reset_filters);actions.addWidget(reset);v2.addLayout(actions)
  self.filter_summary=QLabel();v2.addWidget(self.filter_summary)
  self.empty_results=QLabel('Nincs a feltételeknek megfelelő tárgy.');self.empty_results.setAlignment(Qt.AlignCenter);v2.addWidget(self.empty_results);v2.addWidget(self.detail,1)
  self.top_tab=QWidget();tv=QVBoxLayout(self.top_tab);controls=QHBoxLayout();tv.addLayout(controls)
  self.top_metric=QComboBox();self.top_metric.addItems(['Összérték','Egységérték','Teljes darabszám'])
  self.top_count=QComboBox();self.top_count.addItems(['10','25','50','100'])
  controls.addWidget(QLabel('Rangsor alapja'));controls.addWidget(self.top_metric);controls.addWidget(QLabel('TOP'));controls.addWidget(self.top_count);controls.addStretch()
  self.top_summary=QLabel();tv.addWidget(self.top_summary);self.top_table=QTableWidget();tv.addWidget(self.top_table);self.tabs.addTab(self.top_tab,'TOP tárgyak')
  footer=QHBoxLayout();footer.addStretch();close_button=QPushButton('Bezárás');close_button.setObjectName('closeButton');close_button.clicked.connect(self.close);footer.addWidget(close_button);layout.addLayout(footer)
  self.search.returnPressed.connect(self.filter_items);self.top_metric.currentIndexChanged.connect(self.refresh_top);self.top_count.currentIndexChanged.connect(self.refresh_top)
  self.refresh()
 def prices(self):return {i:(name,price) for i,name,price in self.db.execute('SELECT id,name,price FROM prices')}
 def turns(self):return [(t,n,g,json.loads(j)) for t,n,g,j in self.db.execute('SELECT turn,name,gold,items FROM turns ORDER BY turn')]
 def import_turns(self):
  paths,_=QFileDialog.getOpenFileNames(self,'Fordulók megnyitása','','Fordulók (*.htm *.html *.zip)');good=0;errors=[]
  for p in paths:
   try:
    for t,n,g,items in import_file(p):self.db.execute('INSERT OR REPLACE INTO turns VALUES(?,?,?,?)',(t,n,g,json.dumps(items,ensure_ascii=False)));good+=1
   except Exception as e:errors.append(f'{Path(p).name}: {e}')
  self.db.commit();self.refresh();QMessageBox.information(self,'Importálás',f'{good} forduló importálva.'+('\n\nHibák:\n'+'\n'.join(errors[:15]) if errors else ''))
 def import_prices(self):
  path,_=QFileDialog.getOpenFileName(self,'EA/VE árlista importálása','','Árlista (*.csv *.tsv *.html *.htm)')
  if not path:return
  count=0;bad=0
  try:
   p=Path(path)
   if p.suffix.lower() in ('.html','.htm'):
    soup=BeautifulSoup(decode(p.read_bytes()),'html.parser');records=[]
    for tr in soup.select('tr'):
     cells=tr.find_all(['td','th'],recursive=False)
     if len(cells)<3:continue
     # A HTML táblázat oszlopai eltérhetnek: csak azonosítható tárgy-ID + EA/VE fejléc esetén olvasunk.
     table=tr.find_parent('table');first=table.find('tr') if table else None
     heads=[c.get_text(' ',strip=True).casefold() for c in first.find_all(['th','td'],recursive=False)] if first else []
     ix=next((i for i,h in enumerate(heads) if 'ea/ve' in h),None)
     if ix is None or ix>=len(cells):continue
     full=tr.get_text(' ',strip=True);m=re.search(r'[#(](\d{1,5})\)?',full)
     if not m:continue
     records.append((m.group(1),cells[1].get_text(' ',strip=True),cells[ix].get_text(' ',strip=True)))
   else:
    with p.open(encoding='utf-8-sig',newline='') as f:
     sample=f.read(4096);f.seek(0);dialect=csv.Sniffer().sniff(sample,delimiters=',;\t');reader=csv.DictReader(f,dialect=dialect)
     if not reader.fieldnames:raise ValueError('Nincs CSV fejléc')
     def field(row,*names):
      for k,v in row.items():
       if k and k.strip().lower() in names:return v
      return ''
     records=[(field(r,'id','azonosító','tárgyszám','ssz'),field(r,'name','név','tárgy'),field(r,'ea/ve','value','érték','arany')) for r in reader]
   for ident,name,raw in records:
    try:
     ident=int(re.sub(r'[^0-9]','',str(ident)));value=parse_price(raw)
     if value is None:bad+=1;continue
     self.db.execute('INSERT OR REPLACE INTO prices VALUES(?,?,?,?)',(ident,name,value,p.name));count+=1
    except (ValueError,TypeError):bad+=1
   self.db.commit();self.refresh();QMessageBox.information(self,'Árlista',f'{count} tárgyár importálva; {bad} kihagyva.')
  except Exception as e:QMessageBox.critical(self,'Hiba',str(e))
 def missing(self):
  prices=self.prices();found={}
  for _,_,_,items in self.turns():
   for d in items.values():
    if d['id'] not in prices:found[d['id']]=d['name']
  return found
 def export_missing(self):
  path,_=QFileDialog.getSaveFileName(self,'Hiányzó árak exportálása','hianyzo_arak.csv','CSV (*.csv)')
  if not path:return
  with open(path,'w',encoding='utf-8-sig',newline='') as f:
   w=csv.writer(f,delimiter=';');w.writerow(['id','name','EA/VE']);w.writerows((i,n,'') for i,n in sorted(self.missing().items()))
  QMessageBox.information(self,'Export',f'{len(self.missing())} hiányzó tárgyár exportálva. Az EA/VE oszlopot kitöltve visszaimportálható.')
 def export_csv(self):
  path,_=QFileDialog.getSaveFileName(self,'Fordulók exportálása','vagyon.csv','CSV (*.csv)')
  if not path:return
  with open(path,'w',encoding='utf-8-sig',newline='') as f:
   w=csv.writer(f,delimiter=';');w.writerow(['Forduló','Karakter','Arany','Tárgyak ismert értéke','Bankszéf ismert értéke','Ismert vagyon minimuma','Ismeretlen árú tételek'])
   for t,n,g,items in self.turns():
    a,b,missing=self.calc(items);w.writerow([t,n,g,a,b,g+a+b,missing])
 def calc(self,items):
  prices=self.prices();a=b=missing=0
  for d in items.values():
   if d['id'] not in prices:missing+=1;continue
   val=d['qty']*prices[d['id']][1]
   if d['section']=='bank':b+=val
   else:a+=val
  return a,b,missing
 def choose_turn(self,row,col):
  cell=self.turntable.item(row,0)
  if cell:self.selected=int(cell.text());self.refresh_detail()
 def make_table(self,widget,heads,rows):
  # A Qt beépített cellaszöveg-rendezése helyett a nyers sorokat rendezzük.
  header=widget.horizontalHeader()
  if not hasattr(widget,'_sort_state'):
   default=(6,Qt.DescendingOrder) if widget is self.detail else (0,Qt.AscendingOrder)
   widget._sort_state=default
   header.setSectionsClickable(True)
   header.sectionClicked.connect(lambda column,w=widget:self.sort_header(w,column))
  widget._raw_rows=list(rows)
  widget._heads=list(heads)
  widget.setSortingEnabled(False)
  self.render_sorted(widget)
 def sort_header(self,widget,column):
  old,direction=widget._sort_state
  direction=Qt.DescendingOrder if old==column and direction==Qt.AscendingOrder else Qt.AscendingOrder
  widget._sort_state=(column,direction)
  self.render_sorted(widget)
 def render_sorted(self,widget):
  column,direction=widget._sort_state
  collator=QCollator(QLocale('hu_HU'));collator.setCaseSensitivity(Qt.CaseInsensitive)
  rows=sort_rows(widget._raw_rows,column,direction==Qt.DescendingOrder,collator.compare)
  widget.setUpdatesEnabled(False)
  try:
   widget.clearContents();widget.setColumnCount(len(widget._heads));widget.setHorizontalHeaderLabels(widget._heads);widget.setRowCount(len(rows));widget.setAlternatingRowColors(True)
   for r,row in enumerate(rows):
    for c,val in enumerate(row):
     item=QTableWidgetItem('—' if val is None else str(val));item.setFlags(item.flags() & ~Qt.ItemIsEditable)
     if isinstance(val,(int,float)):item.setTextAlignment(Qt.AlignRight|Qt.AlignVCenter)
     widget.setItem(r,c,item)
   header=widget.horizontalHeader();header.setSectionResizeMode(QHeaderView.ResizeToContents);header.setStretchLastSection(True);header.setSortIndicator(column,direction);header.setSortIndicatorShown(True)
  finally:widget.setUpdatesEnabled(True)
 def refresh(self):
  turns=self.turns();prices=self.prices();missing=self.missing();rows=[];chart=[]
  for t,n,g,items in turns:
   a,b,m=self.calc(items);total=g+a+b;rows.append((t,n,g,a,b,total,m));chart.append({'turn':t,'gold':g,'items':a,'bank':b,'total':total,'missing':m})
  self.make_table(self.turntable,['Forduló','Karakter','Arany','Tárgyak ismert értéke','Bankszéf ismert értéke','Összesített vagyon / minimum','Hiányzó árú típusok'],rows)
  if turns:
   last=turns[-1];self.selected=self.selected if any(t==self.selected for t,_,_,_ in turns) else last[0]
   a,b,m=self.calc(last[3]);total=last[2]+a+b
   self.summary.setText(f'  LEGUTOLSÓ FORDULÓ: {last[0]}  •  {last[1]}\n  {total:,} arany'+('  (ISMERT MINIMUM)' if m else '  (TELJES VAGYON)'))
   self.latest.setText(f'  Arany: {last[2]:,}   •   Tárgyak: {a:,}   •   Saját bankszéf: {b:,}   •   Hiányzó árú típusok: {m}'.replace(',',' '))
   self.info.setText(f'{len(turns)} forduló  •  {len(prices)} rögzített Hyper tárgyár  •  {len(missing)} hiányzó tárgyár  •  A felső kártya mindig a legutolsó fordulót mutatja; a táblázatban régebbi forduló is kijelölhető.')
  else:self.summary.setText('   Nincs importált forduló');self.latest.setText('');self.info.setText('A rögzített Hyper árlista rendelkezésre áll. Importálj HTML-fordulókat.')
  import plotly.graph_objects as go
  fig=go.Figure()
  for key,label,color in [('gold','Arany','#e7b86b'),('items','Nálad lévő tárgyak','#56d6c8'),('bank','Saját bankszéf','#7196f0')]:fig.add_trace(go.Scatter(x=[x['turn'] for x in chart],y=[x[key] for x in chart],name=label,mode='lines+markers',stackgroup='one',line=dict(color=color,width=2)))
  fig.update_layout(template='plotly_dark',paper_bgcolor='#131b28',plot_bgcolor='#131b28',font_color='#c6d3e2',margin=dict(l=65,r=25,t=25,b=45),hovermode='x unified',legend=dict(orientation='h',y=1.12),xaxis_title='Forduló',yaxis_title='Ismert vagyon (arany)')
  graph_path=ROOT/'vagyon_grafikon.html';fig.write_html(str(graph_path),include_plotlyjs=True);self.graph.setUrl(QUrl.fromLocalFile(str(graph_path)))
  self.refresh_detail()
 def refresh_detail(self):
  turns=self.turns();current=next(((t,n,g,i) for t,n,g,i in turns if t==self.selected),None)
  if not current:
   self.detail_rows=[];self.filter_items();self.refresh_top();return
  t,n,g,items=current;prices=self.prices()
  prev=next(((pt,pitems) for pt,_,_,pitems in reversed(turns) if pt<t),None);changes=[]
  self.detail_rows=aggregate_items(items,prev[1] if prev else None,prices,g)
  self.filter_items();self.refresh_top()
  if prev:
   old=defaultdict(int);new=defaultdict(int);names={}
   for d in prev[1].values():old[d['id']]+=d['qty'];names[d['id']]=d['name']
   for d in items.values():new[d['id']]+=d['qty'];names[d['id']]=d['name']
   for ident in sorted(set(old)|set(new)):
    delta=new[ident]-old[ident]
    if not delta:continue
    price=prices.get(ident);changes.append((ident,names[ident],old[ident],new[ident],delta,price[1] if price else 'HIÁNYZIK',delta*price[1] if price else '—'))
  self.make_table(self.changes,['ID','Tárgy','Előző db','Aktuális db','Nettó db változás','Egységérték','Nettó értékváltozás'],changes)
  self.tabs.setTabText(1,f'Tárgyak és bankszéf ({t})');self.tabs.setTabText(2,f'Nettó tárgyváltozások ({t})')
 def reset_filters(self):
  self.search.clear()
  for w in (self.location,self.price_filter,self.delta_filter):w.setCurrentIndex(0)
  for lo,hi in self.bounds:lo.clear();hi.clear()
  self.filter_items()
 def filter_items(self,*args):
  query=self.search.text().casefold().strip();loc=self.location.currentIndex();pf=self.price_filter.currentIndex();df=self.delta_filter.currentIndex()
  ranges=[(int(lo.text()) if lo.text() else None,int(hi.text()) if hi.text() else None) for lo,hi in self.bounds]
  if any(lo is not None and hi is not None and lo>hi for lo,hi in ranges):
   QMessageBox.warning(self,'Érvénytelen szűrő','A minimum nem lehet nagyobb a maximumnál.');return
  rows=select_items(self.detail_rows,query,loc,pf,df,ranges)
  self.empty_results.setVisible(not rows);self.empty_results.setText('Nincs a feltételeknek megfelelő tárgy.' if self.detail_rows else 'Nincs importált tárgylista.')
  self.make_table(self.detail,DETAIL_HEADS,[display_row(r) for r in rows])
  self.filter_summary.setText(f'{len(rows)} / {len(self.detail_rows)} tárgytípus  •  Szűrt ismert érték: {sum(r[6] or 0 for r in rows):,} arany  •  Hiányzó ár: {sum(r[5] is None for r in rows)}'.replace(',',' '))
 def refresh_top(self,*args):
  ix=(6,5,4)[self.top_metric.currentIndex()];limit=int(self.top_count.currentText());rows=sorted((r for r in self.detail_rows if r[ix] is not None),key=lambda r:(-r[ix],r[0]))[:limit]
  self.make_table(self.top_table,['Helyezés']+DETAIL_HEADS,[(i,*display_row(r)) for i,r in enumerate(rows,1)])
  self.top_summary.setText(f'{self.selected or "—"}. forduló  •  TOP {limit} – {self.top_metric.currentText()}  •  Ismert összérték: {sum(r[6] or 0 for r in rows):,} arany  •  A TOP a teljes tárgylistából készül.'.replace(',',' '))

def select_items(source,query,loc,pf,df,ranges):
  rows=[]
  for r in source:
   ident,name,inv,bank,qty,price,value,share,delta,dvalue=r
   if query and query not in f'{ident} {name}'.casefold():continue
   if loc==1 and not inv or loc==2 and not bank or loc==3 and not(inv and bank):continue
   if pf==1 and not(price is not None and price>0) or pf==2 and price!=0 or pf==3 and price is not None:continue
   if df==1 and not(delta is not None and delta>0) or df==2 and not(delta is not None and delta<0) or df==3 and delta!=0 or df==4 and delta is not None:continue
   if any((lo is not None and (v is None or v<lo)) or (hi is not None and (v is None or v>hi)) for v,(lo,hi) in zip((qty,price,value),ranges)):continue
   rows.append(r)
  return rows

DETAIL_HEADS=['ID','Tárgy','Karakternél (db)','Bankszéf (db)','Teljes készlet','Egységérték','Összérték','Vagyonarány (%)','Nettó db változás','Nettó értékváltozás']
def aggregate_items(items,previous,prices,gold):
 grouped={};old=defaultdict(int)
 for d in (previous or {}).values():old[d['id']]+=d['qty']
 for d in items.values():
  r=grouped.setdefault(d['id'],[d['name'],0,0]);r[2 if d['section']=='bank' else 1]+=d['qty']
 total=gold+sum((r[1]+r[2])*prices[i][1] for i,r in grouped.items() if i in prices)
 incomplete=any(i not in prices for i in grouped)
 rows=[]
 for i,(name,inv,bank) in grouped.items():
  qty=inv+bank;price=prices[i][1] if i in prices else None;value=qty*price if price is not None else None;delta=qty-old[i] if previous is not None else None
  rows.append((i,name,inv,bank,qty,price,value,round(100*value/total,3) if value is not None and total and not incomplete else None,delta,delta*price if delta is not None and price is not None else None))
 return rows
def display_row(r):return r

def sort_rows(rows,column,descending,compare_text):
 def missing(v):return v is None or v in ('—','HIÁNYZIK')
 known=[r for r in rows if not missing(r[column])]
 unknown=[r for r in rows if missing(r[column])]
 def compare(a,b):
  x,y=a[column],b[column]
  if isinstance(x,(int,float)) and isinstance(y,(int,float)):
   return (x>y)-(x<y)
  return compare_text(str(x),str(y))
 return sorted(known,key=cmp_to_key(compare),reverse=descending)+unknown

STYLE='''QPushButton#closeButton{background:#702e39;border:1px solid #a54a55;color:#ffe3e5}QPushButton#closeButton:hover{background:#963d4b}QComboBox{background:#1d2b39;border:1px solid #365165;border-radius:8px;padding:9px;color:#d9e5ef}QComboBox QAbstractItemView{background:#1d2b39;selection-background-color:#28525a;color:#d9e5ef}QLabel#latest{background:#162937;border:1px solid #2a4b55;border-radius:11px;padding:17px;color:#8de7db;font-size:15px;font-weight:600}QMainWindow,QWidget{background:#101722;color:#d9e5ef;font-family:Inter,"Noto Sans",sans-serif;font-size:13px}QLabel#brand{font-size:23px;font-weight:800;color:#65dfd1}QLabel#sub{color:#9aabc1;font-size:12px}QLabel#summary{background:#1b2938;border:1px solid #314458;border-radius:15px;padding:22px;color:#f5f8fa;font-size:18px;font-weight:700}QPushButton{background:#203443;border:1px solid #345063;border-radius:9px;padding:11px 14px;color:#aaf3e7;font-weight:650}QPushButton:hover{background:#2c5860}QTabWidget::pane{border:1px solid #293c4f;border-radius:10px}QTabBar::tab{background:#1a2634;color:#a9bac9;padding:13px 19px;border-radius:7px;margin-right:5px}QTabBar::tab:selected{background:#28525a;color:#b7fff0}QTableWidget{background:#141f2c;alternate-background-color:#1b2a38;gridline-color:#2a3b4c;selection-background-color:#24666c;border:0}QHeaderView::section{background:#243747;color:#b7d8de;padding:11px;border:0}QLineEdit{background:#1d2b39;border:1px solid #365165;border-radius:8px;padding:11px}'''
if __name__=='__main__':
 app=QApplication(sys.argv);app.setStyleSheet(STYLE);w=Window();w.show();sys.exit(app.exec())
