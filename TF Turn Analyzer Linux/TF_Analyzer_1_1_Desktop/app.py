import argparse, hashlib, sys, os
from pathlib import Path
import pandas as pd
from PySide6.QtCore import Qt, QSettings, QThread, Signal, QAbstractTableModel, QModelIndex, QSortFilterProxyModel, QTimer, QLockFile
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtWidgets import *
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
import parser as store
from battle_view import METRICS, LABELS, fmt, aggregate, ranking, display_battles
from numbers import Real
from matplotlib.ticker import FuncFormatter
from engine import report
from pantheon import PANTHEON
ROOT=Path(__file__).resolve().parent
EXT={'.html','.htm','.mhtml','.mht'}
THEMES={'Obsidian':('#0b1018','#182330','#c7a66a','#e4eaf0','#354455',8,''),**PANTHEON}
class Model(QAbstractTableModel):
    def __init__(self,df): super().__init__(); self.df=df
    def rowCount(self,p=QModelIndex()): return len(self.df)
    def columnCount(self,p=QModelIndex()): return len(self.df.columns)
    def data(self,i,role=Qt.ItemDataRole.DisplayRole):
        if not i.isValid(): return None
        v=self.df.iat[i.row(),i.column()]
        if role==Qt.ItemDataRole.DisplayRole: return '' if pd.isna(v) else fmt(v) if isinstance(v,Real) and not isinstance(v,bool) else str(v)
        if role==Qt.ItemDataRole.UserRole: return float(v) if isinstance(v,Real) and not pd.isna(v) else str(v)
    def headerData(self,s,o,role=Qt.ItemDataRole.DisplayRole):
        if role==Qt.ItemDataRole.DisplayRole: return str(self.df.columns[s]) if o==Qt.Orientation.Horizontal else str(s+1)
class Worker(QThread):
    status=Signal(str); result=Signal(object); failed=Signal(str)
    def __init__(self,fn): super().__init__(); self.fn=fn
    def run(self):
        try: self.result.emit(self.fn(self.status.emit))
        except Exception as e: self.failed.emit(str(e))
class Window(QMainWindow):
    def __init__(self):
        super().__init__(); self.settings=QSettings('TF','AnalyzerDesktop'); self.turns=[]; self.selected=[]; self.data={}; self.worker=None; self.pending=[]; self.setWindowTitle('TF Analyzer 1.1 • Desktop Edition'); self.resize(1250,820)
        if self.settings.value('geometry'): self.restoreGeometry(self.settings.value('geometry'))
        root=QWidget(); self.setCentralWidget(root); outer=QHBoxLayout(root); outer.setContentsMargins(16,16,16,16)
        side=QVBoxLayout(); outer.addLayout(side); title=QLabel('T F   A N A L Y Z E R'); title.setObjectName('hero'); side.addWidget(title); side.addWidget(QLabel('1.1  /  DESKTOP EDITION'))
        self.nav=QListWidget(); self.nav.setFixedWidth(215); self.nav.addItems(['Áttekintés','Importálás','TVP','Harcok','Parancsok','Hibajelzések','Keresés','Adatminőség','Beállítások']); side.addWidget(self.nav,1)
        close=QPushButton('Bezárás'); close.clicked.connect(self.close); side.addWidget(close)
        main=QVBoxLayout(); outer.addLayout(main,1); bar=QHBoxLayout(); main.addLayout(bar); self.character=QComboBox(); self.character.setMinimumWidth(150); bar.addWidget(QLabel('Karakter')); bar.addWidget(self.character); self.lo=QSpinBox(); self.hi=QSpinBox();
        for w in (self.lo,self.hi): w.setRange(0,999999); bar.addWidget(w)
        apply=QPushButton('Elemzés'); apply.clicked.connect(self.refresh); bar.addWidget(apply); bar.addStretch(); self.theme=QComboBox(); self.theme.addItems(THEMES); self.theme.setCurrentText(self.settings.value('theme','Obsidian')); bar.addWidget(self.theme); self.theme.currentTextChanged.connect(self.style)
        self.stack=QStackedWidget(); main.addWidget(self.stack,1); self.pages=[]
        for _ in range(9):
            scroll=QScrollArea(); scroll.setWidgetResizable(True); page=QWidget(); layout=QVBoxLayout(page); layout.setAlignment(Qt.AlignmentFlag.AlignTop); scroll.setWidget(page); self.stack.addWidget(scroll); self.pages.append(layout)
        self.nav.currentRowChanged.connect(self.stack.setCurrentIndex); self.nav.setCurrentRow(0); self.character.currentIndexChanged.connect(self.range_changed)
        self.status=QLabel('Készen áll'); main.addWidget(self.status); self.progress=QProgressBar(); self.progress.setRange(0,0); self.progress.hide(); main.addWidget(self.progress); self.style(); self.render(); self.run_job(lambda p:store.load_all(),self.loaded)
    def style(self):
        bg,card,accent,fg,border,radius,_=THEMES[self.theme.currentText()]; self.settings.setValue('theme',self.theme.currentText()); self.setStyleSheet(f'QWidget{{background:{bg};color:{fg};font-size:13px}} QLabel#hero{{font-size:20px;font-weight:bold;color:{accent}}} QLabel#heading{{font-size:19px;font-weight:bold;color:{accent}}} QPushButton,QComboBox,QSpinBox,QLineEdit{{background:{card};border:1px solid {border};border-radius:{radius}px;padding:8px}} QPushButton:hover{{border-color:{accent}}} QListWidget,QTableView{{background:{card};border:1px solid {border};border-radius:{radius}px;alternate-background-color:{bg};gridline-color:{border}}} QListWidget::item{{padding:13px}} QListWidget::item:selected,QTableView::item:selected{{background:{accent};color:{bg}}} QHeaderView::section{{background:{card};color:{accent};padding:8px;border:1px solid {border}}} QFrame#metric{{background:{card};border:1px solid {border};border-radius:{radius}px}}')
        if self.data: self.render()
    def run_job(self,fn,done):
        if self.worker: return
        self.progress.show(); self.centralWidget().setEnabled(False); self.worker=Worker(fn); self.worker.status.connect(self.status.setText); self.done_callback=done; self.worker.result.connect(self.job_result, Qt.ConnectionType.QueuedConnection); self.worker.failed.connect(self.failure, Qt.ConnectionType.QueuedConnection); self.worker.start()
    def job_result(self,r): self.complete(self.done_callback,r)
    def complete(self,done,r):
        self.worker.wait(); self.worker=None; self.centralWidget().setEnabled(True); self.progress.hide(); self.status.setText('Készen áll'); done(r); self.drain()
    def failure(self,s): self.complete(lambda _:QMessageBox.critical(self,'Hiba',s),None)
    def loaded(self,turns,focus=None):
        self.turns=turns; self.character.blockSignals(True); self.character.clear(); self.character.addItems(sorted({x['character'] for x in turns})); self.character.blockSignals(False)
        if focus:
            x=next((x for x in turns if x['hash']==focus),None)
            if x: self.character.blockSignals(True); self.character.setCurrentText(x['character']); self.character.blockSignals(False); self.range_changed(False); self.lo.setValue(x['turn'] or 0); self.hi.setValue(x['turn'] or 0); self.nav.setCurrentRow(0); self.refresh(focus); return
        self.range_changed()
    def range_changed(self,*args):
        ns=[x['turn'] or 0 for x in self.turns if x['character']==self.character.currentText()]; self.lo.setValue(min(ns,default=0)); self.hi.setValue(max(ns,default=0));
        if args!=(False,): self.refresh()
    def refresh(self,focus=None):
        if self.lo.value()>self.hi.value(): QMessageBox.warning(self,'Tartomány','A kezdő forduló nagyobb a zárónál.'); return
        self.selected=[x for x in self.turns if x['character']==self.character.currentText() and self.lo.value()<=(x['turn'] or 0)<=self.hi.value() and (not focus or x['hash']==focus)]; self.run_job(lambda p:report(self.selected,p),self.report_done)
    def report_done(self,d): self.data=d; self.render()
    def import_paths(self,paths,focus=False):
        if not paths:return
        if self.worker: self.pending.append((paths,focus)); return
        def job(p):
            errors=[]; last=None
            for i,f in enumerate(paths):
                p(f'Importálás {i+1}/{len(paths)}: {Path(f).name}')
                try:
                    path=Path(f); raw=path.read_bytes(); parsed=store.parse_turn(raw,path.name)
                    if parsed['turn'] is None: raise ValueError('Nem található fordulószám')
                    store.save(parsed); last=parsed['hash']
                except Exception as e: errors.append(f'{f}: {e}')
            return store.load_all(),last if focus else None,errors
        def done(r):
            turns,last,errors=r
            if errors: QMessageBox.warning(self,'Importálási hibák','\n'.join(errors))
            self.loaded(turns,last)
        self.run_job(job,done)
    def drain(self):
        if not self.worker and self.pending:
            paths,focus=self.pending.pop(0); self.import_paths(paths,focus)
    def files(self): self.import_paths(QFileDialog.getOpenFileNames(self,'Fordulók', '', 'Fordulók (*.html *.htm *.mhtml *.mht)')[0])
    def folder(self):
        d=QFileDialog.getExistingDirectory(self,'Fordulómappa');
        if d:self.import_paths(sorted(str(p) for p in Path(d).rglob('*') if p.is_file() and p.suffix.lower() in EXT))
    def clear_db(self):
        if QMessageBox.question(self,'Adatbázis kiürítése','Végleg törlöd az összes importált fordulót? Az eredeti fájlok megmaradnak.',QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,QMessageBox.StandardButton.No)==QMessageBox.StandardButton.Yes: self.run_job(lambda p:(store.clear_database(),store.load_all())[1],self.loaded)
    def heading(self,l,s): w=QLabel(s); w.setObjectName('heading'); l.addWidget(w)
    def note(self,l,s): w=QLabel(s); w.setWordWrap(True); l.addWidget(w)
    def button(self,l,s,fn): w=QPushButton(s); w.clicked.connect(fn); l.addWidget(w)
    def table(self,l,name,df=None,on_open=None):
        df=self.data.get(name,pd.DataFrame()) if df is None else df; self.heading(l,name)
        if df.empty: self.note(l,'Nincs adat.'); return
        row=QHBoxLayout(); l.addLayout(row); search=QLineEdit(); search.setPlaceholderText('Szűrés a táblázatban…'); row.addWidget(search,1); model=Model(df); proxy=QSortFilterProxyModel(self); proxy.setSourceModel(model); proxy.setFilterKeyColumn(-1); proxy.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive); proxy.setSortRole(Qt.ItemDataRole.UserRole); search.textChanged.connect(proxy.setFilterFixedString)
        view=QTableView(); view.setModel(proxy); view._model=model; view._proxy=proxy; model.setParent(view); proxy.setParent(view); view.setSortingEnabled(True); view.setAlternatingRowColors(True); view.setMinimumHeight(250); view.horizontalHeader().setDefaultSectionSize(145); l.addWidget(view)
        if on_open: view.doubleClicked.connect(lambda idx: on_open(proxy.mapToSource(idx).row()))
        for ext in ('csv','xlsx'):
            b=QPushButton(ext.upper()); row.addWidget(b); b.clicked.connect(lambda _,e=ext,d=df,n=name:self.export(d,n,e))
    def export(self,d,n,e):
        f=QFileDialog.getSaveFileName(self,'Exportálás',n+'.'+e,f'{e.upper()} (*.{e})')[0]
        if f:
            try:
                if not f.lower().endswith('.'+e):f+='.'+e
                if e=='csv':d.to_csv(f,index=False,encoding='utf-8-sig')
                else:d.to_excel(f,index=False)
            except Exception as exc:QMessageBox.critical(self,'Exportálási hiba',str(exc))
    def chart(self,l,name,x,y):
        d=self.data.get(name,pd.DataFrame());
        if d.empty:return
        bg,card,accent,fg,border,*_=THEMES[self.theme.currentText()]; fig=Figure(figsize=(7,3),facecolor=card,layout='constrained'); ax=fig.add_subplot(111,facecolor=card); d=d.head(20); ax.barh(d[x].astype(str),d[y],color=accent); ax.invert_yaxis(); ax.tick_params(colors=fg,labelsize=8); ax.set_title(name,color=fg); ax.grid(axis='x',alpha=.15); ax.set_axisbelow(True); [s.set_color(border) for s in ax.spines.values()]; canvas=FigureCanvasQTAgg(fig); canvas.setMinimumHeight(290); l.addWidget(canvas)
    def metrics(self,l,items):
        row=QHBoxLayout(); l.addLayout(row)
        for n,v in items:
            f=QFrame(); f.setObjectName('metric'); a=QVBoxLayout(f); a.addWidget(QLabel(n)); self.heading(a,str(v)); row.addWidget(f)
    def combat_panel(self,l,b):
        if b.empty: self.note(l,'Nincs csata.'); return
        self.metrics(l,[('Csaták',fmt(len(b))),('Kapott sebzés',fmt(b.taken.sum(min_count=1))),('Gyógyulás',fmt(b.healed.sum(min_count=1))),('Nettó ÉP',fmt(b.net.sum(min_count=1))),('Okozott sebzés',fmt(b.dealt.sum(min_count=1)))])
        self.note(l,'Nettó ÉP = a játék által közölt összesen érték. Negatív: veszteség; pozitív: nyereség. A diagram a kiválasztott fordulókra vonatkozik.')
        summary=aggregate(b); controls=QHBoxLayout(); l.addLayout(controls)
        metric=QComboBox(); metric.addItems(METRICS); controls.addWidget(metric,2)
        mode=QComboBox(); mode.addItems(['Összesített érték','Csatánkénti átlag']); controls.addWidget(mode,1)
        limit=QComboBox(); limit.addItems(['Top 20','Top 50','Mind']); controls.addWidget(limit)
        bg,card,accent,fg,border,*_=THEMES[self.theme.currentText()]
        fig=Figure(figsize=(8,5),facecolor=card,layout='constrained'); canvas=FigureCanvasQTAgg(fig); l.addWidget(canvas)
        self.note(l,'Kattints egy oszlopra vagy szörny nevére a csaták megnyitásához. A táblázatban dupla kattintás is működik.')
        def draw():
            key=METRICS[metric.currentText()]; mode.setEnabled(key!='count'); d=ranking(summary,metric.currentText(),mode.currentIndex()==1)
            if limit.currentIndex()<2: d=d.head([20,50][limit.currentIndex()])
            fig.clear(); ax=fig.add_subplot(111,facecolor=card); names=d.monster.tolist(); values=d.value.tolist()
            colors=[('#d87980' if v<0 else '#66c79d') if key=='net' else {'taken':'#d87980','healed':'#66c79d','dealt':'#c9a76b','count':'#62c6c8'}[key] for v in values]
            bars=ax.barh(range(len(names)),values,color=colors,picker=True); ax.set_yticks(range(len(names)),names); ax.invert_yaxis(); ax.axvline(0,color=fg,alpha=.6); ax.tick_params(colors=fg,labelsize=9); ax.xaxis.set_major_formatter(FuncFormatter(lambda x,pos:fmt(x))); ax.set_xlabel('Darab' if key=='count' else 'Életpont (ÉP)',color=fg); ax.set_title(metric.currentText()+' – '+('csatánkénti átlag' if mode.currentIndex()==1 and key!='count' else 'összesen'),color=fg); ax.grid(axis='x',alpha=.15); ax.set_axisbelow(True); ax.margins(x=.24)
            for spine in ax.spines.values():spine.set_color(border)
            for bar,name,v in zip(bars,names,values):
                bar._monster=name; ax.annotate(fmt(v),(v,bar.get_y()+bar.get_height()/2),xytext=(5 if v>=0 else -5,0),textcoords='offset points',ha='left' if v>=0 else 'right',va='center',color=fg,fontsize=9)
            for tick,name in zip(ax.get_yticklabels(),names):tick.set_picker(True); tick._monster=name
            canvas.setMinimumHeight(max(340, len(names)*25+100)); canvas.draw_idle()
        def pick(event):
            name=getattr(event.artist,'_monster',None)
            if name is not None:self.monster_dialog(b[b.monster==name])
        canvas.mpl_connect('pick_event',pick)
        for w in (metric,mode,limit):w.currentIndexChanged.connect(draw)
        draw()
        columns={'monster':'Szörny','count':'Csaták','taken':'Kapott sebzés','healed':'Gyógyulás','net':'Nettó ÉP','dealt':'Okozott sebzés','net_avg':'Átlagos nettó ÉP','taken_avg':'Átlagos kapott sebzés','dealt_avg':'Átlagos okozott sebzés','healed_avg':'Átlagos gyógyulás','dealt_known':'Ismert okozott sebzés (db)'}
        ordered=summary.sort_values('net').reset_index(drop=True)
        self.table(l,'Szörnyenként – teljes rangsor',ordered[list(columns)].rename(columns=columns),lambda i:self.monster_dialog(b[b.monster==ordered.iloc[i].monster]))
        self.table(l,'Összes csata',display_battles(b),lambda i:self.battle_dialog(b.iloc[i]))
        self.table(l,'További harci mutatók (becslések is)',self.data.get('Szörnyenként',pd.DataFrame()))
    def monster_dialog(self,b):
        if len(b)==1:self.battle_dialog(b.iloc[0]); return
        dlg=QDialog(self); dlg.setWindowTitle(str(b.iloc[0].monster)+' – összecsapások'); dlg.resize(1050,620); l=QVBoxLayout(dlg)
        self.heading(l,str(b.iloc[0].monster)+' • '+str(len(b))+' csata')
        self.metrics(l,[(LABELS[k],fmt(b[k].sum(min_count=1))) for k in ('taken','healed','net','dealt')]); self.note(l,'Dupla kattintással megnyitható az egyedi csata.')
        cols=['turn','battle_no','taken','healed','net','dealt','xp','rounds_est']; self.table(l,'Összecsapások',display_battles(b[cols]),lambda i:self.battle_dialog(b.iloc[i])); self.button(l,'Bezárás',dlg.accept); dlg.exec()
    def battle_dialog(self,r):
        dlg=QDialog(self); dlg.resize(1000,720); dlg.setWindowTitle(f'{r.monster} – {r.turn}. forduló'); l=QVBoxLayout(dlg)
        self.heading(l,f'{r.monster} • {r.turn}. forduló • {r.battle_no}. csata'); self.metrics(l,[(LABELS[k],fmt(r[k])) for k in ('taken','healed','net','dealt')]); self.table(l,'Részletes adatok',pd.DataFrame([{'Mutató':LABELS.get(k,k),'Érték':v} for k,v in r.items() if k not in ('source_hash','evidence','attack_evidence')]))
        self.note(l,'Eredeti fordulószöveg – az előző csatastatisztikától az aktuálisig (köztes eseményeket is tartalmazhat).')
        text=QPlainTextEdit(); text.setReadOnly(True); source=next((x for x in self.selected if x['hash']==r.source_hash),None)
        if source:
            lines=[x.strip() for x in source['text'].splitlines() if x.strip()]; end=int(r.line)-1; start=next((i+1 for i in range(end-1,-1,-1) if 'Csatastatisztika' in lines[i]),0); text.setPlainText('\n'.join(lines[start:end+1])+'\n\n'+str(r.evidence))
        else:text.setPlainText(str(r.evidence))
        l.addWidget(text,1); self.button(l,'Bezárás',dlg.accept); dlg.exec()
    def render(self):
        for l in self.pages:
            while l.count(): self.remove(l.takeAt(0))
        a,i,t,b,c,h,s,q,k=self.pages; self.heading(a,'Áttekintés'); d=self.data.get('TVP események',pd.DataFrame()); battles=self.data.get('Összes csata',pd.DataFrame()); earned=d.loc[d['Típus']=='Bevétel','TVP'].sum() if not d.empty else 0; spent=-d.loc[d['Típus']=='Kiadás','TVP'].sum() if not d.empty else 0
        self.metrics(a,[('Fordulók',len(self.selected)),('Csaták',len(battles)),('TVP-bevétel',earned),('TVP-kiadás',spent)]); self.button(a,'Fordulók importálása',self.files); self.button(a,'Adatbázis kiürítése',self.clear_db); self.table(a,'Fordulók'); self.heading(i,'Fordulók importálása'); self.button(i,'Fájlok kiválasztása',self.files); self.button(i,'Teljes mappa (almappákkal)',self.folder); self.note(i,'HTML, HTM, MHTML, MHT • Azonos fájlok SHA-256 alapján nem duplikálódnak.')
        self.heading(t,'TVP-gazdálkodás'); self.metrics(t,[('Bevétel',earned),('Kiadás',spent),('Nettó',earned-spent)]); self.note(t,'Feltételes események: csak darabszám; a mozgás teljes költsége változatlan.');
        for n in ['Bevételek','Kiadások']: self.chart(t,n,'Kategória','TVP'); self.table(t,n)
        cond=self.data.get('Feltételes események',pd.DataFrame());
        if not cond.empty: self.metrics(t,[(n, int(cond[n].sum()) if cond[n].notna().any() else 'Nincs adat') for n in ['Feltételes kutatás','Feltételes mászás','Feltételes gyógyítás']]);
        self.table(t,'Feltételes események'); self.table(t,'Fordulónkénti TVP'); self.table(t,'TVP események'); self.heading(b,'Harci statisztikák'); self.note(b,'A körök és támadási tartalék becslések. Nincs automatikus Düh-javaslat.');
        self.combat_panel(b,battles)
        self.chart(c,'Parancsok összesítve','Parancs','Darab'); self.table(c,'Parancsok'); self.note(h,'Kizárólag span.hiba jelölések.'); self.table(h,'Hibajelzések'); self.heading(s,'Keresés'); query=QLineEdit(); query.setPlaceholderText('Keresett szöveg'); s.addWidget(query); results=QVBoxLayout(); s.addLayout(results)
        def find():
            while results.count():self.remove(results.takeAt(0))
            needle=query.text().strip().casefold(); hits=[]
            if needle:
                for x in self.selected:
                    for j,line in enumerate(x['text'].splitlines(),1):
                        if needle in line.casefold():hits.append({'Forduló':x['turn'],'Sor':j,'Találat':line})
                        if len(hits)>=1000:break
                    if len(hits)>=1000:break
            self.table(results,'Találatok (max. 1000)',pd.DataFrame(hits))
        self.button(s,'Keresés',find); query.returnPressed.connect(find); self.heading(q,'Adatminőség'); self.note(q,f'Hiányzó eredeti HTML: {sum(not x.get("_html") for x in self.selected)}. Ezeknél szöveges tartalékfeldolgozás fut; importáld újra az eredetit.'); self.table(q,'Fordulók'); self.heading(k,'Beállítások'); self.note(k,f'Adatbázis: {store.DB}\nTéma és ablakméret automatikusan mentve.'); self.button(k,'Adatbázis kiürítése',self.clear_db)
    def remove(self,item):
        if item.widget():item.widget().deleteLater()
        elif item.layout():
            while item.layout().count():self.remove(item.layout().takeAt(0))
            item.layout().deleteLater()
    def closeEvent(self,e):
        if self.worker: QMessageBox.information(self,'Feldolgozás','Várd meg az aktuális művelet végét.'); e.ignore(); return
        self.settings.setValue('geometry',self.saveGeometry()); e.accept()
def main():
    p=argparse.ArgumentParser(); p.add_argument('--fordulo',type=Path); args=p.parse_args(); app=QApplication(sys.argv[:1]); name='tf-analyzer-'+hashlib.sha256(str(ROOT).encode()).hexdigest()[:20]; lock=QLockFile(str(ROOT/'.analyzer.lock')); lock.setStaleLockTime(0)
    if not lock.tryLock(100):
        if not args.fordulo:return 0
        sock=QLocalSocket(); sock.connectToServer(name)
        if not sock.waitForConnected(3000): print('Az Analyzer nem érhető el.',file=sys.stderr); return 1
        sock.write(str(args.fordulo.resolve()).encode('utf-8')+b'\n'); sock.flush(); sock.waitForBytesWritten(3000); return 0
    QLocalServer.removeServer(name); server=QLocalServer(); server.setSocketOptions(QLocalServer.SocketOption.UserAccessOption); server.listen(name); w=Window(); sockets=[]
    def receive():
        while server.hasPendingConnections():
            sock=server.nextPendingConnection(); sockets.append(sock)
            def read(s=sock):
                if not s.canReadLine():return
                path=bytes(s.readLine()).decode('utf-8').strip(); w.showNormal(); w.raise_(); w.activateWindow(); w.import_paths([path],True); s.disconnectFromServer()
            sock.readyRead.connect(read); sock.disconnected.connect(lambda s=sock:sockets.remove(s) if s in sockets else None); read()
    server.newConnection.connect(receive); w.show()
    if args.fordulo: QTimer.singleShot(0,lambda:w.import_paths([str(args.fordulo.resolve())],True))
    return app.exec()
if __name__=='__main__':sys.exit(main())
