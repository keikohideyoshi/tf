import sys,re,csv,json,zipfile,sqlite3,html
from pathlib import Path
from collections import defaultdict
from bs4 import BeautifulSoup
from PySide6.QtCore import Qt,QUrl
from PySide6.QtWidgets import (QApplication,QMainWindow,QWidget,QVBoxLayout,QHBoxLayout,QPushButton,QLabel,QTabWidget,QTableWidget,QTableWidgetItem,QFileDialog,QMessageBox,QLineEdit,QHeaderView,QTextEdit,QSplitter)
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
  super().__init__();self.setWindowTitle('TF Vagyonanalizátor 1.1');self.resize(1450,900)
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
  self.detail=QTableWidget();self.tabs.addTab(self.detail,'Tárgyak és bankszéf')
  self.changes=QTableWidget();self.tabs.addTab(self.changes,'Fordulók közötti változások')
  self.turntable=QTableWidget();self.tabs.addTab(self.turntable,'Fordulók')
  self.turntable.cellClicked.connect(self.choose_turn)
  self.search=QLineEdit();self.search.setPlaceholderText('Tárgy keresése név vagy azonosító alapján…');self.search.textChanged.connect(self.filter_items);v2=QVBoxLayout();v2.addWidget(self.search);self.detail_tab=QWidget();v2.addWidget(self.detail)
  self.tabs.removeTab(1);self.detail.setParent(self.detail_tab);self.detail_tab.setLayout(v2);self.tabs.insertTab(1,self.detail_tab,'Tárgyak és bankszéf')
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
  widget.setSortingEnabled(False);widget.clear();widget.setColumnCount(len(heads));widget.setHorizontalHeaderLabels(heads);widget.setRowCount(len(rows));widget.setAlternatingRowColors(True)
  for r,row in enumerate(rows):
   for c,val in enumerate(row):
    item=QTableWidgetItem(str(val));item.setFlags(item.flags() & ~Qt.ItemIsEditable)
    if isinstance(val,(int,float)):item.setData(Qt.EditRole,val);item.setTextAlignment(Qt.AlignRight|Qt.AlignVCenter)
    widget.setItem(r,c,item)
  widget.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents);widget.horizontalHeader().setStretchLastSection(True);widget.setSortingEnabled(True)
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
  if not current:return
  t,n,g,items=current;prices=self.prices();detail=[]
  for d in items.values():
   price=prices.get(d['id']);detail.append((d['id'],d['name'],'Saját bankszéf' if d['section']=='bank' else 'Karakter',d['qty'],price[1] if price else 'HIÁNYZIK',d['qty']*price[1] if price else '—'))
  self.make_table(self.detail,['ID','Tárgy','Hely','Darab','Egységérték','Összérték'],detail);self.filter_items(self.search.text())
  prev=next(((pt,pitems) for pt,_,_,pitems in reversed(turns) if pt<t),None);changes=[]
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
 def filter_items(self,query):
  for r in range(self.detail.rowCount()):
   self.detail.setRowHidden(r,query.casefold() not in (' '.join(self.detail.item(r,c).text() for c in (0,1))).casefold())

STYLE='''QLabel#latest{background:#162937;border:1px solid #2a4b55;border-radius:11px;padding:17px;color:#8de7db;font-size:15px;font-weight:600}QMainWindow,QWidget{background:#101722;color:#d9e5ef;font-family:Inter,"Noto Sans",sans-serif;font-size:13px}QLabel#brand{font-size:23px;font-weight:800;color:#65dfd1}QLabel#sub{color:#9aabc1;font-size:12px}QLabel#summary{background:#1b2938;border:1px solid #314458;border-radius:15px;padding:22px;color:#f5f8fa;font-size:18px;font-weight:700}QPushButton{background:#203443;border:1px solid #345063;border-radius:9px;padding:11px 14px;color:#aaf3e7;font-weight:650}QPushButton:hover{background:#2c5860}QTabWidget::pane{border:1px solid #293c4f;border-radius:10px}QTabBar::tab{background:#1a2634;color:#a9bac9;padding:13px 19px;border-radius:7px;margin-right:5px}QTabBar::tab:selected{background:#28525a;color:#b7fff0}QTableWidget{background:#141f2c;alternate-background-color:#1b2a38;gridline-color:#2a3b4c;selection-background-color:#24666c;border:0}QHeaderView::section{background:#243747;color:#b7d8de;padding:11px;border:0}QLineEdit{background:#1d2b39;border:1px solid #365165;border-radius:8px;padding:11px}'''
if __name__=='__main__':
 app=QApplication(sys.argv);app.setStyleSheet(STYLE);w=Window();w.show();sys.exit(app.exec())
