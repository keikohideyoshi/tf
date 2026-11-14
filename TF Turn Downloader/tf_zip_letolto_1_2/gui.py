#!/usr/bin/env python3
"""Sötét témájú TF ZIP Letöltő GUI (Tkinter, külső témacsomag nélkül)."""
import queue
import re
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from tf_zip_letolto import URL, PROFILE, safe_filename
import zipfile

BG='#151a23'; PANEL='#202735'; FG='#edf2fa'; MUTED='#a7b4c6'; ACCENT='#528bff'

class App:
    def __init__(self, root):
        self.root=root; root.title('TF ZIP Letöltő 1.2'); root.geometry('820x630'); root.minsize(650,490); root.configure(bg=BG)
        self.events=queue.Queue(); self.busy=False; self.login_event=threading.Event()
        self.character=tk.StringVar(value='TF3042')
        self.folder=tk.StringVar(value=str(Path.home()/'Letöltések'/'TF'/'TF3042'))
        self.auto_folder=True
        self.status=tk.StringVar(value='Készen áll'); self.progress=tk.DoubleVar(value=0)
        style=ttk.Style(); style.theme_use('clam')
        style.configure('Dark.Horizontal.TProgressbar',troughcolor='#303a4a',background=ACCENT,borderwidth=0)
        outer=tk.Frame(root,bg=BG,padx=22,pady=18); outer.pack(fill='both',expand=True)
        tk.Label(outer,text='TF ZIP Letöltő',font=('DejaVu Sans',21,'bold'),bg=BG,fg=FG).pack(anchor='w')
        tk.Label(outer,text='Fordulók letöltése és HTML-fájlok kigyűjtése',font=('DejaVu Sans',10),bg=BG,fg=MUTED).pack(anchor='w',pady=(2,17))
        pane=tk.Frame(outer,bg=PANEL,padx=16,pady=14); pane.pack(fill='x')
        tk.Label(pane,text='Karakterazonosító',bg=PANEL,fg=MUTED).grid(row=0,column=0,sticky='w')
        entry=tk.Entry(pane,textvariable=self.character,bg='#111722',fg=FG,insertbackground=FG,relief='flat',font=('DejaVu Sans',11),width=18)
        entry.grid(row=1,column=0,sticky='we',padx=(0,16),ipady=8)
        entry.bind('<FocusOut>',self.update_default_folder)
        tk.Label(pane,text='ZIP-ek mappája',bg=PANEL,fg=MUTED).grid(row=0,column=1,sticky='w')
        self.path_entry=tk.Entry(pane,textvariable=self.folder,bg='#111722',fg=FG,insertbackground=FG,relief='flat',font=('DejaVu Sans',10))
        self.path_entry.grid(row=1,column=1,sticky='we',padx=(0,9),ipady=9)
        self.path_entry.bind('<KeyRelease>',lambda e:setattr(self,'auto_folder',False))
        tk.Button(pane,text='Tallózás',command=self.browse,bg='#354052',fg=FG,activebackground='#46556d',relief='flat',padx=12,pady=8).grid(row=1,column=2)
        pane.grid_columnconfigure(1,weight=1)
        actions=tk.Frame(outer,bg=BG); actions.pack(fill='x',pady=(17,14))
        self.download_button=self.button(actions,'ZIP-ek letöltése + HTML',self.download,ACCENT); self.download_button.pack(side='left',padx=(0,10))
        self.extract_button=self.button(actions,'HTML-ek kigyűjtése',self.extract,'#354052'); self.extract_button.pack(side='left')
        self.continue_button=self.button(actions,'Bejelentkezés kész',self.continue_login,'#27836a'); self.continue_button.pack(side='right'); self.continue_button.config(state='disabled')
        tk.Label(outer,textvariable=self.status,bg=BG,fg=FG,anchor='w').pack(fill='x')
        ttk.Progressbar(outer,variable=self.progress,maximum=100,style='Dark.Horizontal.TProgressbar').pack(fill='x',pady=(8,13))
        tk.Label(outer,text='Műveleti napló',bg=BG,fg=MUTED).pack(anchor='w',pady=(0,6))
        logframe=tk.Frame(outer,bg=PANEL); logframe.pack(fill='both',expand=True)
        self.logbox=tk.Text(logframe,bg=PANEL,fg=FG,insertbackground=FG,relief='flat',wrap='word',state='disabled',font=('DejaVu Sans Mono',9),padx=12,pady=10)
        sb=tk.Scrollbar(logframe,command=self.logbox.yview); self.logbox.configure(yscrollcommand=sb.set)
        self.logbox.pack(side='left',fill='both',expand=True); sb.pack(side='right',fill='y')
        foot=tk.Frame(outer,bg=BG); foot.pack(fill='x',pady=(12,0))
        tk.Label(foot,text='A HTML-ek a ZIP-mappán belüli HTML almappába kerülnek.',bg=BG,fg=MUTED).pack(side='left')
        tk.Button(foot,text='Bezárás',command=self.close,bg='#354052',fg=FG,relief='flat',padx=15,pady=6).pack(side='right')
        root.protocol('WM_DELETE_WINDOW',self.close)
        root.after(100,self.poll)

    def button(self,parent,text,command,bg):
        return tk.Button(parent,text=text,command=command,bg=bg,fg='white',activebackground=bg,activeforeground='white',relief='flat',font=('DejaVu Sans',10,'bold'),padx=15,pady=11,cursor='hand2')
    def update_default_folder(self,event=None):
        if self.auto_folder:
            self.folder.set(str(Path.home()/'Letöltések'/'TF'/self.character.get().upper().strip()))
    def browse(self):
        path=filedialog.askdirectory(initialdir=self.folder.get(),title='ZIP-ek mappája')
        if path: self.folder.set(path); self.auto_folder=False
    def emit(self,kind,*args): self.events.put((kind,args))
    def log(self,s): self.emit('log',s)
    def poll(self):
        try:
            while True:
                kind,args=self.events.get_nowait()
                if kind=='log':
                    self.logbox.config(state='normal'); self.logbox.insert('end',args[0]+'\n'); self.logbox.see('end'); self.logbox.config(state='disabled')
                elif kind=='status': self.status.set(args[0])
                elif kind=='progress': self.progress.set(args[0])
                elif kind=='login': self.continue_button.config(state='normal')
                elif kind=='done':
                    self.busy=False; self.download_button.config(state='normal'); self.extract_button.config(state='normal'); self.continue_button.config(state='disabled')
                    self.status.set(args[0]); self.progress.set(100)
        except queue.Empty: pass
        self.root.after(100,self.poll)
    def settings(self):
        c=self.character.get().upper().strip()
        if not re.fullmatch(r'TF\d+',c): messagebox.showerror('Hibás azonosító','Példa: TF3042'); return None
        p=Path(self.folder.get()).expanduser()
        if not str(p).strip(): messagebox.showerror('Hiba','Válassz célmappát!'); return None
        return c,p.resolve()
    def start(self,fn):
        if self.busy: return
        s=self.settings()
        if not s:return
        self.busy=True; self.progress.set(0); self.download_button.config(state='disabled'); self.extract_button.config(state='disabled')
        threading.Thread(target=self.run,args=(fn,*s),daemon=True).start()
    def download(self): self.start('download')
    def extract(self): self.start('extract')
    def continue_login(self): self.login_event.set(); self.continue_button.config(state='disabled')
    def run(self,mode,c,p):
        try:
            if mode=='download': self.download_zips(c,p)
            self.extract_html(p)
            self.emit('done','Kész – a művelet befejeződött.')
        except Exception as exc:
            self.log(f'HIBA: {type(exc).__name__}: {exc}'); self.emit('done','Hiba történt – részletek a naplóban.')
    def download_zips(self,c,p):
        from playwright.sync_api import sync_playwright
        p.mkdir(parents=True,exist_ok=True); PROFILE.mkdir(parents=True,exist_ok=True)
        self.emit('status','Böngésző indítása…')
        with sync_playwright() as pw:
            browser=pw.chromium.launch_persistent_context(str(PROFILE),headless=False,accept_downloads=True)
            try:
                page=browser.pages[0] if browser.pages else browser.new_page()
                page.goto(URL.format(c),wait_until='domcontentloaded',timeout=60000)
                self.login_event.clear(); self.emit('login'); self.emit('status','Jelentkezz be a böngészőben, majd kattints: Bejelentkezés kész')
                self.log('Várakozás a böngészős bejelentkezésre…')
                self.login_event.wait()
                if c not in page.url.upper(): page.goto(URL.format(c),wait_until='domcontentloaded',timeout=60000)
                links=page.locator('a').filter(has_text=re.compile(r'^\s*\(\s*ZIP\s*\)\s*$',re.I))
                n=links.count(); self.log(f'Talált ZIP-linkek: {n}')
                if n==0: raise RuntimeError('Nem találhatók (ZIP) linkek. Ellenőrizd a bejelentkezést.')
                ok=skip=bad=0
                for i in range(n):
                    self.emit('status',f'ZIP letöltés: {i+1}/{n}'); self.emit('progress',100*(i+1)/n)
                    try:
                        with page.expect_download(timeout=45000) as ev: links.nth(i).click(timeout=15000)
                        dl=ev.value; name=safe_filename(dl.suggested_filename)
                        if not name.lower().endswith('.zip'): raise ValueError('Nem ZIP fájlnév: '+name)
                        dest=p/name
                        if dest.exists() and zipfile.is_zipfile(dest): skip+=1; self.log('Meglévő: '+name); continue
                        temp=p/(name+'.part'); dl.save_as(temp)
                        if not zipfile.is_zipfile(temp): temp.unlink(missing_ok=True); raise ValueError('Hibás ZIP: '+name)
                        temp.replace(dest); ok+=1; self.log('Letöltve: '+name)
                    except Exception as exc: bad+=1; self.log(f'Letöltési hiba ({i+1}/{n}): {exc}')
                self.log(f'Letöltés: új {ok}, meglévő {skip}, hiba {bad}')
            finally: browser.close()
    def extract_html(self,p):
        if not p.exists(): raise FileNotFoundError(f'Nem létezik a ZIP-mappa: {p}')
        out=p/'HTML'; out.mkdir(exist_ok=True)
        zips=sorted(p.glob('*.zip')); self.log(f'HTML kigyűjtés: {len(zips)} ZIP')
        added=unchanged=errors=0
        for i,archive in enumerate(zips):
            self.emit('status',f'HTML kigyűjtés: {i+1}/{len(zips)}'); self.emit('progress',100*(i+1)/max(1,len(zips)))
            try:
                with zipfile.ZipFile(archive) as z:
                    for m in z.infolist():
                        if m.is_dir() or not m.filename.lower().endswith(('.htm','.html')):continue
                        try:
                            name=f'{safe_filename(archive.stem)}__{safe_filename(m.filename)}'; dest=out/name
                            data=z.read(m)
                            if dest.exists() and dest.read_bytes()==data: unchanged+=1;continue
                            if dest.exists():
                                k=2
                                while (out/f'{safe_filename(archive.stem)}__{k}__{safe_filename(m.filename)}').exists():k+=1
                                dest=out/f'{safe_filename(archive.stem)}__{k}__{safe_filename(m.filename)}'
                            dest.write_bytes(data);added+=1
                        except Exception as exc: errors+=1;self.log(f'HTML hiba: {archive.name}: {exc}')
            except Exception as exc: errors+=1;self.log(f'ZIP hiba: {archive.name}: {exc}')
        self.log(f'HTML: új {added}, változatlan {unchanged}, hiba {errors}')
        self.log(f'Célmappa: {out}')
    def close(self):
        if self.busy:
            messagebox.showinfo('Folyamatban','Várd meg a folyamat végét, mielőtt bezárod az alkalmazást.')
            return
        self.root.destroy()

if __name__=='__main__':
    root=tk.Tk(); App(root);root.mainloop()
