"""Native storage transactions and a real pre-transaction book save."""
import json,mgba.log
from tools.emulator import Session,Snapshot,Debugger
from tools.rom import ROOT,load_base,digest,require
from tools.audit_menu_layouts import Observer
from tools.research_mansion import Discovery
from tools.holy_flame_playtest import items
OUT=ROOT/'build/services/storage-transactions-original'
def run():
 mgba.log.silence();rom=load_base();cases=[]
 for name,fixture,actions in [
  ('save',ROOT/'build/services/storage-research/menu',['DOWN','DOWN','DOWN','A','A','A','A','A']),
  ('deposit',ROOT/'build/services/storage-populated/deposit-list',['R','A','A','A','B']),
 ]:
  with Session(rom,OUT/name) as g:
   g.restore(Snapshot.load(fixture));o=Observer(g);c=Discovery(g);saved=[];before=items(g)
   def cb(e):
    o.callback(e)
    if e['address'] in c.ADDRESSES:c.callback(e)
    if e['address']==0x08015354:saved.append(e['frame'])
   with Debugger(g,cb,max_events=50000) as d:
    for a in set(o.ADDRESSES+c.ADDRESSES+(0x08015354,)):d.breakpoint(a)
    for i,key in enumerate(actions):g.press(key,wait=180);g.capture(f'step-{i}');print(name,i,key,items(g),flush=True)
   g.snapshot().save(OUT/name/'end');g.capture('end')
   if saved:
    (OUT/'storage-ready.sav').write_bytes(g.snapshot().battery)
   cases.append({'case':name,'before':before,'after':items(g),'saved':saved,'reads':o.reads,'creates':o.creates,'entries':c.entries,'inputs':g.inputs})
 (OUT/'report.json').write_text(json.dumps({'source_rom_sha256':digest(rom),'cases':cases},ensure_ascii=False,indent=2)+'\n')
if __name__=='__main__':run()
