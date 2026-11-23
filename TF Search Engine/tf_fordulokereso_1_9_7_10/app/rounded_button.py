"""Pure Tk canvas rounded buttons, no third-party GUI dependencies."""
import tkinter as tk
from tkinter import font

PALETTE={
 'neutral':('#30465e','#42647a'),
 'search':('#255a79','#33799e'),
 'export':('#28624e','#357e64'),
 'reset':('#465267','#59677f'),
 'close':('#703e48','#8a4a57'),
}
class RoundedButton(tk.Canvas):
 def __init__(self,parent,text,command,icon=None,tone='neutral',**kwargs):
  self.text=text;self.command=command;self.enabled=True;self.tone=tone
  self.font=tk.font.Font(family='DejaVu Sans',size=10,weight='normal')
  w=max(105,self.font.measure(text)+28)
  super().__init__(parent,width=w,height=39,bg='#151a24',highlightthickness=0,bd=0,cursor='hand2',**kwargs)
  self.w=w;self.hover=False;self.draw()
  self.bind('<Enter>',lambda e:self.set_hover(True));self.bind('<Leave>',lambda e:self.set_hover(False))
  self.bind('<Button-1>',lambda e:self.command() if self.enabled else None)
 def configure(self,cnf=None,**kw):
  state=kw.pop('state',None)
  if state is not None:self.enabled=state!='disabled';self.draw()
  if kw or cnf:return super().configure(cnf,**kw)
 config=configure
 def set_hover(self,value):self.hover=value;self.draw()
 def draw(self):
  self.delete('all');w=self.w;h=39;r=10
  base,hover=PALETTE.get(self.tone,PALETTE['neutral'])
  fill='#263242' if not self.enabled else hover if self.hover else base
  self.create_rectangle(r,1,w-r,h-1,fill=fill,outline='')
  self.create_rectangle(1,r,w-1,h-r,fill=fill,outline='')
  for x,y,start in [(1,1,90),(w-2*r-1,1,0),(w-2*r-1,h-2*r-1,270),(1,h-2*r-1,180)]:
   self.create_arc(x,y,x+2*r,y+2*r,start=start,extent=90,style='pieslice',fill=fill,outline=fill)
  self.create_text(w/2,19,text=self.text,anchor='center',font=self.font,fill='#e5eef8' if self.enabled else '#758292')
