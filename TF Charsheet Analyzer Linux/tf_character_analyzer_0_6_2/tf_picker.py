"""Dark, resizable TF turn picker. Uses only standard-library Tkinter."""
from pathlib import Path
import re
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

EXTENSIONS = {'.html', '.htm', '.mhtml', '.mht'}
BG='#111a2b'; PANEL='#18263a'; ENTRY='#21344e'; FG='#e8f0ff'; MUTED='#b6c7df'; BLUE='#355b92'

def choose_turns():
    root=tk.Tk()
    root.title('TF Character Analyzer · Fordulók kiválasztása')
    root.geometry('900x620');root.minsize(560,390);root.resizable(True,True)
    root.configure(bg=BG)
    style=ttk.Style(root);style.theme_use('clam')
    style.configure('TF.Treeview',background=PANEL,fieldbackground=PANEL,foreground=FG,borderwidth=0,rowheight=29,font=('DejaVu Sans',10))
    style.map('TF.Treeview',background=[('selected',BLUE)],foreground=[('selected','#ffffff')])
    style.configure('TF.Treeview.Heading',background=ENTRY,foreground=FG,relief='flat',font=('DejaVu Sans',10,'bold'))
    style.map('TF.Treeview.Heading',background=[('active',BLUE)])
    style.configure('TF.Vertical.TScrollbar',background=ENTRY,troughcolor=BG,arrowcolor=FG)
    selected_paths=[]
    current_dir=tk.StringVar(value=str(Path.cwd()))
    status=tk.StringVar(value='')
    header=tk.Frame(root,bg=BG,padx=24,pady=18);header.pack(fill='x')
    tk.Label(header,text='TF Character Analyzer',font=('DejaVu Sans',19,'bold'),fg=FG,bg=BG,anchor='w').pack(fill='x')
    tk.Label(header,text='Fordulók kiválasztása · 0.6.2',font=('DejaVu Sans',10),fg=MUTED,bg=BG,anchor='w').pack(fill='x',pady=(3,0))
    folder=tk.Frame(root,bg=BG,padx=24);folder.pack(fill='x')
    tk.Label(folder,text='FORDULÓK MAPPÁJA',font=('DejaVu Sans',9,'bold'),fg=MUTED,bg=BG).pack(anchor='w',pady=(0,6))
    pathrow=tk.Frame(folder,bg=BG);pathrow.pack(fill='x')
    tk.Label(pathrow,textvariable=current_dir,anchor='w',fg=FG,bg=ENTRY,padx=12,pady=10,relief='flat').pack(side='left',fill='x',expand=True)
    def button(parent,text,command,primary=False):
        return tk.Button(parent,text=text,command=command,bg=BLUE if primary else ENTRY,fg='#ffffff',activebackground='#4673ac',activeforeground='#ffffff',relief='flat',bd=0,padx=15,pady=10,cursor='hand2',font=('DejaVu Sans',10,'bold'))
    content=tk.Frame(root,bg=BG,padx=24,pady=16);content.pack(fill='both',expand=True)
    tk.Label(content,text='ELÉRHETŐ FORDULÓK',font=('DejaVu Sans',9,'bold'),fg=MUTED,bg=BG).pack(anchor='w',pady=(0,8))
    tableframe=tk.Frame(content,bg=PANEL,highlightthickness=1,highlightbackground='#34445c');tableframe.pack(fill='both',expand=True)
    tree=ttk.Treeview(tableframe,columns=('turn','filename'),show='headings',selectmode='extended',style='TF.Treeview')
    tree.heading('turn',text='Forduló');tree.heading('filename',text='Fájlnév')
    tree.column('turn',width=110,minwidth=75,stretch=False,anchor='center');tree.column('filename',width=620,minwidth=200,stretch=True)
    scroll=ttk.Scrollbar(tableframe,orient='vertical',command=tree.yview,style='TF.Vertical.TScrollbar');tree.configure(yscrollcommand=scroll.set)
    scroll.pack(side='right',fill='y');tree.pack(side='left',fill='both',expand=True)
    def refresh():
        tree.delete(*tree.get_children())
        folder=Path(current_dir.get())
        try:
            paths=sorted((p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in EXTENSIONS),key=lambda p:(int(m.group(1)) if (m:=re.search(r'(\d{3,6})\.\s*fordul',p.name,re.I)) else 10**9,p.name.casefold()))
        except OSError as exc:
            messagebox.showerror('Mappa nem olvasható',str(exc),parent=root);paths=[]
        for p in paths:
            m=re.search(r'(\d{3,6})\.\s*fordul',p.name,re.I)
            tree.insert('', 'end',iid=str(p),values=(m.group(1) if m else '—',p.name))
        status.set(f'{len(paths)} fájl · 0 kijelölve')
    def browse():
        d=filedialog.askdirectory(parent=root,title='Fordulókat tartalmazó mappa',initialdir=current_dir.get(),mustexist=True)
        if d:current_dir.set(d);refresh()
    button(pathrow,'📁  Tallózás',browse).pack(side='left',padx=(10,0))
    def selection_changed(_=None):status.set(f'{len(tree.get_children())} fájl · {len(tree.selection())} kijelölve')
    tree.bind('<<TreeviewSelect>>',selection_changed)
    # Treeview extended selection natively supports Shift+arrows, Ctrl+click and Shift+click.
    # Bind Ctrl+A explicitly to select every file.
    def select_all(_=None):
        tree.selection_set(tree.get_children());selection_changed();return 'break'
    tree.bind('<Control-a>',select_all);tree.bind('<Control-A>',select_all)
    footer=tk.Frame(root,bg=BG,padx=24,pady=16);footer.pack(fill='x')
    tk.Label(footer,textvariable=status,bg=BG,fg=MUTED,font=('DejaVu Sans',10)).pack(side='left')
    def finish():
        selected_paths.extend(tree.selection());root.destroy()
    def cancel():root.destroy()
    button(footer,'Feldolgozás',finish,True).pack(side='right')
    button(footer,'Mégse',cancel).pack(side='right',padx=8)
    button(footer,'Összes kijelölése',select_all).pack(side='right',padx=8)
    tk.Label(root,text='Ctrl+kattintás: különálló fájlok  ·  Shift+nyíl: tartomány bővítése  ·  Ctrl+A: összes',bg=BG,fg=MUTED,font=('DejaVu Sans',9),pady=8).pack(fill='x')
    root.protocol('WM_DELETE_WINDOW',cancel)
    refresh();tree.focus_set();root.mainloop()
    return list(selected_paths)
