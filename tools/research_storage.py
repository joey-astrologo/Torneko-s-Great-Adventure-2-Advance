"""Reach the repaired blue book through ordinary inputs, with source/geometry traces."""
import json,mgba.log
from tools.rom import ROOT,load_base,digest,require
from tools.emulator import Session,Snapshot,Debugger
from tools.trace_mansion import SourceTrace
from tools.audit_menu_layouts import Observer
from tools.town_playtest import position
OUT=ROOT/'build/services/storage-research'
def run():
 mgba.log.silence();rom=load_base()
 with Session(rom,OUT) as g:
  g.restore(Snapshot.load(ROOT/'build/services/storage-bluebook/end'));c=SourceTrace(g);o=Observer(g)
  def cb(e):c.callback(e);o.callback(e)
  with Debugger(g,cb,max_events=50000) as d:
   for a in set(c.ADDRESSES+o.ADDRESSES):d.breakpoint(a)
   g.press('B',wait=240)
   for _ in range(20):
    print('dialogue',c.active,flush=True)
    if not c.active:break
    g.press('A',wait=240)
   g.press('A',wait=120)  # Close the final dialogue acknowledgement outside the reader.
   for i,(key,hold) in enumerate([('DOWN',8),('RIGHT',16),('UP',32),('LEFT',16),('UP',3),('A',3)]):
    g.press(key,hold=hold,wait=120);g.capture(f'approach-{i}');print(key,position(g),flush=True)
   g.capture('menu');g.snapshot().save(OUT/'menu')
  report={'source_rom_sha256':digest(rom),'position':position(g),'reads':o.reads,'creates':o.creates,'callers':o.callers,'entries':c.entries,'inputs':g.inputs}
  (OUT/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
  print([(hex(r['source']),r['window_width'],r['text']) for r in o.reads])
if __name__=='__main__':run()
