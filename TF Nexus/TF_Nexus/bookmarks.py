"""Local bookmark menu and editor; no external dependencies beyond Qt."""
from pathlib import Path
from urllib.parse import urlsplit
import os
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices, QIcon
from PySide6.QtWidgets import (QDialog, QFormLayout, QLineEdit, QComboBox, QPushButton,
    QHBoxLayout, QVBoxLayout, QDialogButtonBox, QFileDialog, QMessageBox, QListWidget,
    QListWidgetItem, QAbstractItemView, QListView, QStyle, QLabel, QMenu, QToolButton)


def local_path(value):
    return Path(os.path.expandvars(value)).expanduser().absolute()


def valid_web(value):
    try:
        u = urlsplit(value)
        return u.scheme.lower() in ('http', 'https') and bool(u.hostname) and not any(c.isspace() for c in value)
    except ValueError:
        return False


def bookmark_icon(widget, entry):
    kind = entry['kind']
    if kind == 'web':
        icon = QIcon.fromTheme('internet-web-browser')
        fallback = QStyle.SP_DriveNetIcon
    elif kind == 'folder':
        icon = QIcon.fromTheme('folder')
        fallback = QStyle.SP_DirIcon
    else:
        suffix = Path(entry.get('target', '')).suffix.lower()
        theme = 'x-office-spreadsheet' if suffix in ('.xlsx','.xls','.ods','.csv') else 'application-pdf' if suffix == '.pdf' else 'text-x-generic'
        icon = QIcon.fromTheme(theme)
        fallback = QStyle.SP_FileIcon
    return widget.style().standardIcon(fallback) if icon.isNull() else icon


class BookmarkEdit(QDialog):
    def __init__(self, parent, entry=None):
        super().__init__(parent)
        self.setWindowTitle('Könyvjelző szerkesztése' if entry else 'Új könyvjelző')
        self.resize(560, 200)
        entry = entry or {}
        f = QFormLayout(self)
        self.name = QLineEdit(entry.get('name',''))
        f.addRow('Megjelenítendő név', self.name)
        self.kind = QComboBox()
        for label, key in [('Weboldal','web'),('Helyi fájl','file'),('Helyi könyvtár','folder')]:
            self.kind.addItem(label,key)
        self.kind.setCurrentIndex(max(0,self.kind.findData(entry.get('kind','web'))))
        f.addRow('Típus',self.kind)
        self.target = QLineEdit(entry.get('target',''))
        h = QHBoxLayout(); h.addWidget(self.target,1)
        self.browse_button = QPushButton('Tallózás…'); h.addWidget(self.browse_button)
        self.browse_button.clicked.connect(self.browse)
        f.addRow('Webcím / elérési út',h)
        self.kind.currentIndexChanged.connect(self.update_kind)
        self.update_kind()
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Save).setText('Mentés'); buttons.button(QDialogButtonBox.Cancel).setText('Mégse')
        buttons.accepted.connect(self.accept); buttons.rejected.connect(self.reject); f.addRow(buttons)

    def update_kind(self,*_):
        web = self.kind.currentData() == 'web'
        self.browse_button.setEnabled(not web)
        self.target.setPlaceholderText('https://…' if web else '/home/…')

    def browse(self):
        start = str(local_path(self.target.text())) if self.target.text() else str(Path.home())
        if self.kind.currentData() == 'folder':
            value = QFileDialog.getExistingDirectory(self,'Könyvtár kiválasztása',start)
        else:
            value,_ = QFileDialog.getOpenFileName(self,'Fájl kiválasztása',start)
        if value: self.target.setText(value)

    def accept(self):
        name, target, kind = self.name.text().strip(), self.target.text().strip(), self.kind.currentData()
        if not name or not target:
            QMessageBox.warning(self,'Könyvjelző','A név és a cél megadása kötelező.'); return
        if kind == 'web':
            if not valid_web(target):
                QMessageBox.warning(self,'Könyvjelző','Érvényes http:// vagy https:// webcímet adj meg.'); return
        else:
            p = local_path(target)
            if not (p.is_file() if kind == 'file' else p.is_dir()):
                QMessageBox.warning(self,'Könyvjelző','A kiválasztott fájl vagy könyvtár nem található.'); return
            target = str(p)
        self.entry = dict(kind=kind,name=name,target=target)
        super().accept()


class BookmarkManager(QDialog):
    def __init__(self,parent,entries,commit):
        super().__init__(parent); self.commit = commit
        self.setWindowTitle('Könyvjelzők kezelése'); self.resize(650,440)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel('A sorrend fogd és vidd módszerrel módosítható. A változások automatikusan mentődnek.'))
        self.items = QListWidget(); layout.addWidget(self.items,1)
        self.items.setViewMode(QListView.ListMode)
        self.items.setDragDropMode(QAbstractItemView.InternalMove)
        self.items.setDefaultDropAction(Qt.MoveAction)
        self.items.setSelectionMode(QAbstractItemView.SingleSelection)
        for entry in entries: self.items.addItem(self.make_item(entry))
        self.items.model().rowsMoved.connect(self.persist)
        self.items.itemDoubleClicked.connect(lambda _:self.edit())
        h = QHBoxLayout(); layout.addLayout(h)
        for name, fn in [('Hozzáadás',self.add),('Szerkesztés',self.edit),('Törlés',self.remove),('Elválasztó',self.separator)]:
            b=QPushButton(name); b.clicked.connect(fn); h.addWidget(b)
        close=QPushButton('Bezárás'); close.clicked.connect(self.accept); layout.addWidget(close)

    def make_item(self,entry):
        if entry['kind']=='separator':
            item=QListWidgetItem('──────── Elválasztó ────────')
        else:
            item=QListWidgetItem(bookmark_icon(self,entry),entry['name']+' — '+entry['target'])
            item.setToolTip(entry['target'])
        item.setData(Qt.UserRole,dict(entry))
        item.setFlags(item.flags() & ~Qt.ItemIsDropEnabled)
        return item

    def persist(self,*_):
        self.commit([self.items.item(i).data(Qt.UserRole) for i in range(self.items.count())])

    def insert(self,entry):
        row=self.items.currentRow(); row=row+1 if row>=0 else self.items.count()
        self.items.insertItem(row,self.make_item(entry)); self.items.setCurrentRow(row); self.persist()

    def add(self):
        d=BookmarkEdit(self)
        if d.exec(): self.insert(d.entry)

    def separator(self): self.insert({'kind':'separator'})

    def edit(self):
        row=self.items.currentRow()
        if row<0: return
        entry=self.items.item(row).data(Qt.UserRole)
        if entry['kind']=='separator': return
        d=BookmarkEdit(self,entry)
        if d.exec():
            self.items.takeItem(row); self.items.insertItem(row,self.make_item(d.entry)); self.items.setCurrentRow(row); self.persist()

    def remove(self):
        row=self.items.currentRow()
        if row<0: return
        if QMessageBox.question(self,'Törlés','Eltávolítod a menüelemet? Az eredeti fájl vagy könyvtár megmarad.')==QMessageBox.Yes:
            self.items.takeItem(row); self.persist()


class BookmarkMenu(QToolButton):
    def __init__(self,parent,config,save):
        super().__init__(parent); self.config=config; self.save=save
        self.setText('Könyvjelzők'); self.setPopupMode(QToolButton.InstantPopup)
        self.popup=QMenu(self); self.setMenu(self.popup)
        self.popup.aboutToShow.connect(self.rebuild); self.rebuild()

    def commit(self,entries):
        self.config['bookmarks']=entries; self.save()

    def rebuild(self):
        self.popup.clear()
        for entry in self.config['bookmarks']:
            if entry['kind']=='separator': self.popup.addSeparator(); continue
            action=self.popup.addAction(bookmark_icon(self,entry),entry['name'].replace('&','&&'))
            action.triggered.connect(lambda checked=False,e=entry:self.open_entry(e))
        if not any(e['kind']!='separator' for e in self.config['bookmarks']):
            self.popup.addAction('Még nincs könyvjelző').setEnabled(False)
        self.popup.addSeparator()
        self.popup.addAction('Új könyvjelző hozzáadása…',self.add)
        self.popup.addAction('Könyvjelzők kezelése…',self.manage)

    def add(self):
        d=BookmarkEdit(self)
        if d.exec(): self.commit(self.config['bookmarks']+[d.entry])

    def manage(self): BookmarkManager(self,self.config['bookmarks'],self.commit).exec()

    def open_entry(self,entry):
        target=entry['target']; kind=entry['kind']
        if kind=='web':
            if not valid_web(target):
                QMessageBox.warning(self,'Könyvjelző','Érvénytelen webcím.'); return
            url=QUrl(target)
        else:
            p=local_path(target)
            if not (p.is_file() if kind=='file' else p.is_dir()):
                QMessageBox.warning(self,'Könyvjelző','A fájl vagy könyvtár nem található. A könyvjelző megmarad.'); return
            url=QUrl.fromLocalFile(str(p))
        if not QDesktopServices.openUrl(url): QMessageBox.warning(self,'Könyvjelző','Nem sikerült megnyitni a célt.')
