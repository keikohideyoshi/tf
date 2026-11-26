import tkinter as tk
from tkinter import ttk,filedialog,messagebox,simpledialog
import threading,queue,csv,os
from collections import Counter
from core import *
from mapview import MapView
BG='#10151e'; PANEL='#1c2533'; FG='#e0e6ef'; GOLD='#d6b579'; GREEN='#65c5a5'
class App:
 def __init__(self):
    self.root=tk.Tk();self.root.title('TF Journal 1.1');self.root.geometry('1180x760');self.root.minsize(800,520);self.root.configure(bg=BG)
    self.db=connect(ROOT/'journal.sqlite3');self.zones=load_zones();self.busy=False;self.q=queue.Queue();self.data={};self.sort={}
    s=ttk.Style();s.theme_use('clam');s.configure('.',background=BG,foreground=FG,fieldbackground=PANEL,font=('Sans',10));s.configure('TButton',background=PANEL,padding=7);s.map('TButton',background=[('active','#34465a')]);s.configure('Treeview',background=PANEL,fieldbackground=PANEL,foreground=FG,rowheight=27);s.configure('Treeview.Heading',background='#293749',foreground=GOLD);s.map('Treeview',background=[('selected','#36596a')]);s.configure('TCombobox',fieldbackground=PANEL);s.map('TCombobox',fieldbackground=[('readonly',PANEL)],foreground=[('readonly',FG)]);s.configure('TNotebook.Tab',padding=(12,8));s.map('TNotebook.Tab',background=[('selected',PANEL)]);s.configure('TEntry',insertcolor=FG)
    top=ttk.Frame(self.root,padding=14);top.pack(fill='x');tk.Label(top,text='TF Journal',font=('Sans',26,'bold'),bg=BG,fg=GOLD).pack(anchor='w');ttk.Label(top,text='A karakter útinaplója  •  1.1').pack(anchor='w')
    bar=ttk.Frame(self.root,padding=(14,0));bar.pack(fill='x');self.buttons=[]
    for text,cmd in [('Mappa importálása',self.folder),('Fájlok importálása',self.files),('Területszerkesztő',self.edit),('CSV export',lambda:self.export(False)),('Excel export',lambda:self.export(True))]:
        b=ttk.Button(bar,text=text,command=cmd);b.pack(side='left',padx=3);self.buttons.append(b)
    filters=ttk.Frame(self.root,padding=14);filters.pack(fill='x');ttk.Label(filters,text='Karakter:').pack(side='left');self.char=ttk.Combobox(filters,state='readonly',width=32);self.char.pack(side='left',padx=6);self.char.bind('<<ComboboxSelected>>',lambda e:self.refresh());self.lo=tk.StringVar();self.hi=tk.StringVar()
    for label,var in [('Fordulótól',self.lo),('Fordulóig',self.hi)]:ttk.Label(filters,text=label).pack(side='left',padx=5);ttk.Entry(filters,textvariable=var,width=8).pack(side='left')
    ttk.Button(filters,text='Szűrés',command=self.refresh).pack(side='left',padx=5);ttk.Button(filters,text='Alaphelyzet',command=self.reset).pack(side='left');self.summary=tk.Label(self.root,bg=PANEL,fg=GREEN,anchor='w',padx=15,pady=12,font=('Sans',12));self.summary.pack(fill='x',padx=14)
    self.nb=ttk.Notebook(self.root);self.nb.pack(fill='both',expand=True,padx=14,pady=10);self.trees={}
    for name,cols in [('Fordulók',['Forduló','Dátum','X','Y','Terület','Labirintus','Forrás','Koordináta forrása']),('Zónaváltások',['Előző forduló','Első ismert forduló','Honnan','Hová','Bizonyosság']),('Időszakok',['Terület','Első forduló','Utolsó forduló','Darab']),('Statisztikák',['Terület','Fordulók','Első','Utolsó','Időszakok','Leghosszabb','Egyedi mezők','Arány (%)']),('Hiányzó fordulók',['Első hiányzó','Utolsó hiányzó','Darab'])]:
        f=ttk.Frame(self.nb);self.nb.add(f,text=name);self.trees[name]=self.tree(f,cols,name)
    f=ttk.Frame(self.nb);self.nb.add(f,text='Idővonal');self.canvas=tk.Canvas(f,bg=PANEL,highlightthickness=0);self.canvas.pack(fill='both',expand=True);self.canvas.bind('<Configure>',lambda e:self.draw())
    self.mapview=MapView(self.nb,self);self.nb.add(self.mapview.frame,text="Térkép")
    self.status=tk.StringVar(value='Készen áll');foot=ttk.Frame(self.root,padding=(14,0,14,10));foot.pack(fill='x');ttk.Label(foot,textvariable=self.status).pack(side='left');ttk.Button(foot,text='Bezárás',command=self.close).pack(side='right');self.root.protocol('WM_DELETE_WINDOW',self.close);self.characters();self.root.after(100,self.poll)
 def tree(self,f,cols,name):
    t=ttk.Treeview(f,columns=cols,show='headings');v=ttk.Scrollbar(f,orient='vertical',command=t.yview);h=ttk.Scrollbar(f,orient='horizontal',command=t.xview);t.configure(yscrollcommand=v.set,xscrollcommand=h.set);v.pack(side='right',fill='y');h.pack(side='bottom',fill='x');t.pack(fill='both',expand=True)
    for i,c in enumerate(cols):t.heading(c,text=c,command=lambda j=i:self.order(name,j));t.column(c,width=260 if c in ('Terület','Forrás','Honnan','Hová','Bizonyosság','Labirintus') else 105,minwidth=65)
    return t
 def order(self,name,i):
    rev=not self.sort.get((name,i),True);self.sort[(name,i)]=rev;self.data[name].sort(key=lambda r:(isinstance(r[i],str) or r[i] is None,str(r[i]) if r[i] is None else r[i]),reverse=rev);self.fill(name)
 def fill(self,name):
    t=self.trees[name];t.delete(*t.get_children());
    for r in self.data.get(name,[]):t.insert('', 'end',values=r)
 def characters(self):
    old=self.char.get();self.ids={f'{n} (#{c})':c for c,n in self.db.execute('SELECT cid,name FROM rounds r WHERE turn=(SELECT max(turn) FROM rounds WHERE cid=r.cid) ORDER BY name')};self.char['values']=list(self.ids);self.char.set(old if old in self.ids else next(iter(self.ids),''));self.refresh()
 def reset(self):self.lo.set('');self.hi.set('');self.refresh()
 def refresh(self):
    try:
        a=int(self.lo.get() or 0);b=int(self.hi.get() or 999999999)
        if a<0 or b<a:raise ValueError()
    except ValueError:messagebox.showerror('Szűrés','Érvénytelen fordulótartomány');return
    rows=[(t,d,x,y,zone(x,y,self.zones),l,s,m) for t,d,x,y,l,s,m in self.db.execute('SELECT turn,date,x,y,lab,source,method FROM rounds WHERE cid=? AND turn BETWEEN ? AND ? ORDER BY turn',(self.ids.get(self.char.get(),-1),a,b))];self.rows=rows;sp=spans(rows);changes=[];missing=[]
    for p,r in zip(rows,rows[1:]):
        gap=r[0]-p[0]>1
        if gap:missing.append((p[0]+1,r[0]-1,r[0]-p[0]-1))
        if p[4]!=r[4]:changes.append((p[0],r[0],p[4],r[4],'Hiányzó fordulók között' if gap else 'Szomszédos fordulók'))
    stats=[]
    for z,n in Counter(r[4] for r in rows).most_common():
        rr=[r for r in rows if r[4]==z];ss=[s for s in sp if s[0]==z];stats.append((z,n,rr[0][0],rr[-1][0],len(ss),max(s[3] for s in ss),len({(r[2],r[3]) for r in rr if r[2] is not None}),round(100*n/len(rows),2)))
    self.data=dict(zip(self.trees,[rows,changes,sp,stats,missing]));self.summary.config(text=f'{len(rows)} forduló   |   {len(stats)} terület   |   {len(changes)} megfigyelt váltás   |   {sum(r[2] for r in missing)} hiányzó forduló');[self.fill(n) for n in self.trees];self.draw();self.mapview.refresh()
 def draw(self):
    c=self.canvas;c.delete('all');rows=getattr(self,'rows',[]);w=max(c.winfo_width(),300);c.create_text(20,20,anchor='nw',fill=FG,text='Fordulóvégi területek – a szürke sáv hiányzó adatot jelöl');
    if not rows:return
    rows=sorted(rows);a,b=rows[0][0],rows[-1][0];scale=(w-40)/(b-a+1);palette=['#427f72','#426d9b','#a48749','#765d9b','#39899b','#a65e44','#537e98'];names=list(dict.fromkeys(r[4] for r in rows));colors={n:palette[i%len(palette)] for i,n in enumerate(names)};c.create_rectangle(20,60,w-20,105,fill='#49515b',outline='')
    for z,l,h,n in spans(rows):c.create_rectangle(20+(l-a)*scale,60,20+(h-a+1)*scale,105,fill=colors[z],outline='')
    c.create_text(20,120,anchor='nw',fill=FG,text=str(a));c.create_text(w-20,120,anchor='ne',fill=FG,text=str(b))
    for i,n in enumerate(names):x=20+(i%3)*(w-40)/3;y=155+(i//3)*27;c.create_rectangle(x,y,x+13,y+13,fill=colors[n],outline='');c.create_text(x+20,y,anchor='nw',fill=FG,text=n)
 def folder(self):
    p=filedialog.askdirectory();
    if p:self.start([Path(p)])
 def files(self):
    p=filedialog.askopenfilenames(filetypes=[('TF fordulók','*.html *.htm *.mhtml *.mht *.zip'),('Minden fájl','*')]);
    if p:self.start(list(map(Path,p)))
 def start(self,paths):
    if self.busy:return
    self.busy=True;[b.configure(state='disabled') for b in self.buttons];self.status.set('Dolgozom…');threading.Thread(target=self.worker,args=(paths,),daemon=True).start()
 def worker(self,paths):
    db=connect(ROOT/'journal.sqlite3');added=dup=0;errors=[]
    try:
        files=[f for p in paths for f in (p.rglob('*') if p.is_dir() else [p]) if f.is_file() and f.suffix.lower() in EXT]
        for i,p in enumerate(files):
            try:
                for raw,src in records(p):
                    try:
                        r=parse(raw,src);old=db.execute('SELECT date,direct_x,direct_y,lab FROM rounds WHERE cid=? AND turn=?',(r[0],r[2])).fetchone()
                        if old:
                            dup+=1
                            db.execute('UPDATE rounds SET direct_x=coalesce(direct_x,?),direct_y=coalesce(direct_y,?),start_x=coalesce(start_x,?),start_y=coalesce(start_y,?),move_x=coalesce(move_x,?),move_y=coalesce(move_y,?) WHERE cid=? AND turn=?',(*r[8:14],r[0],r[2]))
                            if old[1] is not None and r[4] is not None and tuple(old[1:3])!=r[4:6]:errors.append(src+': eltérő duplikátum, korábbi adat megőrizve')
                        else:db.execute('INSERT INTO rounds (cid,name,turn,date,x,y,lab,source,direct_x,direct_y,start_x,start_y,move_x,move_y) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)',r);added+=1
                    except Exception as e:errors.append(src+': '+str(e))
            except Exception as e:errors.append(str(p)+': '+str(e))
            self.q.put(('progress',f'Dolgozom… {i+1}/{len(files)} fájl'))
        resolve(db);db.commit()
    except Exception as e:errors.append(str(e));db.rollback();added=0
    finally:db.close();self.q.put(('done',(added,dup,errors)))
 def poll(self):
    try:
        while True:
            k,v=self.q.get_nowait()
            if k=='progress':self.status.set(v)
            else:
                self.busy=False;[b.configure(state='normal') for b in self.buttons];a,d,e=v;self.characters();self.status.set(f'Import: {a} új, {d} ismételt, {len(e)} jelzés');(ROOT/'import.log').write_text('\n'.join(e),encoding='utf8');messagebox.showinfo('Importálás',self.status.get()+ ('\nRészletek: import.log' if e else ''))
    except queue.Empty:pass
    self.root.after(100,self.poll)
 def edit(self):
    win=tk.Toplevel(self.root);win.title('Területszerkesztő');win.geometry('800x560');win.configure(bg=BG);win.transient(self.root);win.grab_set();zs=[list(z) for z in self.zones];f=ttk.Frame(win);f.pack(fill='both',expand=True);t=self.tree(f,['Név','Min X','Max X','Min Y','Max Y'],'editor')
    for c in t['columns']:t.heading(c,command=lambda:None)
    def reload():
        t.delete(*t.get_children());[t.insert('', 'end',iid=str(i),values=z) for i,z in enumerate(zs)]
    def change(add=False):
        sel=t.selection();i=None if add else int(sel[0]) if sel else None
        if not add and i is None:return
        old=zs[i] if i is not None else ['',0,0,0,0];vals=[]
        for j,label in enumerate(['Név','Min X','Max X','Min Y','Max Y']):
            v=simpledialog.askstring('Terület',label,initialvalue=str(old[j]),parent=win)
            if v is None:return
            try:vals.append(v.strip() if j==0 else int(v))
            except ValueError:messagebox.showerror('Hiba','Egész szám szükséges',parent=win);return
        if i is None:zs.append(vals)
        else:zs[i]=vals
        reload()
    def delete():
        for i in sorted(map(int,t.selection()),reverse=True):zs.pop(i)
        reload()
    def save():
        try:validate(zs);p=ROOT/'zones.json';tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(zs,ensure_ascii=False,indent=2),encoding='utf8');tmp.replace(p);self.zones=zs;self.refresh();win.destroy()
        except Exception as e:messagebox.showerror('Hiba',str(e),parent=win)
    bar=ttk.Frame(win);bar.pack(fill='x');
    for n,fn in [('Új',lambda:change(True)),('Módosítás',change),('Törlés',delete),('Mentés',save),('Mégse',win.destroy)]:ttk.Button(bar,text=n,command=fn).pack(side='left',padx=4,pady=8)
    reload()
 def export(self,xlsx):
    name=self.nb.tab(self.nb.select(),'text');name='Időszakok' if name=='Idővonal' else 'Fordulók' if name=='Térkép' else name;ext='.xlsx' if xlsx else '.csv';p=filedialog.asksaveasfilename(defaultextension=ext,filetypes=[(ext,'*'+ext)],initialfile='TF_Journal_'+name+ext)
    if not p:return
    try:
        if xlsx:
            from openpyxl import Workbook
            from openpyxl.styles import Font,PatternFill
            from openpyxl.utils import get_column_letter
            wb=Workbook();wb.remove(wb.active)
            for n,t in self.trees.items():
                ws=wb.create_sheet(n);ws.append(list(t['columns']));[ws.append(list(r)) for r in self.data[n]];ws.freeze_panes='A2';ws.auto_filter.ref=ws.dimensions
                for cell in ws[1]:cell.font=Font(bold=True,color='FFFFFF');cell.fill=PatternFill('solid',fgColor='293749')
                for i,col in enumerate(ws.columns,1):ws.column_dimensions[get_column_letter(i)].width=min(70,max(12,max(len(str(c.value or '')) for c in col)+2))
            wb.save(p)
        else:
            with open(p,'w',encoding='utf-8-sig',newline='') as f:w=csv.writer(f,delimiter=';');w.writerow(self.trees[name]['columns']);w.writerows(self.data[name])
        self.status.set('Exportálva: '+p)
    except Exception as e:messagebox.showerror('Exportálási hiba',str(e))
 def close(self):
    if self.busy:messagebox.showinfo('Importálás','Várd meg az importálás végét.');return
    self.db.close();self.root.destroy()
if __name__=='__main__':App().root.mainloop()
