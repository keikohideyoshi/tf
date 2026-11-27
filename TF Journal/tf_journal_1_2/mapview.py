import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from collections import defaultdict
import math
class MapView:
 def __init__(self,parent,app):
    self.app=app;self.frame=ttk.Frame(parent);self.mode=tk.StringVar(value='Hőtérkép');self.area=tk.StringVar(value='Teljes világ');self.minimum=tk.StringVar(value='1');self.estimated=tk.BooleanVar(value=False);self.step=tk.DoubleVar(value=0);self.playing=False;self.job=None;self.zoom=1;self.pan=[0,0];self.drag=None;self.rows=[];self.hit=[]
    bar=ttk.Frame(self.frame);bar.pack(fill='x');
    for var,values,width in [(self.mode,['Hőtérkép','Táborhelyek','Útvonal','Visszajátszás'],17),(self.area,['Teljes világ'],24)]:
        cb=ttk.Combobox(bar,textvariable=var,values=values,state='readonly',width=width);cb.pack(side='left',padx=3);cb.bind('<<ComboboxSelected>>',lambda e:self.reset());
        if var is self.area:self.areas=cb
    ttk.Label(bar,text='Min. gyakoriság').pack(side='left');en=ttk.Entry(bar,textvariable=self.minimum,width=5);en.pack(side='left');en.bind('<Return>',lambda e:self.draw());ttk.Button(bar,text='Szűrés',command=self.draw).pack(side='left');ttk.Checkbutton(bar,text='Feltételezett pontok',variable=self.estimated,command=self.draw).pack(side='left');ttk.Button(bar,text='Alaphelyzet',command=self.reset).pack(side='left');ttk.Button(bar,text='PNG',command=self.png).pack(side='left')
    self.canvas=tk.Canvas(self.frame,bg='#10151e',highlightthickness=0);self.canvas.pack(fill='both',expand=True);self.canvas.bind('<Configure>',lambda e:self.draw());self.canvas.bind('<Button-1>',self.down);self.canvas.bind('<B1-Motion>',self.move);self.canvas.bind('<ButtonRelease-1>',self.up);self.canvas.bind('<MouseWheel>',lambda e:self.wheel(e,1 if e.delta>0 else -1));self.canvas.bind('<Button-4>',lambda e:self.wheel(e,1));self.canvas.bind('<Button-5>',lambda e:self.wheel(e,-1))
    self.story=tk.Frame(self.frame,bg='#192230',padx=12,pady=5);self.story.pack(fill='x')
    self.when=tk.Label(self.story,bg='#192230',fg='#d6b579',font=('Sans',16,'bold'),anchor='w');self.when.pack(side='left')
    self.level=tk.Label(self.story,bg='#192230',fg='#d6b579',font=('Sans',19,'bold'),padx=12);self.level.pack(side='right')
    self.where=tk.Label(self.story,bg='#192230',fg='#b9c8d6',anchor='w');self.where.pack(side='left',padx=18)
    self.graph=tk.Canvas(self.frame,height=65,bg='#10151e',highlightthickness=0);self.graph.pack(fill='x');self.graph.bind('<Configure>',lambda e:self.timeline())
    bottom=ttk.Frame(self.frame);bottom.pack(fill='x');self.slider=ttk.Scale(bottom,from_=0,to=1,variable=self.step,command=lambda v:self.draw());self.slider.pack(side='left',fill='x',expand=True);ttk.Button(bottom,text='Lejátszás / szünet',command=self.play).pack(side='left');self.speed=tk.StringVar(value='250');ttk.Combobox(bottom,textvariable=self.speed,values=['100','250','500','1000'],width=6,state='readonly').pack(side='left');ttk.Button(bottom,text='TOP 20',command=self.top).pack(side='left');self.info=ttk.Label(self.frame,text='');self.info.pack(fill='x')
 def refresh(self):
    self.stop()
    self.rows=sorted(self.app.rows,key=lambda r:r[0]);self.areas['values']=['Teljes világ']+[z[0] for z in self.app.zones];self.slider.configure(to=max(0,len(self.rows)-1));self.step.set(max(0,len(self.rows)-1));self.draw()
 def timeline(self):
    g=self.graph;g.delete('all');rows=self.rows;w=max(80,g.winfo_width());n=len(rows)
    if not n:
        self.when.config(text='Nincs forduló');self.level.config(text='Szint: –');self.where.config(text='');return
    i=max(0,min(n-1,int(self.step.get())));r=rows[i];lv=r[9];prev=rows[i-1] if i else None
    delta=lv-prev[9] if prev and lv is not None and prev[9] is not None and prev[0]+1==r[0] else 0
    self.when.config(text=f'{r[1] or "Ismeretlen dátum"}  {r[8] or ""}');self.where.config(text=f'{r[0]}. forduló  |  {r[4]}  |  '+(f'{r[2]},{r[3]}' if r[2] is not None else '–'))
    self.level.config(text=f'Szint: {lv if lv is not None else "–"}'+(f'  ▲ +{delta}' if delta>0 else ''),fg='#65c5a5' if delta>0 else '#d6b579')
    vals=[p[9] for p in rows if p[9] is not None];lo=min(vals,default=0);hi=max(vals,default=1);x=lambda j:12+j*(w-24)/max(1,n-1);y=lambda v:43-30*(v-lo)/max(1,hi-lo)
    lastyear=None;lastlabel=-100
    for j,p in enumerate(rows):
        year=p[1][:4] if p[1] else None
        if year and year!=lastyear:
            if x(j)-lastlabel>=45:g.create_text(x(j),55,text=year,fill='#aebccc',anchor='w' if j==0 else 'center',font=('Sans',8));lastlabel=x(j)
            lastyear=year
        if p[9] is None:continue
        if j and rows[j-1][9] is not None and rows[j-1][0]+1==p[0]:
            old=rows[j-1][9];g.create_line(x(j-1),y(old),x(j),y(old),x(j),y(p[9]),fill='#d6b579');
            if p[9]>old:g.create_oval(x(j)-2,y(p[9])-2,x(j)+2,y(p[9])+2,fill='#65c5a5',outline='')
        else:g.create_oval(x(j)-1,y(p[9])-1,x(j)+1,y(p[9])+1,fill='#d6b579',outline='')
    g.create_line(x(i),2,x(i),47,fill='#65c5a5',dash=(2,2))
    if lv is not None:g.create_oval(x(i)-4,y(lv)-4,x(i)+4,y(lv)+4,fill='#65c5a5',outline='white')
 def reset(self):self.zoom=1;self.pan=[0,0];self.draw()
 def filtered(self):
    rows=self.rows[:int(self.step.get())+1] if self.mode.get()=='Visszajátszás' else self.rows
    return [r for r in rows if r[2] is not None and r[3] is not None and (self.estimated.get() or r[7]!='Korábbi táborhely') and (self.area.get()=='Teljes világ' or r[4]==self.area.get())]
 def groups(self):
    g=defaultdict(list)
    for r in self.filtered():g[r[2],r[3]].append(r)
    try:m=max(1,int(self.minimum.get()))
    except ValueError:m=1
    return {p:r for p,r in g.items() if len(r)>=m}
 def draw(self):
    self.timeline()
    c=self.canvas;c.delete('all');w=max(1,c.winfo_width());h=max(1,c.winfo_height());zs=self.app.zones;sel=[z for z in zs if z[0]==self.area.get()] or zs
    if not sel:return
    a=min(z[1] for z in sel);b=max(z[2] for z in sel);d=min(z[3] for z in sel);e=max(z[4] for z in sel);scale=max(.01,min((w-50)/(b-a+1),(h-70)/(e-d+1)))*self.zoom;ox=w/2-(a+b)/2*scale+self.pan[0];oy=h/2-(d+e)/2*scale+self.pan[1];self.transform=(scale,ox,oy);xy=lambda x,y:(ox+x*scale,oy+y*scale)
    palette=['#28485c','#28564d','#5c5030','#493d62','#285563','#653e32']
    for i,(n,x1,x2,y1,y2) in enumerate(zs):
        c.create_rectangle(*xy(x1-.5,y1-.5),*xy(x2+.5,y2+.5),fill=palette[i%6],outline='#8495a5');c.create_text(*xy((x1+x2)/2,(y1+y2)/2),text=n,fill='#dce5ed',width=max(30,(x2-x1+1)*scale-4),font=('Sans',9))
    g=self.groups();self.hit=[];mode=self.mode.get();rows=self.filtered()
    if mode in ('Útvonal','Visszajátszás'):
        for p,r in zip(rows,rows[1:]):
            if r[0]==p[0]+1 and (p[2],p[3]) in g and (r[2],r[3]) in g:c.create_line(*xy(p[2],p[3]),*xy(r[2],r[3]),fill='#d6b579',dash=(3,3))
    colors=['#50d9f4','#65c5a5','#ffdc42','#ffa52e','#ff7135','#ff3425']
    for (x,y),rr in sorted(g.items(),key=lambda v:len(v[1])):
        n=len(rr);px,py=xy(x,y);k=sum(n>=v for v in (2,6,11,26,51));rad=min(22,3+math.sqrt(n)*1.5);color=colors[k] if mode=='Hőtérkép' else '#65c5a5';c.create_oval(px-rad,py-rad,px+rad,py+rad,fill=color,outline='#10151e');self.hit.append((px,py,rad,(x,y),rr))
    c.create_text(10,10,anchor='nw',fill='#d6b579',text='1 · 2–5 · 6–10 · 11–25 · 26–50 · 51+ forduló' if mode=='Hőtérkép' else 'A vonalak csak egymást követő ismert végpozíciókat jelölnek.');self.info.configure(text=f'{len(g)} táborhely | {sum(map(len,g.values()))} forduló | maximum: {max(map(len,g.values()),default=0)}'+(f' | {self.rows[min(int(self.step.get()),len(self.rows)-1)][0]}. forduló' if mode=='Visszajátszás' and self.rows else ''))
 def down(self,e):self.drag=(e.x,e.y,*self.pan)
 def move(self,e):
    if self.drag:self.pan=[self.drag[2]+e.x-self.drag[0],self.drag[3]+e.y-self.drag[1]];self.draw()
 def up(self,e):
    if self.drag and abs(e.x-self.drag[0])+abs(e.y-self.drag[1])<5:
        hits=[v for v in self.hit if math.hypot(e.x-v[0],e.y-v[1])<=v[2]+3]
        if hits:
            _,_,_,p,rr=min(hits,key=lambda v:math.hypot(e.x-v[0],e.y-v[1]));self.details(p,rr)
    self.drag=None
 def wheel(self,e,d):
    old=self.zoom;self.zoom=max(.5,min(100,old*1.25**d));f=self.zoom/old;self.pan=[e.x-self.canvas.winfo_width()/2+(self.pan[0]-(e.x-self.canvas.winfo_width()/2))*f,e.y-self.canvas.winfo_height()/2+(self.pan[1]-(e.y-self.canvas.winfo_height()/2))*f];self.draw()
 def details(self,p,rr):
    win=tk.Toplevel(self.frame);win.title(f'{p[0]},{p[1]} – {rr[0][4]}');win.geometry('650x400');ttk.Label(win,text=f'{len(rr)} forduló | első: {rr[0][0]} | utolsó: {rr[-1][0]}').pack();t=tk.Text(win,bg='#1c2533',fg='#e0e6ef');t.pack(fill='both',expand=True);t.insert('end','\n'.join(f'{r[0]}. forduló  {r[1]}  {r[7]}' for r in rr));t.configure(state='disabled')
 def top(self):
    g=self.groups();messagebox.showinfo('TOP 20','\n'.join(f'{i}. {p[0]},{p[1]} – {rr[0][4]}: {len(rr)} forduló' for i,(p,rr) in enumerate(sorted(g.items(),key=lambda v:-len(v[1]))[:20],1)) or 'Nincs adat')
 def stop(self):
    self.playing=False
    if self.job is not None:self.frame.after_cancel(self.job);self.job=None
 def play(self):
    if not self.rows:return
    if self.playing:self.stop();return
    self.playing=True
    if self.playing:
        self.mode.set('Visszajátszás');self.step.set(0 if self.step.get()>=len(self.rows)-1 else self.step.get());self.tick()
 def tick(self):
    self.job=None
    if not self.playing:return
    self.draw()
    if self.step.get()>=len(self.rows)-1:self.playing=False;return
    self.step.set(int(self.step.get())+1);self.job=self.frame.after(int(self.speed.get()),self.tick)
 def png(self):
    p=filedialog.asksaveasfilename(defaultextension='.png',filetypes=[('PNG','*.png')]);
    if not p:return
    try:
        from PIL import Image
        import io
        im=Image.open(io.BytesIO(self.canvas.postscript(colormode='color').encode()));im.load();im.save(p)
    except Exception as e:messagebox.showerror('PNG export','Pillow és Ghostscript szükséges: '+str(e))
