import os, sys, json, shutil, subprocess, signal, uuid
from pathlib import Path
from rounds import scan
from pantheon import PANTHEON
from bookmarks import BookmarkMenu
from PySide6.QtCore import Qt,QTimer,QSize
from PySide6.QtGui import QIcon,QPixmap,QPainter,QColor,QPen
from PySide6.QtWidgets import *
ROOT=Path(__file__).resolve().parent
CONF=ROOT/'config.json'; LOG=ROOT/'logs'; LOG.mkdir(exist_ok=True)
THEMES={'Obsidian':('#0b1018','#182330','#c7a66a'),'Arcane':('#160e23','#302044','#c8a0ec'),'Chaos':('#160d10','#321b20','#ef7770'),'Federation':('#061421','#123047','#68cfe4')}
THEMES.update({name: values[:3] for name,values in PANTHEON.items()})
def save():
    if CONF.exists(): shutil.copy2(CONF,CONF.with_suffix('.json.bak'))
    tmp=CONF.with_suffix('.tmp'); tmp.write_text(json.dumps(cfg,ensure_ascii=False,indent=2)); tmp.replace(CONF)
def path(a): return Path(os.path.expandvars(a.get('script',''))).expanduser().absolute()
def alive(a):
    try:
        p=json.loads((LOG/(a['id']+'.pid')).read_text()); pid=p['pid']
        # Validate the Linux boot ID and session leader start time when available.
        if p['boot']!=Path('/proc/sys/kernel/random/boot_id').read_text(): return False
        for f in Path('/proc').iterdir():
            if not f.name.isdigit(): continue
            try:
                s=(f/'stat').read_text().rsplit(')',1)[1].split()
                if int(s[3])==pid and s[0]!='Z' and int(s[19])>=p['start']: return True
            except (OSError,ValueError,IndexError): pass
    except (OSError,ValueError,KeyError): pass
    return False
class Edit(QDialog):
    def __init__(self,a,parent):
        super().__init__(parent); self.setWindowTitle('Alkalmazás szerkesztése'); self.a=a; f=QFormLayout(self); self.fields={}
        for k,label in [('name','Név'),('description','Leírás'),('category','Kategória'),('script','Bash szkript'),('color','Ikonszín')]:
            e=QLineEdit(a.get(k,'')); self.fields[k]=e
            if k=='script':
                row=QHBoxLayout(); row.addWidget(e); b=QPushButton('Tallózás'); b.clicked.connect(lambda: self.browse()); row.addWidget(b); f.addRow(label,row)
            else: f.addRow(label,e)
        self.enabled=QCheckBox('Engedélyezve'); self.enabled.setChecked(a.get('enabled',True)); f.addRow(self.enabled)
        self.icon=QComboBox(); self.icon.addItems(['download','file','search','chart','user','coins','portal']); self.icon.setCurrentText(a.get('icon','portal')); f.addRow('Ikon',self.icon)
        b=QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Cancel); b.accepted.connect(self.accept); b.rejected.connect(self.reject); f.addRow(b)
    def browse(self):
        p,_=QFileDialog.getOpenFileName(self,'Indítószkript',str(Path.home()),'Shell (*.sh);;Minden fájl (*)');
        if p:self.fields['script'].setText(p)
    def accept(self):
        if not self.fields['name'].text().strip(): return
        if not QColor(self.fields['color'].text()).isValid(): QMessageBox.warning(self,'Hiba','Érvénytelen szín.'); return
        self.a.update({k:v.text().strip() for k,v in self.fields.items()}); self.a.update(enabled=self.enabled.isChecked(),icon=self.icon.currentText()); super().accept()
class Window(QMainWindow):
    def __init__(self):
        super().__init__(); self.setWindowTitle('TF Nexus • Túlélők Földje'); self.resize(*cfg.get('size',[1100,750])); self.setMinimumSize(650,450); self.setWindowIcon(QIcon(str(ROOT/'assets/portal.svg')))
        if cfg.get('position'): self.move(*cfg['position'])
        w=QWidget(); self.setCentralWidget(w); v=QVBoxLayout(w); v.setContentsMargins(24,20,24,20); v.setSpacing(14)
        h=QHBoxLayout(); logo=QLabel(); logo.setPixmap(QIcon(str(ROOT/'assets/portal.svg')).pixmap(58,58)); h.addWidget(logo); titles=QVBoxLayout(); t=QLabel('T F   N E X U S'); t.setObjectName('hero'); titles.addWidget(t); self.subtitle=QLabel('Túlélők Földje alkalmazásközpont'); titles.addWidget(self.subtitle); h.addLayout(titles); h.addStretch(); self.theme=QComboBox(); self.theme.addItems(THEMES); self.theme.setCurrentText(cfg.get('theme','Obsidian')); self.theme.currentTextChanged.connect(self.style); h.addWidget(self.theme); gallery=QPushButton('Témagaléria…'); gallery.clicked.connect(self.gallery); h.addWidget(gallery); self.bg=QCheckBox('Fantasy háttér'); self.bg.setChecked(cfg.get('fantasy',True)); self.bg.toggled.connect(self.style); h.addWidget(self.bg); v.addLayout(h)
        h=QHBoxLayout(); self.filter=QComboBox(); self.filter.currentTextChanged.connect(self.refresh); h.addWidget(self.filter); self.query=QLineEdit(); self.query.setPlaceholderText('Alkalmazás keresése…'); self.query.textChanged.connect(self.refresh); h.addWidget(self.query,1); b=QPushButton('+ Új alkalmazás'); b.clicked.connect(self.add); h.addWidget(b); v.addLayout(h)
        self.list=QListWidget(); self.list.setObjectName("appCards"); self.list.setViewMode(QListView.IconMode); self.list.setResizeMode(QListView.Adjust); self.list.setMovement(QListView.Snap); self.list.setWrapping(True); self.list.setSpacing(8); self.list.setGridSize(QSize(290,164)); self.list.setDragDropMode(QAbstractItemView.InternalMove); self.list.setDefaultDropAction(Qt.MoveAction); self.list.model().rowsMoved.connect(self.reorder); self.list.itemDoubleClicked.connect(lambda i:self.launch(self.get(i))); self.list.setContextMenuPolicy(Qt.CustomContextMenu); self.list.customContextMenuRequested.connect(self.menu); v.addWidget(self.list,1)
        self.build_rounds(v)
        h=QHBoxLayout(); self.status=QLabel('Dupla kattintás: indítás • Jobb kattintás: beállítások'); h.addWidget(self.status,1)
        for name,fn in [('Indítás',self.launch_selected),('Szerkesztés',self.edit_selected),('TF honlap',lambda:self.web('https://www.beholder.hu/')),('Bezárás',self.close)]:
            if name=='TF honlap':
                self.links(h,'WebHyper','hyper'); self.links(h,'TF Map','map'); self.bookmarks=BookmarkMenu(self,cfg,save); h.addWidget(self.bookmarks)
            b=QPushButton(name); b.clicked.connect(fn); h.addWidget(b)
        v.addLayout(h); self.categories(); self.style(); self.timer=QTimer(self); self.timer.timeout.connect(self.update_status); self.timer.start(2500)
    def links(self,h,name,key):
        b=QToolButton(); b.setText(name); b.setPopupMode(QToolButton.InstantPopup); m=QMenu(b)
        for entry in cfg['links'][key]:
            m.addAction(entry['name'],lambda checked=False,url=entry['url']:self.web(url))
        b.setMenu(m); h.addWidget(b)
    def build_rounds(self,v):
        self.round_cache={}; self.round_rows=[]; self.round_signature=None
        panel=QGroupBox('Letöltött fordulók böngészése'); panel.setObjectName('roundPanel'); l=QVBoxLayout(panel)
        h=QHBoxLayout(); self.character=QComboBox(); h.addWidget(QLabel('Karakter:')); h.addWidget(self.character,2)
        self.limit=QComboBox(); self.limit.addItems(['5','10','20','50','Összes']); self.limit.setCurrentText(str(cfg['round_browser'].get('recent_count',5))); h.addWidget(QLabel('Utolsó:')); h.addWidget(self.limit)
        for name,fn in [('Karakterek…',self.edit_characters),('Frissítés',self.refresh_rounds),('Mappa',self.open_folder),('Legutóbbi',self.open_latest)]:
            b=QPushButton(name); b.clicked.connect(fn); h.addWidget(b)
        l.addLayout(h); self.round_table=QTableWidget(0,3); self.round_table.setHorizontalHeaderLabels(['Forduló','Formátum','Fájlnév']); self.round_table.horizontalHeader().setSectionResizeMode(2,QHeaderView.Stretch); self.round_table.setSelectionBehavior(QAbstractItemView.SelectRows); self.round_table.setEditTriggers(QAbstractItemView.NoEditTriggers); self.round_table.verticalHeader().hide(); self.round_table.setMinimumHeight(130); self.round_table.setMaximumHeight(210); self.round_table.cellDoubleClicked.connect(lambda r,c:self.open_round(r)); self.round_table.setContextMenuPolicy(Qt.CustomContextMenu); self.round_table.customContextMenuRequested.connect(self.round_menu); l.addWidget(self.round_table)
        h=QHBoxLayout(); self.round_info=QLabel(); h.addWidget(self.round_info,1); b=QPushButton('Megnyitás'); b.clicked.connect(lambda:self.open_round(self.round_table.currentRow())); h.addWidget(b); l.addLayout(h); v.addWidget(panel)
        self.load_characters(); self.character.currentIndexChanged.connect(self.round_selection); self.limit.currentTextChanged.connect(self.round_selection)
        self.round_timer=QTimer(self); self.round_timer.timeout.connect(self.refresh_rounds); self.round_timer.start(10000); self.refresh_rounds()
    def load_characters(self):
        self.character.blockSignals(True); self.character.clear()
        for c in cfg['characters']:self.character.addItem(c['name'],c['id'])
        i=self.character.findData(cfg['round_browser'].get('character')); self.character.setCurrentIndex(max(0,i)); self.character.blockSignals(False)
    def selected_character(self):
        return next((c for c in cfg['characters'] if c['id']==self.character.currentData()),None)
    def round_selection(self,*_):
        cfg['round_browser'].update(character=self.character.currentData(),recent_count=self.limit.currentText()); save(); self.refresh_rounds()
    def refresh_rounds(self,*_):
        c=self.selected_character(); unknown=0; rows=[]
        if c:
            try:rows,unknown=scan(c['folder'],c.get('recursive',True),self.round_cache)
            except OSError as e:self.round_info.setText(str(e)); return
        limit=self.limit.currentText(); shown=rows if limit=='Összes' else rows[:int(limit)]
        sig=(self.character.currentData(),tuple(shown),unknown,len(rows))
        if sig==self.round_signature:return
        self.round_signature=sig; self.round_rows=shown; self.round_table.setRowCount(len(shown))
        for r,(n,p) in enumerate(shown):
            for col,value in enumerate((str(n),p.suffix[1:].upper(),p.name)):
                item=QTableWidgetItem(value); item.setToolTip(str(p)); self.round_table.setItem(r,col,item)
        self.round_info.setText(f'{len(shown)} / {len(rows)} forduló'+(f' • {unknown} fel nem ismert fájl' if unknown else '') if c else 'Adj hozzá karaktert a Karakterek… gombbal.')
    def round_menu(self,pos):
        item=self.round_table.itemAt(pos)
        if item is None:return
        r=item.row()
        if not 0<=r<len(self.round_rows):return
        p=self.round_rows[r][1].absolute()
        self.round_table.selectRow(r)
        m=QMenu(self)
        m.addAction('Forduló megnyitása',lambda:self.open_local(p))
        m.addAction('Elemzés a TF Analyzerrel',lambda:self.analyze_round(p))
        m.addSeparator()
        m.addAction('Fájl helyének megnyitása',lambda:self.open_local(p.parent))
        m.addAction('Elérési út másolása',lambda:QApplication.clipboard().setText(str(p)))
        m.exec(self.round_table.viewport().mapToGlobal(pos))
    def analyze_round(self,p):
        a=next((a for a in cfg['applications'] if a['id']=='chart'),None)
        if a is None:
            a=next((a for a in cfg['applications'] if a['name'].strip().casefold()=='tf analyzer'),None)
        if a is None:
            QMessageBox.warning(self,'TF Analyzer','A TF Analyzer alkalmazáskártya hiányzik.'); return
        if not a.get('enabled',True):
            QMessageBox.warning(self,'TF Analyzer','Az alkalmazáskártya le van tiltva.'); return
        if not a.get('script') or not path(a).is_file():
            self.edit(a)
        if not a.get('enabled',True) or not a.get('script') or not path(a).is_file():return
        if not p.is_file():
            QMessageBox.warning(self,'TF Analyzer','A fordulófájl nem található.'); return
        self.launch(a,round_file=p)
    def open_round(self,r):
        if 0<=r<len(self.round_rows):self.open_local(self.round_rows[r][1])
    def open_latest(self):self.open_round(0)
    def open_folder(self):
        c=self.selected_character()
        if c:self.open_local(Path(os.path.expandvars(c['folder'])).expanduser())
    def open_local(self,p):
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QDesktopServices
        if not p.exists():QMessageBox.warning(self,'TF Nexus','A fájl vagy mappa nem található.');return
        if not QDesktopServices.openUrl(QUrl.fromLocalFile(str(p.absolute()))):QMessageBox.warning(self,'TF Nexus','Nem sikerült megnyitni.')
    def edit_characters(self):
        d=QDialog(self); d.setWindowTitle('Karakterek kezelése'); d.resize(650,400); l=QVBoxLayout(d); items=[dict(c) for c in cfg['characters']]; lst=QListWidget(); l.addWidget(lst)
        def reload():
            lst.clear()
            for c in items:lst.addItem(c['name']+' — '+c['folder'])
        def edit(add=False):
            i=lst.currentRow()
            if not add and i<0:return
            c=dict(id=uuid.uuid4().hex,name='',folder='',recursive=True) if add else dict(items[i]); e=QDialog(d); e.setWindowTitle('Karakter'); f=QFormLayout(e); name=QLineEdit(c['name']); folder=QLineEdit(c['folder']); f.addRow('Név',name); h=QHBoxLayout(); h.addWidget(folder); b=QPushButton('Tallózás'); h.addWidget(b)
            def browse():
                p=QFileDialog.getExistingDirectory(e,'Fordulókönyvtár',folder.text() or str(Path.home()))
                if p:folder.setText(p)
            b.clicked.connect(browse); f.addRow('Könyvtár',h); rec=QCheckBox('Alkönyvtárak átvizsgálása'); rec.setChecked(c.get('recursive',True)); f.addRow(rec); bb=QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Cancel); bb.accepted.connect(e.accept); bb.rejected.connect(e.reject); f.addRow(bb)
            if e.exec() and name.text().strip() and folder.text().strip():
                c.update(name=name.text().strip(),folder=folder.text().strip(),recursive=rec.isChecked())
                if add:items.append(c)
                else:items[i]=c
                reload()
        def remove():
            i=lst.currentRow()
            if i>=0:items.pop(i);reload()
        h=QHBoxLayout()
        for name,fn in [('Hozzáadás',lambda:edit(True)),('Szerkesztés',lambda:edit()),('Eltávolítás',remove)]:
            b=QPushButton(name); b.clicked.connect(fn); h.addWidget(b)
        l.addLayout(h); bb=QDialogButtonBox(QDialogButtonBox.Save|QDialogButtonBox.Cancel); bb.accepted.connect(d.accept); bb.rejected.connect(d.reject); l.addWidget(bb); reload()
        if d.exec():cfg['characters']=items; self.load_characters(); self.round_selection()
    def web(self,url):
        from PySide6.QtGui import QDesktopServices
        from PySide6.QtCore import QUrl
        QDesktopServices.openUrl(QUrl(url))
    def gallery(self):
        d=QDialog(self); d.setWindowTitle('TF Nexus • Témagaléria'); d.resize(740,520); l=QVBoxLayout(d)
        for heading,names in [('Klasszikus témák',list(THEMES)[:4]),('Pantheon – Ghalla istenei',list(PANTHEON))]:
            l.addWidget(QLabel(heading)); grid=QGridLayout(); l.addLayout(grid)
            for i,name in enumerate(names):
                bg,card,accent=THEMES[name]; b=QPushButton(name); b.setMinimumSize(145,85)
                b.setStyleSheet(f'QPushButton {{background:{card};color:{accent};border:2px solid {accent};border-radius:8px;font-weight:bold;}} QPushButton:hover {{background:{accent};color:{bg};}}')
                b.clicked.connect(lambda checked=False,n=name:(self.theme.setCurrentText(n),d.accept())); grid.addWidget(b,i//4,i%4)
        close=QPushButton('Bezárás'); close.clicked.connect(d.reject); l.addWidget(close); d.exec()
    def style(self,*_):
        cfg.update(theme=self.theme.currentText(),fantasy=self.bg.isChecked()); bg,card,accent=THEMES[cfg['theme']]; image=f'background-image:url("{ROOT}/assets/background.svg");' if cfg['fantasy'] else ''
        if cfg['theme'] in PANTHEON:
            name=cfg['theme']; bg,card,accent,fg,border,r,subtitle=PANTHEON[name]
            self.subtitle.setText('Túlélők Földje alkalmazásközpont')
            image=f'background-image:url("{ROOT}/assets/pantheon/{name}.svg");background-position:center;' if cfg['fantasy'] else ''
            selected='#ffffff' if name=='Raia' else bg
            self.setStyleSheet(f"""QWidget {{background:{bg};color:{fg};font-size:13px;}}
            QLabel#hero {{font-size:30px;font-weight:700;color:{accent};}}
            QPushButton,QToolButton,QComboBox,QLineEdit,QPlainTextEdit {{background:{card};border:1px solid {border};border-radius:{r}px;padding:8px;}}
            QPushButton:hover,QToolButton:hover {{background:{accent};color:{selected};}}
            QListWidget#appCards {{background:{bg};{image} border:1px solid {border};border-radius:{r}px;}}
            QListWidget#appCards::item {{background:{card};border:1px solid {border};border-radius:{r}px;padding:10px;}}
            QListWidget#appCards::item:selected,QTableWidget::item:selected,QMenu::item:selected,QComboBox QAbstractItemView::item:selected {{background:{accent};color:{selected};}}
            QGroupBox {{border:1px solid {border};border-radius:{r}px;margin-top:12px;padding-top:10px;}}
            QGroupBox::title {{subcontrol-origin:margin;left:12px;color:{accent};}}
            QHeaderView::section {{background:{card};color:{fg};padding:5px;border:1px solid {border};}}
            QTableWidget,QComboBox QAbstractItemView,QMenu {{background:{card};color:{fg};gridline-color:{border};selection-background-color:{accent};selection-color:{selected};}}
            QToolTip {{background:{card};color:{fg};border:1px solid {border};}}
            """); save(); self.refresh(); return
        self.subtitle.setText('Túlélők Földje alkalmazásközpont')
        self.setStyleSheet(f'QWidget {{background:{bg};color:#e5e8ef;font-size:13px;}} QLabel#hero {{font-size:30px;font-weight:700;color:{accent};}} QPushButton,QToolButton,QComboBox,QLineEdit {{background:{card};border:1px solid {accent};border-radius:7px;padding:8px;}} QPushButton:hover,QToolButton:hover {{background:{accent};color:{bg};}} QListWidget#appCards {{background:{bg};{image} border:1px solid {card};border-radius:12px;}} QListWidget#appCards::item {{background:{card};border:1px solid {accent};border-radius:12px;padding:10px;}} QListWidget#appCards::item:selected {{background:{accent};color:{bg};}} QGroupBox {{border:1px solid {accent};border-radius:10px;margin-top:12px;padding-top:10px;}} QGroupBox::title {{subcontrol-origin:margin;left:12px;color:{accent};}} QHeaderView::section {{background:{card};color:#e5e8ef;padding:5px;}} QTableWidget {{background:{card};gridline-color:{bg};}} QMenu::item:selected {{background:{accent};color:{bg};}}'); save(); self.refresh()
    def categories(self):
        old=self.filter.currentText(); self.filter.blockSignals(True); self.filter.clear(); self.filter.addItems(['Összes','Kedvencek']+sorted({a['category'] for a in cfg['applications']})); self.filter.setCurrentText(old if old else 'Összes'); self.filter.blockSignals(False); self.refresh()
    def get(self,i): return next(a for a in cfg['applications'] if a['id']==i.data(Qt.UserRole))
    def state(self,a): return 'Fut' if alive(a) else 'Letiltva' if not a.get('enabled',True) else 'Indítható' if a.get('script') and path(a).is_file() else 'Útvonal megadása szükséges'
    def label(self,a): return ('★ ' if a.get('favorite') else '')+a['name']+'\n'+a['description']+'\n'+self.state(a)
    def refresh(self,*_):
        if not hasattr(self,'list'): return
        self.list.clear(); c=self.filter.currentText(); q=self.query.text().casefold(); self.list.setDragEnabled(c=='Összes' and not q); self.list.setAcceptDrops(c=='Összes' and not q)
        for a in cfg['applications']:
            if c not in ('','Összes') and not (c=='Kedvencek' and a.get('favorite')) and c!=a['category']: continue
            if q not in (a['name']+' '+a['description']).casefold(): continue
            i=QListWidgetItem(QIcon(str(ROOT/'assets'/(a.get('icon','portal')+'.svg'))),self.label(a)); i.setData(Qt.UserRole,a['id']); i.setSizeHint(QSize(280,150)); i.setTextAlignment(Qt.AlignCenter); self.list.addItem(i)
        self.list.setIconSize(QSize(52,52))
    def update_status(self):
        for n in range(self.list.count()):
            i=self.list.item(n); s=self.label(self.get(i));
            if i.text()!=s:i.setText(s)
    def reorder(self,*_):
        if self.list.count()==len(cfg['applications']): cfg['applications']=[self.get(self.list.item(i)) for i in range(self.list.count())]; save()
    def add(self):
        a=dict(id=uuid.uuid4().hex,name='',description='',category='Segédprogramok',script='',color='#c7a66a',icon='portal',enabled=True)
        if Edit(a,self).exec(): cfg['applications'].append(a); save(); self.categories()
    def edit_selected(self):
        if self.list.currentItem(): self.edit(self.get(self.list.currentItem()))
    def edit(self,a):
        if Edit(a,self).exec(): save(); self.categories()
    def launch_selected(self):
        if self.list.currentItem(): self.launch(self.get(self.list.currentItem()))
    def launch(self,a,round_file=None):
        running=alive(a)
        if running and round_file is None: QMessageBox.information(self,'TF Nexus','Az alkalmazás már fut.'); return
        if not a.get('enabled',True) or not a.get('script') or not path(a).is_file(): self.edit(a); return
        p=path(a)
        try:
            with (LOG/(a['id']+'.log')).open('ab') as f:
                args=['/bin/bash',str(p)]
                if round_file is not None: args.extend(['--fordulo',str(round_file)])
                proc=subprocess.Popen(args,cwd=p.parent,stdin=subprocess.DEVNULL,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
                if not running:
                    s=Path(f'/proc/{proc.pid}/stat').read_text().rsplit(')',1)[1].split(); (LOG/(a['id']+'.pid')).write_text(json.dumps(dict(pid=proc.pid,start=int(s[19]),boot=Path('/proc/sys/kernel/random/boot_id').read_text())))
            self.status.setText(('Elemzés kérése: '+round_file.name) if round_file is not None else 'Elindítva: '+a['name']); self.update_status()
        except OSError as e: QMessageBox.warning(self,'Indítási hiba',str(e))
    def menu(self,pos):
        i=self.list.itemAt(pos)
        if not i:return
        a=self.get(i); m=QMenu(self); m.addAction('Indítás',lambda:self.launch(a)); m.addAction('Szerkesztés',lambda:self.edit(a)); m.addAction('Kedvenc váltása',lambda:self.favorite(a)); m.addAction('Indítási napló',lambda:self.log(a)); m.addAction('Törlés',lambda:self.remove(a)); m.exec(self.list.mapToGlobal(pos))
    def favorite(self,a): a['favorite']=not a.get('favorite'); save(); self.refresh()
    def log(self,a):
        p=LOG/(a['id']+'.log'); d=QDialog(self); d.setWindowTitle('Indítási napló'); d.resize(750,450); l=QVBoxLayout(d); t=QPlainTextEdit(); t.setReadOnly(True); t.setPlainText(p.read_bytes()[-100000:].decode(errors='replace') if p.exists() else 'Még nincs napló.'); l.addWidget(t); d.exec()
    def remove(self,a):
        if alive(a): QMessageBox.warning(self,'TF Nexus','Futó alkalmazás nem törölhető.'); return
        if QMessageBox.question(self,'Törlés','Eltávolítod a kártyát? A program fájljai megmaradnak.')==QMessageBox.Yes: cfg['applications'].remove(a); save(); self.categories()
    def closeEvent(self,e): cfg.update(size=[self.width(),self.height()],position=[self.x(),self.y()]); save(); e.accept()
if __name__=='__main__':
    import fcntl
    lock=open(ROOT/'.nexus.lock','w')
    try: fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BlockingIOError: sys.exit('A TF Nexus már fut.')
    app=QApplication(sys.argv)
    try: cfg=json.loads(CONF.read_text())
    except (OSError,ValueError) as e: QMessageBox.critical(None,'Konfigurációs hiba',str(e)); sys.exit(1)
    cfg.setdefault("bookmarks",[])
    cfg.setdefault("characters",[])
    cfg.setdefault("round_browser",{"recent_count":5})
    links=cfg.setdefault("links",{})
    links.setdefault("hyper",[{"name":"Hivatalos WebHyper","url":"https://hyper.pbm.hu/webhyper/"},{"name":"Kuka Hyper","url":"https://kukabetyar.hu/webhyper/"}])
    links.setdefault("map",[{"name":"Erynome térkép","url":"https://erynome.hu/map/"},{"name":"Kukabetyár térkép","url":"https://kukabetyar.hu/tf_map/viewer/"}])
    win=Window(); win.show(); sys.exit(app.exec())
