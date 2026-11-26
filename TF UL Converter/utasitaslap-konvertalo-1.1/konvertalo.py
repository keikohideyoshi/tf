#!/usr/bin/env python3
"""Túlélők Földje – Utasításlap konvertáló (ODS/XLSX)."""
import re
import sys
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

SUM_RE = re.compile(r'(?i)\bSUM\s*\(\s*(?:\[)?\s*\.?\$?([A-Z]+)\$?(\d+)\s*:\s*\.?\$?([A-Z]+)\$?(\d+)\s*(?:\])?\s*\)')


def col_num(letters):
    n = 0
    for ch in letters.upper(): n = n * 26 + ord(ch) - 64
    return n


def number(value):
    if value is None or isinstance(value, bool): return None
    if isinstance(value, (int, float, Decimal)):
        v = Decimal(str(value))
    elif isinstance(value, str):
        try: v = Decimal(value.strip())
        except InvalidOperation: return None
    else: return None
    return v if v.is_finite() else None


def fmt_num(v):
    if v is None: return '0'
    return format(v, 'f').rstrip('0').rstrip('.') if v != v.to_integral_value() else str(int(v))


@dataclass
class Sheet:
    values: dict
    formulas: dict
    name: str

    def get(self, row, col): return self.values.get((row, col))


def read_xlsx(path):
    from openpyxl import load_workbook
    wb = load_workbook(path, read_only=False, data_only=False)
    result = []
    for ws in wb.worksheets:
        values, formulas = {}, {}
        for row in ws:
            for cell in row:
                if cell.value is None: continue
                key = (cell.row, cell.column)
                if cell.data_type == 'f': formulas[key] = str(cell.value)
                else: values[key] = cell.value
        result.append(Sheet(values, formulas, ws.title))
    wb.close()
    return result


def read_ods(path):
    from odf.opendocument import load
    from odf.table import Table, TableRow
    from odf import teletype
    doc = load(str(path))
    result = []
    for table in doc.spreadsheet.getElementsByType(Table):
        values, formulas = {}, {}
        row_index = 1
        for row in table.childNodes:
            if getattr(row, 'qname', (None, None))[1] != 'table-row': continue
            row_repeat = int(row.getAttribute('numberrowsrepeated') or 1)
            col_index = 1
            for cell in row.childNodes:
                if getattr(cell, 'qname', (None, None))[1] not in ('table-cell', 'covered-table-cell'): continue
                col_repeat = int(cell.getAttribute('numbercolumnsrepeated') or 1)
                formula = cell.getAttribute('formula')
                val = cell.getAttribute('value')
                if val is not None:
                    try: val = Decimal(val)
                    except InvalidOperation: pass
                else:
                    val = teletype.extractText(cell).strip() or None
                if formula or val is not None:
                    for rr in range(row_index, row_index + min(row_repeat, 100)):
                        for cc in range(col_index, col_index + min(col_repeat, 100)):
                            if formula: formulas[(rr, cc)] = formula
                            elif val is not None: values[(rr, cc)] = val
                col_index += col_repeat
            row_index += row_repeat
        result.append(Sheet(values, formulas, table.getAttribute('name')))
    return result


def read_file(path):
    suffix = Path(path).suffix.lower()
    if suffix == '.xlsx': return read_xlsx(path)
    if suffix == '.ods': return read_ods(path)
    raise ValueError('Csak .ods és .xlsx fájl támogatott.')


def sum_ranges(sheet):
    found = []
    for (row, col), formula in sheet.formulas.items():
        for match in SUM_RE.finditer(formula.replace('$', '')):
            a, r1, b, r2 = match.groups()
            c1, c2 = col_num(a), col_num(b)
            if int(r1) == 1 and int(r2) == 40 and c2 - c1 == 2 and row > 40:
                found.append((c1 - 1, row, col, formula))
    return found


def commands(sheet, start_col):
    result = []
    for row in range(1, 41):
        cmd = sheet.get(row, start_col)
        if cmd is None or str(cmd).strip() == '':
            if any(sheet.get(row, start_col + i) not in (None, '') for i in (1, 2, 3)):
                raise ValueError(f'{row}. sor: paraméter szerepel parancs nélkül.')
            continue
        if not isinstance(cmd, str) or not re.fullmatch(r'[a-zA-Z][a-zA-Z0-9]*', cmd.strip()):
            raise ValueError(f'{row}. sor: érvénytelen parancs: {cmd!r}')
        params = []
        for i in (1, 2, 3):
            raw = sheet.get(row, start_col + i)
            if raw is None or str(raw).strip() == '': params.append(Decimal(0)); continue
            v = number(raw)
            if v is None or v != v.to_integral_value():
                raise ValueError(f'{row}. sor, {i}. paraméter: egész szám szükséges ({raw!r}).')
            params.append(v)
        result.append((cmd.strip(), params))
    if not result: raise ValueError('Nem találhatók parancsok.')
    return result


def detect_normal(sheets):
    candidates = []
    for sheet in sheets:
        for start, row, col, formula in sum_ranges(sheet):
            if start <= 4: continue
            try: parsed = commands(sheet, start)
            except ValueError: continue
            # Require the SUM cell to sit within the three parameter columns.
            if not (start + 1 <= col <= start + 3): continue
            candidates.append((sheet, start, parsed))
    unique = {(id(s), c): (s, c, cmds) for s, c, cmds in candidates}
    if not unique:
        raise ValueError('Nem található a normál UL. A program a parancsoszlop mellett, az első 40 sor három paraméteroszlopát összegző SZUM-képletet keresi.')
    if len(unique) != 1:
        details = ', '.join(f'{s.name}: {c}. oszlop' for s,c,_ in unique.values())
        raise ValueError('Több lehetséges normál UL található: ' + details + '. Kérlek, pontosítsd a munkalapot.')
    return next(iter(unique.values()))


def convert(parsed, ksz, szla, ford, psw, setting):
    head = f'VERSION=2.0&KSZ={ksz}&SZLA={szla}&FORD={ford}&'
    if setting: head += 'BEALL=OFF&'
    head += f'PSW={psw}&'
    lines = [head]
    checksum = Decimal(0)
    for n, (cmd, params) in enumerate(parsed, 1):
        lines.append(f'C{n}={cmd}&P{n}1={fmt_num(params[0])}&P{n}2={fmt_num(params[1])}&P{n}3={fmt_num(params[2])}&')
        checksum += sum((p for p in params if p < 1000), Decimal(0))
    lines.append(f'ELLSZ={fmt_num(checksum)}&KOD=B64&Post=P')
    return '\n'.join(lines) + '\n', fmt_num(checksum)


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('TF – Utasítás Lap konvertáló')
        self.geometry('1000x740')
        self.minsize(760, 570)
        self.bg = '#171b24'
        self.panel = '#222936'
        self.input_bg = '#2b3444'
        self.fg = '#e7edf7'
        self.muted = '#a8b6cb'
        self.accent = '#4285dc'
        self.configure(bg=self.bg)
        self.style = ttk.Style(self)
        if 'clam' in self.style.theme_names(): self.style.theme_use('clam')
        self.style.configure('TFrame', background=self.bg)
        self.style.configure('TLabel', background=self.bg, foreground=self.fg, font=('DejaVu Sans', 10))
        self.style.configure('Title.TLabel', font=('DejaVu Sans', 17, 'bold'))
        self.style.configure('Subtitle.TLabel', foreground=self.muted)
        self.style.configure('TButton', background=self.panel, foreground=self.fg, bordercolor='#3a465a',
                             lightcolor=self.panel, darkcolor=self.panel, padding=(12, 8), font=('DejaVu Sans', 10))
        self.style.map('TButton', background=[('active', '#35445a'), ('pressed', '#26354a')],
                       foreground=[('disabled', '#8290a4')])
        self.style.configure('Accent.TButton', background=self.accent, foreground='#ffffff',
                             bordercolor=self.accent, lightcolor=self.accent, darkcolor=self.accent)
        self.style.map('Accent.TButton', background=[('active', '#5599ed'), ('pressed', '#316ab5')])
        self.style.configure('TEntry', fieldbackground=self.input_bg, foreground=self.fg,
                             insertcolor=self.fg, bordercolor='#455167', lightcolor=self.input_bg,
                             darkcolor=self.input_bg, padding=6)
        self.style.map('TEntry', fieldbackground=[('readonly', self.input_bg)])
        self.style.configure('TNotebook', background=self.bg, borderwidth=0)
        self.style.configure('TNotebook.Tab', background=self.panel, foreground=self.muted,
                             padding=(16, 9), borderwidth=0)
        self.style.map('TNotebook.Tab', background=[('selected', '#35445a'), ('active', '#303b4d')],
                       foreground=[('selected', '#ffffff'), ('active', '#ffffff')])
        self.style.configure('Vertical.TScrollbar', background=self.panel, troughcolor=self.bg,
                             arrowcolor=self.fg, bordercolor=self.bg)
        self.style.configure('Horizontal.TScrollbar', background=self.panel, troughcolor=self.bg,
                             arrowcolor=self.fg, bordercolor=self.bg)
        self.vars = {name: tk.StringVar() for name in ('KSZ', 'SZLA', 'FORD', 'PSW')}
        self.file = tk.StringVar(value='Nincs kiválasztott fájl')
        self.status = tk.StringVar(value='Válassz ODS vagy XLSX fájlt, majd add meg a fejléc adatait.')
        self.outputs = {}
        self.make_ui()

    def make_ui(self):
        root = ttk.Frame(self, padding=22)
        root.pack(fill='both', expand=True)
        ttk.Label(root, text='Utasítás Lap konvertáló', style='Title.TLabel').pack(anchor='w')
        ttk.Label(root, text='Túlélők Földje · Beállítás és normál UL', style='Subtitle.TLabel').pack(anchor='w', pady=(3, 18))
        info = ttk.Frame(root)
        info.pack(fill='x')
        for index, (name, label, width) in enumerate((('KSZ','Karakterszám',12), ('SZLA','Számlaszám',12), ('FORD','Forduló',12), ('PSW','Küldő jelszó',20))):
            frame = ttk.Frame(info)
            frame.grid(row=0, column=index, sticky='ew', padx=(0, 12))
            info.columnconfigure(index, weight=1)
            ttk.Label(frame, text=label).pack(anchor='w', pady=(0, 5))
            entry = ttk.Entry(frame, textvariable=self.vars[name], width=width, show='•' if name == 'PSW' else '')
            entry.pack(fill='x')
        filebar = ttk.Frame(root)
        filebar.pack(fill='x', pady=(22, 12))
        ttk.Button(filebar, text='Fájl kiválasztása…', command=self.pick).pack(side='left')
        ttk.Label(filebar, textvariable=self.file).pack(side='left', padx=12)
        ttk.Button(filebar, text='Konvertálás', command=self.run, style='Accent.TButton').pack(side='right')
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill='both', expand=True, pady=(8, 10))
        self.texts = {}
        for key, title in [('bul', 'Beállítás UL'), ('normal', 'Normál UL')]:
            panel = ttk.Frame(self.notebook)
            self.notebook.add(panel, text=title)
            textframe = ttk.Frame(panel)
            textframe.pack(fill='both', expand=True, padx=3, pady=8)
            text = tk.Text(textframe, wrap='none', font=('DejaVu Sans Mono', 10), bg=self.panel, fg=self.fg, insertbackground=self.fg, selectbackground='#365e91', selectforeground='#ffffff', relief='flat', highlightthickness=0, padx=12, pady=12, undo=False)
            sy = ttk.Scrollbar(textframe, orient='vertical', command=text.yview)
            sx = ttk.Scrollbar(panel, orient='horizontal', command=text.xview)
            text.configure(yscrollcommand=sy.set, xscrollcommand=sx.set, state='disabled')
            text.pack(side='left', fill='both', expand=True)
            sy.pack(side='right', fill='y')
            sx.pack(fill='x')
            self.texts[key] = text
        footer = ttk.Frame(root)
        footer.pack(fill='x')
        ttk.Label(footer, textvariable=self.status, wraplength=680).pack(side='left', fill='x', expand=True)
        ttk.Button(footer, text='Mindkettő mentése', command=self.save_both).pack(side='right', padx=(8, 0))
        ttk.Button(footer, text='Aktuális mentése', command=self.save_current).pack(side='right')
        ttk.Button(footer, text='Bezárás', command=self.destroy).pack(side='right', padx=(0, 8))

    def pick(self):
        path = filedialog.askopenfilename(title='Utasításlap kiválasztása', filetypes=[('Táblázatok', '*.ods *.xlsx'), ('Minden fájl', '*.*')])
        if path: self.file.set(path)

    def validate(self):
        data = {k: v.get().strip() for k, v in self.vars.items()}
        if not re.fullmatch(r'\d{4}', data['KSZ']): raise ValueError('A karakterszám pontosan négy számjegyből álljon.')
        if not re.fullmatch(r'\d+', data['SZLA']): raise ValueError('A számlaszám csak számjegyeket tartalmazhat (a kezdő nulla megmarad).')
        if not re.fullmatch(r'[1-9]\d*', data['FORD']): raise ValueError('A forduló pozitív egész szám legyen.')
        if not data['PSW'] or any(c in data['PSW'] for c in '&\r\n='):
            raise ValueError('Adj meg érvényes küldő jelszót (nem tartalmazhat &, = vagy sortörés karaktert).')
        return data

    def run(self):
        try:
            self.outputs = {}
            data = self.validate()
            path = self.file.get()
            if not Path(path).is_file(): raise ValueError('Előbb válassz egy létező ODS/XLSX fájlt.')
            sheets = read_file(path)
            # BUL is always in columns A:D; choose the sheet with its formula.
            bul_sheets = [s for s in sheets if any(start == 1 for start, _, _, _ in sum_ranges(s))]
            if len(bul_sheets) != 1: raise ValueError('A BUL munkalapja nem azonosítható egyértelműen az A–D oszlopok SZUM-képlete alapján.')
            bul = commands(bul_sheets[0], 1)
            normal_sheet, normal_col, normal = detect_normal(sheets)
            bul_txt, bul_sum = convert(bul, **{k.lower(): v for k,v in data.items()}, setting=True)
            norm_txt, norm_sum = convert(normal, **{k.lower(): v for k,v in data.items()}, setting=False)
            self.outputs = {'bul': bul_txt, 'normal': norm_txt}
            for key, content in self.outputs.items():
                widget = self.texts[key]
                widget.configure(state='normal')
                widget.delete('1.0', 'end')
                widget.insert('1.0', content)
                widget.configure(state='disabled')
            self.status.set(f'Kész · BUL: {len(bul)} parancs, ELLSZ={bul_sum} · Normál: {len(normal)} parancs, ELLSZ={norm_sum} · Normál oszlop: {normal_col}')
        except Exception as exc:
            self.status.set('Konvertálási hiba')
            messagebox.showerror('Konvertálás sikertelen', str(exc))

    def save_current(self):
        key = 'bul' if self.notebook.index(self.notebook.select()) == 0 else 'normal'
        if key not in self.outputs: messagebox.showinfo('Nincs kimenet', 'Előbb konvertálj egy fájlt.'); return
        self.save(key)

    def save(self, key, folder=None):
        suffix = 'BUL' if key == 'bul' else 'normal_UL'
        default = f'{self.vars["KSZ"].get()}-{self.vars["FORD"].get()}-{suffix}.txt'
        if folder is None:
            path = filedialog.asksaveasfilename(defaultextension='.txt', initialfile=default, filetypes=[('Szövegfájl', '*.txt')])
            if not path: return
        else: path = str(Path(folder) / default)
        Path(path).write_text(self.outputs[key], encoding='utf-8', newline='\n')
        return path

    def save_both(self):
        if len(self.outputs) != 2: messagebox.showinfo('Nincs kimenet', 'Előbb konvertálj egy fájlt.'); return
        folder = filedialog.askdirectory(title='Kimeneti mappa kiválasztása')
        if not folder: return
        targets = [Path(folder) / f'{self.vars["KSZ"].get()}-{self.vars["FORD"].get()}-{suffix}.txt' for suffix in ('BUL','normal_UL')]
        if any(p.exists() for p in targets) and not messagebox.askyesno('Felülírás', 'Egy vagy több kimeneti fájl már létezik. Felülírhatom?'): return
        for key in ('bul', 'normal'): self.save(key, folder)
        self.status.set(f'Két fájl mentve: {folder}')


if __name__ == '__main__':
    App().mainloop()
