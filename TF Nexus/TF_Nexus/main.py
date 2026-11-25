import os, sys, json, shutil, subprocess, signal, uuid
from pathlib import Path
from PySide6.QtCore import Qt,QTimer,QSize
from PySide6.QtGui import QIcon,QPixmap,QPainter,QColor,QPen
from PySide6.QtWidgets import *
ROOT=Path(__file__).resolve().parent
CONF=ROOT/'config.json'; LOG=ROOT/'logs'; LOG.mkdir(exist_ok=True)
THEMES={'Obsidian':('#0b1018','#182330','#c7a66a'),'Arcane':('#160e23','#302044','#c8a0ec'),'Chaos':('#160d10','#321b20','#ef7770'),'Federation':('#061421','#123047','#68cfe4')}
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
        h=QHBoxLayout(); logo=QLabel(); logo.setPixmap(QIcon(str(ROOT/'assets/portal.svg')).pixmap(58,58)); h.addWidget(logo); titles=QVBoxLayout(); t=QLabel('T F   N E X U S'); t.setObjectName('hero'); titles.addWidget(t); titles.addWidget(QLabel('TÚLÉLŐK FÖLDJE  /  ALKALMAZÁSKÖZPONT')); h.addLayout(titles); h.addStretch(); self.theme=QComboBox(); self.theme.addItems(THEMES); self.theme.setCurrentText(cfg.get('theme','Obsidian')); self.theme.currentTextChanged.connect(self.style); h.addWidget(self.theme); self.bg=QCheckBox('Fantasy háttér'); self.bg.setChecked(cfg.get('fantasy',True)); self.bg.toggled.connect(self.style); h.addWidget(self.bg); v.addLayout(h)
        h=QHBoxLayout(); self.filter=QComboBox(); self.filter.currentTextChanged.connect(self.refresh); h.addWidget(self.filter); self.query=QLineEdit(); self.query.setPlaceholderText('Alkalmazás keresése…'); self.query.textChanged.connect(self.refresh); h.addWidget(self.query,1); b=QPushButton('+ Új alkalmazás'); b.clicked.connect(self.add); h.addWidget(b); v.addLayout(h)
        self.list=QListWidget(); self.list.setViewMode(QListView.IconMode); self.list.setResizeMode(QListView.Adjust); self.list.setMovement(QListView.Snap); self.list.setWrapping(True); self.list.setSpacing(8); self.list.setGridSize(QSize(290,164)); self.list.setDragDropMode(QAbstractItemView.InternalMove); self.list.setDefaultDropAction(Qt.MoveAction); self.list.model().rowsMoved.connect(self.reorder); self.list.itemDoubleClicked.connect(lambda i:self.launch(self.get(i))); self.list.setContextMenuPolicy(Qt.CustomContextMenu); self.list.customContextMenuRequested.connect(self.menu); v.addWidget(self.list,1)
        h=QHBoxLayout(); self.status=QLabel('Dupla kattintás: indítás • Jobb kattintás: beállítások'); h.addWidget(self.status,1)
        for name,fn in [('Indítás',self.launch_selected),('Szerkesztés',self.edit_selected),('WebHyper',lambda: self.web('https://hyper.pbm.hu/')),('TF honlap',lambda:self.web('https://www.beholder.hu/')),('Bezárás',self.close)]:
            b=QPushButton(name); b.clicked.connect(fn); h.addWidget(b)
        v.addLayout(h); self.categories(); self.style(); self.timer=QTimer(self); self.timer.timeout.connect(self.update_status); self.timer.start(2500)
    def web(self,url):
        from PySide6.QtGui import QDesktopServices
        from PySide6.QtCore import QUrl
        QDesktopServices.openUrl(QUrl(url))
    def style(self,*_):
        cfg.update(theme=self.theme.currentText(),fantasy=self.bg.isChecked()); bg,card,accent=THEMES[cfg['theme']]; image=f'background-image:url("{ROOT}/assets/background.svg");' if cfg['fantasy'] else ''
        self.setStyleSheet(f'QWidget {{background:{bg};color:#e5e8ef;font-size:13px;}} QLabel#hero {{font-size:30px;font-weight:700;color:{accent};}} QPushButton,QComboBox,QLineEdit {{background:{card};border:1px solid {accent};border-radius:7px;padding:8px;}} QPushButton:hover {{background:{accent};color:{bg};}} QListWidget {{background:{bg};{image} border:1px solid {card};border-radius:12px;}} QListWidget::item {{background:{card};border:1px solid {accent};border-radius:12px;padding:10px;}} QListWidget::item:selected {{background:{accent};color:{bg};}} QMenu::item:selected {{background:{accent};color:{bg};}}'); save(); self.refresh()
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
    def launch(self,a):
        if alive(a): QMessageBox.information(self,'TF Nexus','Az alkalmazás már fut.'); return
        if self.state(a)!='Indítható': self.edit(a); return
        p=path(a)
        try:
            with (LOG/(a['id']+'.log')).open('ab') as f:
                proc=subprocess.Popen(['/bin/bash',str(p)],cwd=p.parent,stdin=subprocess.DEVNULL,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
                s=Path(f'/proc/{proc.pid}/stat').read_text().rsplit(')',1)[1].split(); (LOG/(a['id']+'.pid')).write_text(json.dumps(dict(pid=proc.pid,start=int(s[19]),boot=Path('/proc/sys/kernel/random/boot_id').read_text())))
            self.status.setText('Elindítva: '+a['name']); self.update_status()
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
    win=Window(); win.show(); sys.exit(app.exec())
