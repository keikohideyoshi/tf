import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
import threading, webbrowser, re, csv, sqlite3, os, subprocess, shutil, sys, time
from core import conn, import_folder, reindex_all, list_turn_files, search_turns, search_turns_advanced, search_text_parallel, stats
from object_search import catalog, search_objects, search_item_events, KINDS
from rounded_button import RoundedButton
from battle_search import search_battles
from natural_search import fallback, online_plan, run, validate, _entity_from_question, apply_selected_object, reconcile_ai_plan
import local_ai
import ollama_service
from search_diagnostics import SearchTrace, LOG

BG='#151a24'; PANEL='#202838'; FG='#edf1f8'; MUTED='#a6b2c6'; ACC='#65c8b3'
class GUI:
 def __init__(self):
  self.root=tk.Tk();self.root.title('TF Fordulókereső 1.9.7.10');self.root.geometry('1200x800');self.root.minsize(850,550);self.root.configure(bg=BG)
  self.c=conn();self.busy=False;self.rows=[];self.timer=None;self.column_sort=None;self.column_desc=False;self.selected_object=None;self.search_generation=0;self.searching=False;self.imported_since_search=False
  style=ttk.Style();style.theme_use('clam')
  style.configure('Treeview',background=PANEL,foreground=FG,fieldbackground=PANEL,rowheight=34,borderwidth=0)
  style.map('Treeview',background=[('selected','#316b78')]);style.configure('Treeview.Heading',background='#344052',foreground=FG)
  # Tk Menu + Menubutton: a teljes legordulo lista sotetre szinezheto,
  # es nem fugg a ttk Combobox temafuggo popdown implementaciojatol.
  style.configure('TF.Horizontal.TProgressbar',troughcolor=PANEL,background=ACC)
  head=tk.Frame(self.root,bg=BG);head.pack(fill='x',padx=20,pady=(14,7))
  tk.Label(head,text='TF  /  FORDULÓKERESŐ',bg=BG,fg=ACC,font=('DejaVu Sans',20,'bold')).pack(anchor='w')
  nav=tk.Frame(self.root,bg=BG);nav.pack(fill='x',padx=20,pady=(0,6))
  tk.Label(nav,text='Keresési felület:',bg=BG,fg=MUTED).pack(side='left')
  self.search_ui_mode=tk.StringVar(value='Kulcsszavas keresés')
  _,ui_menu=self.make_dropdown(nav,self.search_ui_mode,24)
  self.set_menu_values(ui_menu,self.search_ui_mode,['Kulcsszavas keresés','Szabad kérdés'],callback=self.switch_search_mode)
  RoundedButton(nav,text='Adatbázis-kezelő',command=self.open_database_manager).pack(side='left',padx=10)
  RoundedButton(nav,text='AI beállítások',command=self.configure_ai).pack(side='left')
  self.diagnostics_enabled=tk.BooleanVar(value=False)
  tk.Checkbutton(nav,text='Keresési diagnosztika',variable=self.diagnostics_enabled,bg=BG,fg=FG,selectcolor=PANEL,activebackground=BG,activeforeground=FG).pack(side='left',padx=12)
  RoundedButton(nav,text='Naplómappa',command=self.open_diagnostics_folder).pack(side='left')
  bar=tk.Frame(self.root,bg=BG);bar.pack(fill='x',padx=20,pady=9)
  self.keyword_frames=[bar]

  self.q=tk.StringVar();self.q.trace_add('write',self.schedule_search)
  tk.Label(bar,text='Kulcsszavas keresés:',bg=BG,fg=MUTED).pack(side='left',padx=(0,8))
  self.entry=tk.Entry(bar,textvariable=self.q,bg=PANEL,fg=FG,insertbackground=FG,relief='flat',font=('DejaVu Sans',12))
  self.entry.pack(side='left',fill='x',expand=True,ipady=9,padx=(0,8))
  self.char=tk.StringVar(value='Minden karakter')
  self.cbchar,self.charmenu=self.make_dropdown(bar,self.char,30)
  self.mode=tk.StringVar(value='Pontos kifejezés')
  self.cbmode,self.modemenu=self.make_dropdown(bar,self.mode,20)
  self.set_menu_values(self.modemenu,self.mode,['Pontos kifejezés','Intelligens keresés','Objektumkeresés','Harci események'])
  self.sort=tk.StringVar(value='Karakter / forduló')
  self.cbsort,self.sortmenu=self.make_dropdown(bar,self.sort,23)
  self.set_menu_values(self.sortmenu,self.sort,['Karakter / forduló','Legtöbb előfordulás','Legnagyobb fordulószám'])
  # Külön kérdésmező: a meglévő keresőmódok változatlanul működnek.
  askbar=tk.Frame(self.root,bg=BG);askbar.pack(fill='x',padx=20,pady=(2,8));self.question_frames=[askbar]
  tk.Label(askbar,text='Szabad kérdés:',bg=BG,fg=MUTED).pack(side='left',padx=(0,8))
  self.question=tk.StringVar()
  self.askentry=tk.Entry(askbar,textvariable=self.question,bg=PANEL,fg=FG,insertbackground=FG,relief='flat',font=('DejaVu Sans',11))
  self.askentry.pack(side='left',fill='x',expand=True,ipady=8,padx=(0,7))
  self.askentry.bind('<Return>',lambda _:self.ask_question())
  self.question.trace_add('write',self.invalidate_question_plan)
  self.question_object=None
  self.question_object_label=tk.StringVar(value='Nincs kiválasztva')
  objbar=tk.Frame(self.root,bg=BG);objbar.pack(fill='x',padx=20,pady=(0,7));self.question_frames.append(objbar)
  tk.Label(objbar,text='Kérdés objektuma (opcionális):',bg=BG,fg=MUTED).pack(side='left',padx=(0,8))
  tk.Label(objbar,textvariable=self.question_object_label,bg=PANEL,fg=ACC,padx=10,pady=7).pack(side='left',padx=(0,8))
  RoundedButton(objbar,text='Tárgy / szörny kiválasztása',command=self.choose_question_object).pack(side='left',padx=(0,7))
  RoundedButton(objbar,text='Objektum törlése',command=self.clear_question_object).pack(side='left')
  self.askbtn=RoundedButton(askbar,text='1. Kérdés értelmezése',tone='search',command=self.ask_question);self.askbtn.pack(side='left',padx=(0,7))
  self.aiconfig=RoundedButton(askbar,text='AI beállítások',command=self.configure_ai) # felső navigációban
  self.ai_key='';self.ai_model='';self.ai_enabled=False;self.ask_generation=0;self.local_model=local_ai.DEFAULT_MODEL;self.local_ai_enabled=True
  self.ai_status=tk.StringVar(value='AI ellenőrzése…')
  tk.Label(askbar,textvariable=self.ai_status,bg=BG,fg=ACC).pack(side='left',padx=6)
  self.root.after(200,self.refresh_ai_status)
  self.review=tk.Frame(self.root,bg=PANEL);self.review.pack(fill='x',padx=20,pady=(0,8));self.question_frames.append(self.review)
  self.review_widgets=[];self.pending_plan=None;self.pending_question=None
  self.review_status=tk.StringVar(value='Először értelmezd a kérdést. A keresés csak jóváhagyás után indul.')
  tk.Label(self.review,textvariable=self.review_status,bg=PANEL,fg=ACC,wraplength=1080,justify='left').pack(anchor='w',padx=10,pady=5)
  self.review_controls=tk.Frame(self.review,bg=PANEL);self.review_controls.pack(fill='x',padx=8)
  self.runbtn=RoundedButton(self.review,text='2. Keresés indítása',tone='search',command=self.execute_question);self.runbtn.pack(anchor='e',padx=8,pady=6)
  self.runbtn.configure(state='disabled')
  question_actions=tk.Frame(self.root,bg=BG);question_actions.pack(fill='x',padx=20,pady=(0,6));self.question_frames.append(question_actions)
  RoundedButton(question_actions,text='Találatok exportálása',tone='export',command=self.export_results).pack(side='left',padx=(0,8))
  RoundedButton(question_actions,text='Alaphelyzet',tone='reset',command=self.reset_filters).pack(side='left')
  actions=tk.Frame(self.root,bg=BG);actions.pack(fill='x',padx=20,pady=(3,8));self.keyword_frames.append(actions);self.buttons=[]
  for icon,name,fn in [('book','Objektum kiválasztása',self.choose_object),('external','Forduló megnyitása',self.open_source),('download','Találatok exportálása',self.export_results)]:
   b=RoundedButton(actions,text=name,command=fn,tone='export' if name=='Találatok exportálása' else 'neutral')
   b.pack(side='left',padx=(0,7));self.buttons.append(b)
  self.resetbtn=RoundedButton(actions,text='Alaphelyzet',tone='reset',command=self.reset_filters)
  self.resetbtn.pack(side='left',padx=(0,7));self.buttons.append(self.resetbtn)
  eventbar=tk.Frame(self.root,bg=BG);eventbar.pack(fill='x',padx=20,pady=(0,8));self.keyword_frames.append(eventbar)
  tk.Label(eventbar,text='Tárgyesemény:',bg=BG,fg=MUTED).pack(side='left',padx=(0,9))
  self.event_mode=tk.StringVar(value='Összes említés')
  self.event_dropdown,self.event_menu=self.make_dropdown(eventbar,self.event_mode,25)
  self.set_menu_values(self.event_menu,self.event_mode,['Összes említés','Megszereztem','Használtam','Alkímiáztam'])
  tk.Label(eventbar,text='Csak tárgyaknál; kizárólag egyértelmű szövegminták',bg=BG,fg=MUTED).pack(side='left',padx=12)

  battlebar=tk.Frame(self.root,bg=BG);battlebar.pack(fill='x',padx=20,pady=(0,8));self.keyword_frames.append(battlebar)
  tk.Label(battlebar,text='Harci eredmény:',bg=BG,fg=MUTED).pack(side='left')
  self.battle_outcome=tk.StringVar(value='Halál')
  _,battle_menu=self.make_dropdown(battlebar,self.battle_outcome,18)
  self.set_menu_values(battle_menu,self.battle_outcome,['Összes harc','Győzelem','Menekülés','Halál','Ismeretlen'])
  tk.Label(battlebar,text='Időszak:',bg=BG,fg=MUTED).pack(side='left',padx=(12,0))
  self.battle_period=tk.StringVar(value='Utolsó 100 forduló')
  _,period_menu=self.make_dropdown(battlebar,self.battle_period,22)
  self.set_menu_values(period_menu,self.battle_period,['Utolsó 50 forduló','Utolsó 100 forduló','Utolsó 200 forduló','Összes importált forduló'])
  tk.Label(battlebar,text='Szörny: választható az Objektum kiválasztása gombbal; üres kereső = minden szörny.',bg=BG,fg=MUTED).pack(side='left',padx=8)

  importbar=tk.Frame(self.root,bg=BG);self.importbar=importbar
  tk.Label(importbar,text='Importálás feldolgozófolyamatai:',bg=BG,fg=MUTED).pack(side='left',padx=(0,8))
  self.import_workers=tk.StringVar(value='Automatikus')
  self.search_workers=tk.StringVar(value='Automatikus')
  _,workers_menu=self.make_dropdown(importbar,self.import_workers,17)
  self.set_menu_values(workers_menu,self.import_workers,['Automatikus','1','2','4','6','12'])
  tk.Label(importbar,text='Több mag • kötegelt adatbázis-írás • változatlan fájlok kihagyása',bg=BG,fg=MUTED).pack(side='left',padx=12)
  progress=tk.Frame(self.root,bg=BG);self.importprogress=progress
  self.progress=ttk.Progressbar(progress,style='TF.Horizontal.TProgressbar',maximum=100,mode='determinate');self.progress.pack(side='left',fill='x',expand=True)
  self.percent=tk.Label(progress,text='0%',bg=BG,fg=MUTED,width=6);self.percent.pack(side='right')
  frame=tk.Frame(self.root,bg=BG);frame.pack(fill='both',expand=True,padx=20,pady=(0,8))
  cols=('character','turn','count','type','snippet');self.tree=ttk.Treeview(frame,columns=cols,show='headings')
  for key,title,width in [('character','Karakter',230),('turn','Forduló',95),('count','Előfordulás',110),('type','Egyezés',115),('snippet','Szövegkörnyezet (első találat)',690)]:
   self.tree.heading(key,text=title,**({'command':(lambda k=key:self.sort_by_column(k))} if key in ('turn','count') else {}));self.tree.column(key,width=width,stretch=key=='snippet',anchor='center' if key in ('turn','count') else 'w')
  self.tree.pack(side='left',fill='both',expand=True);sc=ttk.Scrollbar(frame,orient='vertical',command=self.tree.yview);sc.pack(side='right',fill='y');self.tree.configure(yscrollcommand=sc.set)
  self.tree.bind('<<TreeviewSelect>>',self.details);self.tree.bind('<Double-1>',lambda _:self.open_source())
  self.info=tk.Text(self.root,height=10,bg=PANEL,fg=FG,relief='flat',wrap='word',font=('DejaVu Sans',10),padx=10,pady=8)
  self.info.pack(fill='x',padx=20,pady=(0,7));self.info.tag_configure('match',background='#d6a64b',foreground='#151a24');self.info.configure(state='disabled')
  footer=tk.Frame(self.root,bg=BG);footer.pack(fill='x',padx=20,pady=(0,12))
  self.status=tk.Label(footer,bg=BG,fg=MUTED,anchor='w');self.status.pack(side='left',fill='x',expand=True)
  self.closebtn=RoundedButton(footer,text='Bezárás',tone='close',command=self.close);self.closebtn.pack(side='right')
  self.root.protocol('WM_DELETE_WINDOW',self.close)
  self.refresh_chars();self.switch_search_mode();self.refresh();self.entry.focus_set()
 def refresh_ai_status(self):
  def worker():
   ok=local_ai.ready(self.local_model)
   label=('AI aktív' if ok and self.local_ai_enabled else 'AI kikapcsolva' if not self.local_ai_enabled else 'Hagyományos keresés')
   try:self.root.after(0,lambda:self.ai_status.set(label))
   except RuntimeError:pass
  threading.Thread(target=worker,daemon=True).start()
 def configure_ai(self):
  win=tk.Toplevel(self.root);win.title('AI funkciók – helyi Ollama');win.geometry('730x580');win.configure(bg=BG);win.transient(self.root)
  tk.Label(win,text='Helyi AI – Ollama',bg=BG,fg=ACC,font=('DejaVu Sans',15,'bold')).pack(anchor='w',padx=18,pady=(15,7))
  tk.Label(win,text='A modell kizárólag a kérdés szövegét kapja meg. Az adatbázis helyben marad.',bg=BG,fg=FG,wraplength=670,justify='left').pack(anchor='w',padx=18)
  enabled=tk.BooleanVar(value=self.local_ai_enabled)
  tk.Checkbutton(win,text='Automatikus helyi AI-értelmezés, ha a modell elérhető',variable=enabled,bg=BG,fg=FG,selectcolor=PANEL,activebackground=BG,activeforeground=FG).pack(anchor='w',padx=18,pady=10)
  tk.Label(win,text='Ollama modell (alapértelmezés: qwen3:1.7b):',bg=BG,fg=FG).pack(anchor='w',padx=18)
  model=tk.Entry(win,bg=PANEL,fg=FG,insertbackground=FG,relief='flat');model.insert(0,self.local_model);model.pack(fill='x',padx=18,pady=5,ipady=6)
  state=tk.StringVar(value='Állapot ellenőrzése…')
  tk.Label(win,textvariable=state,bg=BG,fg=ACC,wraplength=670,justify='left').pack(anchor='w',padx=18,pady=6)
  log=tk.Text(win,height=10,bg=PANEL,fg=FG,relief='flat',wrap='word');log.pack(fill='both',expand=True,padx=18,pady=6)
  def append(line):
   if not win.winfo_exists():return
   log.insert('end',line+'\n');log.see('end')
  start_button=None
  def check():
   def worker():
    try:
     names=local_ai.models();msg='Ollama működik. Telepített modellek: '+(', '.join(names) if names else '(nincs)')
    except Exception:msg='Ollama nem érhető el a 127.0.0.1:11434 címen.'
    def update():
     if not win.winfo_exists():return
     state.set(msg)
     if start_button is not None:start_button.configure(state='disabled' if msg.startswith('Ollama működik.') else 'normal')
    self.root.after(0,update)
   threading.Thread(target=worker,daemon=True).start()
  def start_ollama():
   if start_button is not None:start_button.configure(state='disabled')
   state.set('Ollama indítása folyamatban…')
   append('Ollama indítása…')
   def worker():
    result, detail=ollama_service.start()
    def finish():
     if not win.winfo_exists():return
     append(detail)
     if result=='missing':
      messagebox.showwarning('Ollama',detail+'\nHasználd az „Ollama telepítése” gombot.',parent=win)
     elif result=='failed':messagebox.showwarning('Ollama indítása',detail,parent=win)
     check()
     self.refresh_ai_status()
    self.root.after(0,finish)
   threading.Thread(target=worker,daemon=True).start()
  def run_command(command):
   def worker():
    try:
     proc=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,bufsize=1)
     for line in proc.stdout:
      self.root.after(0,lambda line=line:append(line.rstrip()[:400]))
     code=proc.wait()
     self.root.after(0,lambda:append('Befejezve, kilépési kód: '+str(code)))
    except Exception as exc:self.root.after(0,lambda:append('Hiba: '+str(exc)))
    self.root.after(0,check);self.root.after(0,self.refresh_ai_status)
   threading.Thread(target=worker,daemon=True).start()
  def install():
   if shutil.which('ollama'):
    messagebox.showinfo('Ollama','Az Ollama parancs már telepítve van. Ha nem fut, indítsd el az Ollama szolgáltatást.',parent=win);return
   if sys.platform.startswith('linux') and shutil.which('pacman'):
    if not messagebox.askyesno('Telepítés','A rendszer csomagkezelőjével telepítsük az Ollamát?\n\nA telepítés rendszergazdai jóváhagyást kérhet.\nA parancs: sudo pacman -S ollama',parent=win):return
    terminal=next((x for x in ('xterm','xfce4-terminal','konsole','gnome-terminal','kitty','alacritty') if shutil.which(x)),None)
    if terminal:
     command= ['sudo','pacman','-S','ollama']
     if terminal in ('xterm','xfce4-terminal','kitty','alacritty'):cmd=[terminal,'-e']+command
     elif terminal=='konsole':cmd=[terminal,'-e']+command
     else:cmd=[terminal,'--']+command
     try:subprocess.Popen(cmd);append('Megnyitottam a telepítő terminált. Telepítés után indítsd az Ollama szolgáltatást.');return
     except OSError:pass
    messagebox.showinfo('Kézi telepítés','Nyiss terminált, és futtasd:\nsudo pacman -S ollama\n\nMajd indítsd az Ollama szolgáltatást.',parent=win)
   else:
    import webbrowser
    if messagebox.askyesno('Ollama','A telepítéshez megnyissuk az Ollama hivatalos letöltési oldalát?\nhttps://ollama.com/download',parent=win):webbrowser.open('https://ollama.com/download')
  def pull():
   name=model.get().strip()
   if not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9._:/-]{0,100}',name):messagebox.showwarning('Modell','Érvénytelen modellazonosító.',parent=win);return
   if not shutil.which('ollama'):
    messagebox.showwarning('Ollama','Előbb telepítsd az Ollamát.',parent=win);return
   if not messagebox.askyesno('Modell letöltése',f'Letöltjük a(z) {name} modellt?\n\nA qwen3:1.7b körülbelül 1,4 GB.',parent=win):return
   append('Modell letöltése: '+name);run_command(['ollama','pull',name])
  def save():
   name=model.get().strip()
   if not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9._:/-]{0,100}',name):messagebox.showwarning('Modell','Érvénytelen modellazonosító.',parent=win);return
   self.local_model=name;self.local_ai_enabled=enabled.get();self.refresh_ai_status();win.destroy()
  buttons=tk.Frame(win,bg=BG);buttons.pack(fill='x',padx=18,pady=8)
  first_row=tk.Frame(buttons,bg=BG);first_row.pack(anchor='w')
  second_row=tk.Frame(buttons,bg=BG);second_row.pack(anchor='w',pady=(5,0))
  for title,action in [('Állapot ellenőrzése',check),('Ollama indítása',start_ollama),('Ollama telepítése',install),('Modell letöltése',pull),('Mentés és bezárás',save)]:
   btn=RoundedButton(first_row if title in ('Állapot ellenőrzése','Ollama indítása','Ollama telepítése') else second_row,text=title,command=action,tone='search' if title=='Mentés és bezárás' else 'neutral')
   btn.pack(side='left',padx=(0,7))
   if title=='Ollama indítása':start_button=btn
  check()
 def open_diagnostics_folder(self):
  LOG.parent.mkdir(parents=True,exist_ok=True)
  subprocess.Popen(['xdg-open',str(LOG.parent)])
 def ask_question(self):
  if self.busy:return
  question=self.question.get().strip()
  if not question:return
  m=re.search(r'#(\d+)',self.char.get());cid=int(m.group(1)) if m else None
  key=self.ai_key if self.ai_enabled else '';model=self.ai_model if self.ai_enabled else ''
  use_local=self.local_ai_enabled;local_model=self.local_model
  selected=dict(self.question_object) if self.question_object else None
  self.search_generation+=1;self.ask_generation+=1;generation=self.ask_generation
  self.pending_plan=None;self.runbtn.configure(state='disabled')
  self.status.configure(text='Kérdés értelmezése…')
  self.setinfo('A kérdés feldolgozása folyamatban. Az adatbázis helyben marad.')
  def worker():
   c=conn()
   try:
    warning='';method='Szabályalapú értelmezés'
    if use_local and local_ai.ready(local_model):
     try:
      proposal=local_ai.plan(question,local_model)
      plan=reconcile_ai_plan(question,proposal,c)
      method='Helyi Ollama AI + ellenőrzött keresési terv'
     except Exception as exc:
      warning='A helyi AI értelmezése nem használható; szabályalapú keresés. ('+str(exc)[:140]+')\n'
      plan=fallback(question,c)
    elif key:
     try:
      proposal=online_plan(question,key,model)
      plan=reconcile_ai_plan(question,proposal,c)
      method='Online AI + ellenőrzött keresési terv'
     except Exception as exc:
      warning='Az online AI értelmezése nem használható; szabályalapú keresés. ('+str(exc)[:140]+')\n'
      plan=fallback(question,c)
    else:
     try:plan=fallback(question,c)
     except ValueError:
      if not selected:raise
      plan=fallback('Mikor harcoltam?',c) if selected['kind']=='monster' else {'intent':'item','term':selected['name'],'event':'Összes említés'}
    if selected:
     plan=apply_selected_object(plan,selected)
     method+=' + kiválasztott objektum'
    self.root.after(0,lambda:self.show_question_plan(generation,plan,method,warning,question))
   except Exception as exc:
    error=str(exc);self.root.after(0,lambda:self.question_error(generation,error))
   finally:c.close()
  threading.Thread(target=worker,daemon=True).start()
 def invalidate_question_plan(self,*_):
  if not hasattr(self,'runbtn'):return
  self.ask_generation+=1
  self.pending_plan=None;self.pending_question=None
  self.runbtn.configure(state='disabled')
  self.review_status.set('A kérdés megváltozott. Értelmezd újra a keresés előtt.')
  for w in self.review_controls.winfo_children():w.destroy()
 def question_error(self,generation,error):
  if generation!=self.ask_generation:return
  self.review_status.set('Értelmezési hiba: '+error)
  self.status.configure(text='A kérdés értelmezése sikertelen.')
 def show_question_plan(self,generation,plan,method,warning,question):
  if generation!=self.ask_generation or question!=self.question.get().strip() or self.busy:return
  self.pending_plan=dict(plan);self.pending_question=question;self.plan_method=method;self.plan_warning=warning
  for w in self.review_controls.winfo_children():w.destroy()
  self.review_status.set('Értelmezés kész: '+method+'. Ellenőrizd és szükség esetén módosítsd a feltételeket!')
  self.plan_vars={}
  def dropdown(field,label,options):
   row=tk.Frame(self.review_controls,bg=PANEL);row.pack(side='left',padx=7,pady=5)
   tk.Label(row,text=label,bg=PANEL,fg=MUTED).pack(anchor='w')
   v=tk.StringVar(value=str(plan.get(field) or options[0]));self.plan_vars[field]=v
   _,menu=self.make_dropdown(row,v,19);self.set_menu_values(menu,v,options,callback=lambda:None)
  def entry(field,label):
   row=tk.Frame(self.review_controls,bg=PANEL);row.pack(side='left',padx=7,pady=5)
   tk.Label(row,text=label,bg=PANEL,fg=MUTED).pack(anchor='w')
   v=tk.StringVar(value=str(plan.get(field) or ''));self.plan_vars[field]=v
   tk.Entry(row,textvariable=v,width=20,bg='#33445a',fg=FG,insertbackground=FG,relief='flat').pack(ipady=6)
  dropdown('intent','Típus',['battle','item','text','spell','npc'])
  if plan['intent']=='battle':dropdown('outcome','Harci eredmény',['Összes harc','Győzelem','Menekülés','Halál'])
  if plan['intent']=='item':dropdown('event','Tárgyesemény',['Összes említés','Megszereztem','Használtam','Alkímiáztam'])
  if plan['intent']!='battle':entry('term','Keresett kifejezés')
  entry('last_n','Utolsó N forduló (üres = mind)')
  dropdown('selection','Találatok',['Összes','Legutóbbi','Legelső'] )
  self.plan_vars['selection'].set('Legelső' if plan.get('first') else 'Legutóbbi' if plan.get('latest') else 'Összes')
  extra=[]
  for k in ('monster_id','item_id','entity_id','command_id','exclude_monster','mode'):
   if plan.get(k) is not None and plan.get(k) is not False and plan.get(k)!='':extra.append(f'{k}: {plan[k]}')
  if extra:tk.Label(self.review_controls,text=' | '.join(extra),bg=PANEL,fg=MUTED).pack(side='left')
  self.runbtn.configure(state='normal');self.status.configure(text='Értelmezés kész – keresésre vár.')
  self.setinfo(warning+'A keresés még NEM futott le. Ellenőrizd a fenti keresési tervet, majd kattints a Keresés indítása gombra.')
 def execute_question(self):
  if self.busy or not self.pending_plan or self.pending_question!=self.question.get().strip():return
  p=dict(self.pending_plan)
  try:
   for field,v in self.plan_vars.items():
    if field=='selection':
     p['first']=v.get()=='Legelső';p['latest']=v.get()!='Összes'
    elif field=='last_n':
     val=v.get().strip();p[field]=int(val) if val else None
    else:p[field]=v.get()
   p=validate(p)
  except Exception as exc:
   messagebox.showerror('Hibás keresési feltétel',str(exc));return
  m=re.search(r'#(\d+)',self.char.get());cid=int(m.group(1)) if m else None
  self.ask_generation+=1;generation=self.ask_generation
  self.runbtn.configure(state='disabled');self.status.configure(text='Jóváhagyott keresés folyamatban…')
  diagnostics=self.diagnostics_enabled.get()
  def worker():
   c=conn()
   started=time.perf_counter()
   try:
    with SearchTrace('Szabad kérdés',p.get('intent',''),p.get('item_id') or p.get('entity_id'),p.get('event',''),diagnostics) as trace:
     rows,answer=run(c,p,cid)
     trace.record['counts']['result_turns']=len(rows)
     trace.record['counts']['result_events']=sum(r['count'] for r in rows)
    answer+=f'  [Keresési idő: {time.perf_counter()-started:.2f} s]'
    self.root.after(0,lambda:self.finish_question(generation,rows,answer,self.plan_method,self.plan_warning,p))
   except Exception as exc:
    msg=str(exc);self.root.after(0,lambda:self.finish_question(generation,None,msg,'',''))
   finally:c.close()
  threading.Thread(target=worker,daemon=True).start()
 def switch_search_mode(self):
  natural=self.search_ui_mode.get()=='Szabad kérdés'
  for frame in self.keyword_frames:
   if natural:frame.pack_forget()
   else:frame.pack(fill='x',padx=20,pady=(2,5),before=self.tree.master)
  for frame in self.question_frames:
   if not natural:frame.pack_forget()
   else:frame.pack(fill='x',padx=20,pady=(2,5),before=self.tree.master)
  if natural:self.askentry.focus_set()
  else:self.entry.focus_set()
 def open_database_manager(self):
  if hasattr(self,'db_window') and self.db_window.winfo_exists():self.db_window.lift();return
  win=tk.Toplevel(self.root);self.db_window=win;win.title('TF – Adatbázis-kezelő');win.geometry('830x400');win.configure(bg=BG)
  tk.Label(win,text='Adatbázis-kezelő',bg=BG,fg=ACC,font=('DejaVu Sans',17,'bold')).pack(anchor='w',padx=20,pady=15)
  data=stats(self.c)
  tk.Label(win,text='Adatbázis: '+str(data),bg=BG,fg=FG,wraplength=780,justify='left').pack(anchor='w',padx=20,pady=8)
  buttons=tk.Frame(win,bg=BG);buttons.pack(fill='x',padx=20,pady=10)
  RoundedButton(buttons,text='HTML-mappa importálása',command=self.choose_folder).pack(side='left',padx=5)
  RoundedButton(buttons,text='Fordulók újraindexelése',command=self.choose_reindex).pack(side='left',padx=5)
  workers=tk.Frame(win,bg=BG);workers.pack(fill='x',padx=20,pady=8)
  tk.Label(workers,text='Importálási feldolgozók:',bg=BG,fg=MUTED).pack(side='left')
  _,worker_menu=self.make_dropdown(workers,self.import_workers,18)
  self.set_menu_values(worker_menu,self.import_workers,['Automatikus','1','2','4','6','12'],callback=lambda:None)
  searchbar=tk.Frame(win,bg=BG);searchbar.pack(fill='x',padx=20,pady=5)
  tk.Label(searchbar,text='Keresési feldolgozók:',bg=BG,fg=MUTED).pack(side='left')
  _,smenu=self.make_dropdown(searchbar,self.search_workers,18)
  self.set_menu_values(smenu,self.search_workers,['Automatikus','1','2','4','6','8'],callback=lambda:None)
  tk.Label(win,text='A feldolgozás százaléka a főablak állapotsorában látható.',bg=BG,fg=MUTED).pack(anchor='w',padx=20)
  tk.Label(win,text='Az importálás az eredeti HTML-eket használja. A folyamat a főablak állapotsorában is követhető.',bg=BG,fg=MUTED,wraplength=780).pack(anchor='w',padx=20,pady=10)
 def finish_question(self,generation,rows,answer,method,warning,plan=None):
  if generation!=self.ask_generation or self.busy:return
  if rows is None:
   self.status.configure(text='A kérdést nem sikerült feldolgozni.');self.setinfo('Nem tudtam megbízhatóan megválaszolni: '+answer);return
  self.rows=sorted(rows,key=lambda r:(r['character'].casefold(),-r['turn_number']))
  self.column_sort=None;self.column_desc=False;self.apply_column_sort();self.render_rows()
  self.status.configure(text=f'{method} • {len(rows)} forrásforduló • az eredeti HTML megnyitható')
  criteria=''
  if plan:
   labels={'battle':'Harc','spell':'Varázslat','npc':'NPC / küldetés','item':'Tárgy','text':'Szöveg'}
   bits=[labels.get(plan.get('intent'),'Keresés')]
   if plan.get('monster_id'):bits.append('Szörny #'+str(plan['monster_id']))
   if plan.get('item_id'):bits.append('Tárgy #'+str(plan['item_id']))
   for field in ('outcome','command_id'):
    if plan.get(field):bits.append(str(plan[field]))
   if plan.get('term') and (plan.get('intent')!='battle' or plan.get('monster_id')):bits.append(str(plan['term']))
   if plan.get('exclude_monster'):bits.append('kivéve a megnevezett szörny')
   if plan.get('first'):bits.append('legelső')
   elif plan.get('latest'):bits.append('legutóbbi')
   if plan.get('last_n'):bits.append('utolsó '+str(plan['last_n'])+' forduló')
   criteria='Felismert feltételek: '+' | '.join(bits)+'\n\n'
  self.setinfo(warning+criteria+answer+'\n\nA találatok az eredeti fordulókhoz kapcsolódnak. Jelölj ki egy sort a részletekhez, dupla kattintással nyisd meg a HTML-t.')
 def reset_filters(self):
  if self.busy:return
  if self.timer:
   self.root.after_cancel(self.timer);self.timer=None
  # A mar folyamatban levo keresesi eredmenyeket ervenytelenitjuk.
  self.search_generation+=1;self.ask_generation+=1
  self.selected_object=None
  self.clear_question_object()
  self.q.set('');self.question.set('')
  if self.timer:
   self.root.after_cancel(self.timer);self.timer=None
  self.char.set('Minden karakter')
  self.mode.set('Pontos kifejezés')
  self.sort.set('Karakter / forduló')
  self.event_mode.set('Összes említés')
  self.battle_outcome.set('Összes harc')
  self.battle_period.set('Összes importált forduló')
  self.column_sort=None;self.column_desc=False
  self.rows=[];self.searching=False
  self.invalidate_question_plan()
  self.render_rows();self.apply_column_sort()
  self.status.configure(text='Keresési feltételek alaphelyzetbe állítva.')
  self.setinfo('A keresési feltételek törölve. Az importált fordulók és az adatbázis változatlanok.')
  (self.askentry if self.search_ui_mode.get()=='Szabad kérdés' else self.entry).focus_set()
 def clear_question_object(self):
  self.question_object=None;self.question_object_label.set('Nincs kiválasztva')
 def choose_question_object(self):
  """Dedicated encyclopedia selector; does not modify the keyword search."""
  if self.busy:return
  win=tk.Toplevel(self.root);win.title('Objektum beszúrása a szabad kérdésbe');win.geometry('670x480');win.configure(bg=BG);win.transient(self.root)
  top=tk.Frame(win,bg=BG);top.pack(fill='x',padx=12,pady=12)
  kind=tk.StringVar(value='Szörny')
  _,menu=self.make_dropdown(top,kind,15)
  for label in ('Szörny','Tárgy'):menu.add_radiobutton(label=label,variable=kind,value=label)
  term=tk.StringVar()
  entry=tk.Entry(top,textvariable=term,bg=PANEL,fg=FG,insertbackground=FG,relief='flat',font=('DejaVu Sans',11))
  entry.pack(side='left',fill='x',expand=True,padx=8,ipady=6)
  tk.Label(win,text='Írd be a név egy részét vagy a #azonosítót; a lista gépelés közben frissül.',bg=BG,fg=MUTED).pack(anchor='w',padx=12)
  tree=ttk.Treeview(win,columns=('id','name'),show='headings',selectmode='browse')
  tree.heading('id',text='Azonosító');tree.heading('name',text='Enciklopédiai név')
  tree.column('id',width=120,stretch=False);tree.column('name',width=480)
  tree.pack(fill='both',expand=True,padx=12,pady=9)
  found=[]
  def update(*_):
   nonlocal found
   tree.delete(*tree.get_children())
   found=catalog(self.c,term.get(), 'monster' if kind.get()=='Szörny' else 'item',limit=200)
   for i,r in enumerate(found):tree.insert('','end',iid=str(i),values=(r['entity_id'],r['name']))
  def select(_=None):
   if not tree.selection():return
   self.question_object=dict(found[int(tree.selection()[0])])
   self.question_object_label.set(f"{KINDS[self.question_object['kind']]}: {self.question_object['name']} (#{self.question_object['entity_id']})")
   win.destroy()
  RoundedButton(win,text='Beszúrás a kérdésbe',tone='search',command=select).pack(pady=(0,12))
  tree.bind('<Double-1>',select);term.trace_add('write',update);kind.trace_add('write',update)
  update();entry.focus_set()
 def choose_object(self):
  if self.busy:return
  win=tk.Toplevel(self.root);win.title('TF objektum kiválasztása');win.geometry('650x500');win.configure(bg=BG);win.transient(self.root)
  top=tk.Frame(win,bg=BG);top.pack(fill='x',padx=12,pady=12)
  tk.Label(top,text='Név vagy #azonosító:',bg=BG,fg=FG).pack(side='left')
  term=tk.StringVar(value=self.q.get());entry=tk.Entry(top,textvariable=term,bg=PANEL,fg=FG,insertbackground=FG)
  entry.pack(side='left',fill='x',expand=True,padx=8)
  kinds={'Mindegyik':None,'Tárgy':'item','Szörny':'monster','Varázslat':'spell'}
  k=tk.StringVar(value='Mindegyik')
  button,menu=self.make_dropdown(win,k,20)
  menu.delete(0,'end')
  for label in kinds:menu.add_radiobutton(label=label,variable=k,value=label)
  cols=('kind','id','name');tree=ttk.Treeview(win,columns=cols,show='headings',selectmode='browse')
  for col,title,width in [('kind','Típus',100),('id','Azonosító',100),('name','Név',400)]:tree.heading(col,text=title);tree.column(col,width=width)
  tree.pack(fill='both',expand=True,padx=12,pady=8)
  found=[]
  def update(*_):
   nonlocal found
   tree.delete(*tree.get_children());found=catalog(self.c,term.get(),kinds[k.get()],limit=200)
   for i,item in enumerate(found):tree.insert('','end',iid=str(i),values=(KINDS[item['kind']],item['entity_id'],item['name']))
  def select(_=None):
   sel=tree.selection()
   if not sel:return
   self.selected_object=found[int(sel[0])]
   self.mode.set('Harci események' if self.mode.get()=='Harci események' and self.selected_object['kind']=='monster' else 'Objektumkeresés');self.q.set(self.selected_object['name']);win.destroy();self.refresh()
  RoundedButton(win,text='Kiválasztás',command=select).pack(pady=(0,12))
  tree.bind('<Double-1>',select);term.trace_add('write',update);k.trace_add('write',update)
  update();entry.focus_set()
 def make_dropdown(self,parent,variable,width):
  # Natív Tk menü: kattintásra megnyílik, és az összes szín explicit.
  widget=tk.Menubutton(parent,textvariable=variable,indicatoron=True,
                       relief='flat',bd=1,highlightthickness=1,
                       highlightbackground='#405168',highlightcolor=ACC,
                       bg='#33445a',fg=FG,activebackground='#405168',
                       activeforeground='#ffffff',font=('DejaVu Sans',10),
                       width=width,anchor='w',padx=7,pady=6)
  menu=tk.Menu(widget,tearoff=False,relief='flat',bd=1,
               bg=PANEL,fg=FG,activebackground='#316b78',
               activeforeground='#ffffff',selectcolor=ACC,
               font=('DejaVu Sans',10))
  widget.configure(menu=menu)
  widget.pack(side='left',padx=5)
  return widget,menu
 def set_menu_values(self,menu,variable,values,callback=None):
  menu.delete(0,'end')
  for value in values:
   menu.add_radiobutton(label=value,variable=variable,value=value,
                        command=callback or self.refresh)
 def setinfo(self,s,highlight=None):
  self.info.configure(state='normal');self.info.delete('1.0','end');self.info.insert('1.0',s)
  if highlight:
   for m in re.finditer(re.escape(highlight),s,re.IGNORECASE):
    self.info.tag_add('match',f'1.0+{m.start()}c',f'1.0+{m.end()}c')
  self.info.configure(state='disabled')
 def refresh_chars(self):
  values=['Minden karakter']+[f"{r['character']} (#{r['character_id']})" for r in self.c.execute('SELECT DISTINCT character,character_id FROM turns ORDER BY character')]
  self.set_menu_values(self.charmenu,self.char,values)
  if self.char.get() not in values:self.char.set(values[0])
 def schedule_search(self,*_):
  if self.search_ui_mode.get()=='Szabad kérdés':return
  if self.timer:self.root.after_cancel(self.timer)
  self.timer=self.root.after(250,self.refresh)
 def refresh(self):
  self.timer=None
  if self.busy:return
  m=re.search(r'#(\d+)',self.char.get());cid=int(m.group(1)) if m else None
  query=self.q.get().strip();mode=self.mode.get();chosen=self.selected_object;event_mode=self.event_mode.get()
  if mode=='Harci események' and query and (not chosen or chosen['kind']!='monster' or query!=chosen['name']):chosen=None
  self.search_generation+=1;generation=self.search_generation
  if mode=='Objektumkeresés':
   choices=catalog(self.c,query,limit=100)
   if chosen and query and query!=chosen['name'] and query!=f"#{chosen['entity_id']}":chosen=None
   if not chosen:
    exact=[x for x in choices if x['name'].casefold()==query.casefold()]
    if not exact and query.startswith('#'):exact=choices
    chosen=exact[0] if len(exact)==1 else None
   self.object_hint=(f"{KINDS[chosen['kind']]}: {chosen['name']} (#{chosen['entity_id']})" if chosen else 'Válassz egy objektumot az „Objektum kiválasztása” gombbal. A kétértelmű neveket nem azonosítjuk automatikusan.')
  if mode=='Objektumkeresés' and chosen and chosen['kind']!='item' and event_mode!='Összes említés':
   self.object_hint+=' — Az eseményszűrő jelenleg csak tárgyakra vonatkozik; itt az összes említést keressük.'
  self.ask_generation+=1
  self.searching=True
  self.status.configure(text='Keresés folyamatban… Dolgozom…')
  self.root.update_idletasks()
  diagnostics=self.diagnostics_enabled.get()
  def worker():
   c=conn();started=time.perf_counter()
   try:
    with SearchTrace(mode,'item' if mode=='Objektumkeresés' and chosen and chosen['kind']=='item' else mode,chosen['entity_id'] if chosen else None,event_mode,diagnostics) as trace:
     warnings=0
     if mode=='Harci események':
      period=self.battle_period.get();last_n=None if period.startswith('Összes') else int(re.search(r'\d+',period).group())
      rows,warnings=search_battles(c,self.battle_outcome.get(),cid,last_n,chosen['entity_id'] if chosen and chosen['kind']=='monster' else None)
     elif mode=='Objektumkeresés':
      rows=(search_item_events(c,chosen['entity_id'],event_mode,cid) if chosen['kind']=='item' and event_mode!='Összes említés' else search_objects(c,chosen['kind'],chosen['entity_id'],cid,include_ids=True)) if chosen else []
     else:
      n=int(c.execute('SELECT COUNT(*) FROM turns').fetchone()[0]);workers=int(self.search_workers.get()) if self.search_workers.get().isdigit() else (4 if n>=500 else 1)
      rows=search_text_parallel(c,query,cid,advanced=mode=='Intelligens keresés',workers=workers)
     trace.record['counts']['result_turns']=len(rows)
     trace.record['counts']['result_events']=sum(r['count'] for r in rows)
    total_turns=c.execute('SELECT COUNT(*) FROM turns').fetchone()[0]
    if mode=='Harci események' and warnings:total_turns=f'{total_turns} (hiányzó/hibás forrás: {warnings})'
    elapsed=time.perf_counter()-started
    self.root.after(0,lambda:self.finish_search(generation,rows,None,query,mode,total_turns,elapsed))
   except Exception as e:
    msg=str(e);self.root.after(0,lambda:self.finish_search(generation,[],msg,query,mode,0))
   finally:c.close()
  threading.Thread(target=worker,daemon=True).start()
 def finish_search(self,generation,rows,error,query,mode,total_turns,elapsed=None):
  if generation!=self.search_generation or self.busy:return
  self.searching=False
  if error:
   self.status.configure(text='Keresési hiba');self.setinfo('Keresési hiba: '+error);return
  self.rows=rows
  order=self.sort.get()
  if order=='Legtöbb előfordulás':self.rows.sort(key=lambda r:(-r['count'],r['character'], -r['turn_number']))
  elif order=='Legnagyobb fordulószám':self.rows.sort(key=lambda r:(-r['turn_number'],r['character']))
  else:self.rows.sort(key=lambda r:(r['character'].casefold(),-r['turn_number']))
  self.apply_column_sort();self.render_rows()
  total=sum(r['count'] for r in self.rows);characters=len(set(r['character_id'] for r in self.rows))
  self.status.configure(text=f'{characters} karakter • {len(self.rows)} forduló • {total} előfordulás   |   {total_turns} importált forduló'+(f' | {elapsed:.2f} s' if elapsed is not None else ''))
  if mode=='Objektumkeresés' and not self.rows:self.setinfo(self.object_hint+'\n\nNincs találat a kiválasztott objektumra az importált fordulókban.')
  elif mode=='Harci események':self.setinfo('Harci események: '+self.battle_outcome.get()+' — '+self.battle_period.get()+'.\nA találatok a csatastatisztikákhoz kapcsolódnak. Az eredeti HTML-fájloknak elérhetőnek kell lenniük.\nA szörny megadásához válaszd ki a szörnyet, majd állítsd a keresési módot Harci eseményekre.\nA lista fordulónként csoportosít; az Előfordulás oszlop az adott forduló csatáinak számát mutatja.')
  elif not query:self.setinfo('Írj be egy keresett kifejezést. Intelligens keresésben: ÉS / VAGY / NEM, idézőjeles kifejezések, ékezetfüggetlen keresés.')
  elif not self.rows:self.setinfo('Nincs találat az importált fordulókban. Az enciklopédia tartalma nem számít találatnak.')
  else:self.setinfo((self.object_hint+'\n' if mode=='Objektumkeresés' else '')+'Válassz egy fordulót a találati listából a szövegkörnyezeti példák megtekintéséhez. Dupla kattintás: HTML megnyitása.')
 def render_rows(self):
  self.tree.delete(*self.tree.get_children())
  for i,r in enumerate(self.rows):
   sample=r['snippets'][0]['text'] if r['snippets'] else ''
   self.tree.insert('','end',iid=str(i),values=(r['character'],f"{r['turn_number']}.",f"{r['count']}×",r.get('match_types','—'),sample))
 def apply_column_sort(self):
  if self.column_sort:
   field='turn_number' if self.column_sort=='turn' else 'count'
   self.rows.sort(key=lambda r:(r[field],r['character'].casefold(),r['turn_number']),reverse=self.column_desc)
  for col,label in [('turn','Forduló'),('count','Előfordulás')]:
   suffix=(' ▼' if self.column_desc else ' ▲') if col==self.column_sort else ''
   self.tree.heading(col,text=label+suffix)
 def sort_by_column(self,col):
  if self.busy:return
  if self.column_sort==col:self.column_desc=not self.column_desc
  else:self.column_sort=col;self.column_desc=False
  self.apply_column_sort();self.render_rows()
 def export_results(self):
  if self.busy:return
  if not self.rows:
   messagebox.showinfo('Nincs exportálható találat','Előbb keress rá egy kifejezésre, amelynek vannak találatai.');return
  path=filedialog.asksaveasfilename(title='Találatok exportálása',defaultextension='.xlsx',filetypes=[('Excel munkafüzet','*.xlsx'),('CSV fájl','*.csv')],initialfile='tf_talalatok.xlsx')
  if not path:return
  path=Path(path)
  headings=['Karakter','Karakterazonosító','Forduló','Előfordulás','Egyezés típusa','Első szövegkörnyezet','Forrás HTML']
  records=[[r['character'],r['character_id'],r['turn_number'],r['count'],r.get('match_types',''),r['snippets'][0]['text'] if r['snippets'] else '',r['source_path']] for r in self.rows]
  try:
   if path.suffix.lower()=='.csv':
    with path.open('w',encoding='utf-8-sig',newline='') as f:
     writer=csv.writer(f,delimiter=';');writer.writerow(headings);writer.writerows(records)
   elif path.suffix.lower()=='.xlsx':
    from openpyxl import Workbook
    from openpyxl.styles import Font,PatternFill,Alignment
    from openpyxl.utils import get_column_letter
    wb=Workbook();ws=wb.active;ws.title='Találatok'
    ws.append(headings)
    for record in records:ws.append(record)
    ws.freeze_panes='A2';ws.auto_filter.ref=ws.dimensions
    for cell in ws[1]:cell.font=Font(bold=True,color='FFFFFF');cell.fill=PatternFill('solid',fgColor='263448');cell.alignment=Alignment(wrap_text=True)
    for i,width in enumerate([27,19,13,17,19,90,75],1):ws.column_dimensions[get_column_letter(i)].width=width
    for row in ws.iter_rows(min_row=2):
     for cell in row:
      cell.alignment=Alignment(vertical='top',wrap_text=cell.column==6)
      if cell.row%2==0:cell.fill=PatternFill('solid',fgColor='EDF3F7')
     ws.row_dimensions[row[0].row].height=34
    wb.save(path)
   else:raise ValueError('Csak CSV vagy XLSX kiterjesztés használható.')
  except Exception as e:messagebox.showerror('Exportálási hiba',str(e));return
  messagebox.showinfo('Exportálás kész',f'{len(records)} forduló találatai exportálva:\n{path}')
 def details(self,_=None):
  sel=self.tree.selection()
  if not sel:return
  r=self.rows[int(sel[0])]
  snippets='\n\n'.join(f"{i}. példa (szövegblokk #{x['seq']+1}):\n{x['text']}" for i,x in enumerate(r['snippets'],1))
  s=f"{r['character']} — {r['turn_number']}. forduló — {r['count']} előfordulás\n"+(f"Egyezés: {r.get('match_types','')} (név: {r.get('name_count',0)}, azonosító: {r.get('id_count',0)})\n" if self.mode.get()=='Objektumkeresés' else '')+f"Forrás: {r['source_path']}\n\n{snippets}\n\nDupla kattintás vagy 'Forduló megnyitása': eredeti HTML a böngészőben."
  self.setinfo(s,self.q.get().strip() if self.mode.get()=='Pontos kifejezés' else None)
 def open_source(self):
  sel=self.tree.selection()
  if not sel:return
  p=Path(self.rows[int(sel[0])]['source_path'])
  if p.is_file():
   try:webbrowser.open(p.resolve().as_uri())
   except Exception as e:messagebox.showerror('Megnyitási hiba',str(e))
  else:messagebox.showwarning('Hiányzó forrás',f'A HTML-fájl nem található:\n{p}\nImportáld újra az eredeti mappából.')
 def busy_state(self,value):
  self.busy=value
  for b in self.buttons+[self.askbtn,self.aiconfig,self.runbtn]:b.configure(state='disabled' if value else 'normal')
  if not value and self.pending_plan:self.runbtn.configure(state='normal')
 def update_progress(self,done,total,name):
  pct=round(100*done/total) if total else 100
  self.progress['value']=pct;self.percent.configure(text=f'{pct}%');self.status.configure(text=f'Importálás: {done}/{total} fájl • {name}')
 def import_done(self,result,error):
  self.busy_state(False)
  if error:messagebox.showerror('Importálási hiba',error);return
  self.progress['value']=100;self.percent.configure(text='100%')
  self.refresh_chars();self.refresh()
  errors=[f'{name}: {msg}' for name,msg in result if msg.startswith('HIBA:')]
  self.setinfo(f'Importálás kész: {len(result)} fájl, {len(errors)} hiba.\n'+('\n'.join(errors[:30]) if errors else 'A feldolgozás befejeződött.'))
 def choose_folder(self):
  if self.busy:return
  p=filedialog.askdirectory(title='HTML-fordulók mappája')
  if not p:return
  self.search_generation+=1;self.busy_state(True);self.progress['value']=0;self.percent.configure(text='0%');self.status.configure(text='Fájlok keresése…')
  def worker():
   os.environ['TF_IMPORT_WORKERS']='auto' if self.import_workers.get()=='Automatikus' else self.import_workers.get()
   c=conn()
   try:
    result=import_folder(c,p,lambda d,t,n:self.root.after(0,lambda d=d,t=t,n=n:self.update_progress(d,t,n)))
    self.root.after(0,lambda r=result:self.import_done(r,None))
   except Exception as e:
    self.root.after(0,lambda msg=str(e):self.import_done([],msg))
   finally:c.close()
  threading.Thread(target=worker,daemon=True).start()
 def choose_reindex(self):
  if self.busy:return
  count=self.c.execute('SELECT COUNT(*) FROM turns').fetchone()[0]
  if not count:
   messagebox.showinfo('Újraindexelés','Még nincsenek importált fordulók.');return
  if not messagebox.askyesno('Fordulók újraindexelése',f'{count} forduló teljes szövegét újra feldolgozzuk az eredeti HTML-fájlokból.\n\nA meglévő találatok és események frissülnek. Hiányzó eredeti fájlokat nem törlünk.\n\nElindítod?'):return
  self.search_generation+=1;self.busy_state(True);self.progress['value']=0;self.percent.configure(text='0%');self.status.configure(text='Újraindexelés indul…')
  def worker():
   os.environ['TF_IMPORT_WORKERS']='auto' if self.import_workers.get()=='Automatikus' else self.import_workers.get()
   c=conn()
   try:
    result,errors=reindex_all(c,lambda d,t,n:self.root.after(0,lambda d=d,t=t,n=n:self.update_progress(d,t,n)))
    self.root.after(0,lambda:self.reindex_done(result,errors,None))
   except Exception as e:
    msg=str(e);self.root.after(0,lambda:self.reindex_done([],[],msg))
   finally:c.close()
  threading.Thread(target=worker,daemon=True).start()
 def reindex_done(self,result,errors,error):
  self.busy_state(False)
  if error:messagebox.showerror('Újraindexelési hiba',error);return
  self.progress['value']=100;self.percent.configure(text='100%');self.refresh_chars();self.refresh()
  summary=f'Újraindexelés kész: {len(result)} forduló, {len(errors)} probléma.'
  if errors:summary+='\n\n'+ '\n'.join(f'{path}: {reason}' for path,reason in errors[:25])
  self.setinfo(summary)
  if errors:messagebox.showwarning('Újraindexelés – hiányzó vagy hibás fájlok',summary)
 def close(self):
  if self.busy:
   messagebox.showinfo('Importálás folyamatban','Várd meg az importálás végét a bezárás előtt.');return
  try:self.c.close()
  finally:self.root.destroy()
 def main(self):self.root.mainloop()
if __name__=='__main__':GUI().main()
