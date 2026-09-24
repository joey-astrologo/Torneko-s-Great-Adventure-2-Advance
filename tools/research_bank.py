"""Ordinary-input bank deposit/withdrawal discovery from the earned bank opening."""
import json
import mgba.log
from tools.rom import ROOT,load_base,digest
from tools.emulator import Session,Debugger,Snapshot
from tools.audit_menu_layouts import Observer
OUT=ROOT/'build/services/bank-original'
def run():
 mgba.log.silence();rom=load_base();fixture=Snapshot.load(ROOT/'build/mansion/native/family-1-1/morning')
 with Session(rom,OUT) as g:
  g.restore(fixture);o=Observer(g);formats=[];steps=[]
  def cb(e):
   o.callback(e)
   if e['address']==0x08000fb8:
    r=e['registers'];formats.append({'dest':r[0],'template':r[1],'args':r[2:4],'caller':r[14]})
  def step(key,hold=3):
   g.press(key,hold=hold,wait=180);g.capture(f'step-{len(steps):02}');m=g.core.memory
   steps.append({'key':key,'wallet':m.u32[m.u32[0x02001624]+0x60],'bank':m.u32[0x02002c1c],'reads':len(o.reads)})
  with Debugger(g,cb,max_events=80000) as d:
   for a in o.ADDRESSES+(0x08000fb8,):d.breakpoint(a)
   step('UP',8);step('A');step('A');step('A');step('UP');step('A');step('A');step('A');step('B')
  (OUT/'report.json').write_text(json.dumps({'source_rom_sha256':digest(rom),'reads':o.reads,'callers':o.callers,'formats':formats,'steps':steps,'inputs':g.inputs},ensure_ascii=False,indent=2)+'\n')
  print(steps)
  for r in o.reads:print(hex(r['source']),repr(r['text']))
if __name__=='__main__':run()
