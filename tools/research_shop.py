"""Ordinary-input bakery exploration after the mansion bank opening."""
import json,mgba.log
from tools.rom import ROOT,load_base,digest
from tools.emulator import Session,Snapshot,Debugger
from tools.audit_menu_layouts import Observer
from tools.town_playtest import position
OUT=ROOT/'build/services/shop-original'
def run():
 mgba.log.silence();rom=load_base()
 with Session(rom,OUT) as g:
  g.restore(Snapshot.load(ROOT/'build/mansion/native/family-1-1/morning'));o=Observer(g);steps=[]
  with Debugger(g,o.callback,max_events=50000) as d:
   for a in o.ADDRESSES:d.breakpoint(a)
   for key,hold in [('DOWN',8),('LEFT',120),('UP',32),('A',3),('A',3),('A',3),('A',3)]:
    g.press(key,hold=hold,wait=120);g.capture(f'step-{len(steps):02}');steps.append({'key':key,'hold':hold,'position':position(g),'read_count':len(o.reads)})
  (OUT/'report.json').write_text(json.dumps({'source_rom_sha256':digest(rom),'reads':o.reads,'callers':o.callers,'creates':o.creates,'steps':steps,'inputs':g.inputs},ensure_ascii=False,indent=2)+'\n')
  print(steps)
  for r in o.reads:print(hex(r['source']),r['window_width'],repr(r['text']))
if __name__=='__main__':run()
