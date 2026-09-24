"""Ordinary-input castle quest continuation using a naturally found wand."""
import json,mgba.log
from tools.emulator import Session,Snapshot,Debugger
from tools.rom import ROOT,load_base,require,digest
from tools.mansion_playtest import walk_to_stairs,direction
from tools.name_entry_playtest import position,stairs_path,nearby_monsters,ACTORS,narrow_passage
from tools.research_mansion import Discovery,status
OUT=ROOT/'build/services/holy-flame-equipped'
def items(g):
 m=g.core.memory
 return [(s,m.u8[0x020013d0+m.u8[0x0200df28+s*120+8]],m.u8[0x0200df28+s*120+4]) for s in range(20) if m.u32[0x0200df28+s*120]&0x80000000]
def use(g,ident,action):
 selected=next(s for s,i,_ in items(g) if i==ident)
 g.press('B',hold=8,wait=90);g.press('A',wait=90)
 for _ in range(selected):g.press('DOWN',wait=20)
 g.press('A',wait=90);m=g.core.memory
 commands=[m.u16[0x0200cdd0+i*2]&127 for i in range(7)]
 require(action in commands,'Requested item command unavailable')
 for _ in range(commands.index(action)):g.press('DOWN',wait=20)
 g.press('A',wait=180)
def run():
 mgba.log.silence();rom=load_base();turns=[];error=None
 with Session(rom,OUT) as g:
  g.restore(Snapshot.load(ROOT/'build/services/holy-flame-dungeon/floor-6-start'));o=Discovery(g)
  with Debugger(g,o.callback,max_events=100000) as d:
   for a in o.ADDRESSES:d.breakpoint(a)
   walk_to_stairs(g,(47,27));require(any(i==51 for _,i,_ in items(g)),'Native lightning wand not picked up');g.capture('wand-found')
   try:
    for turn in range(600):
     path=stairs_path(g)
     if not path:break
     m=g.core.memory;p=m.u32[ACTORS];hp=m.u16[p+0x84];enemies=nearby_monsters(g);before=position(g)
     if enemies:
      enemy=min(enemies,key=lambda e:e['hp']);dx,dy=enemy['position'][0]-before[0],enemy['position'][1]-before[1]
      g.press(direction(dx,dy),wait=30)
      if enemy['hp']>=10 and any(i==51 and charge>0 for _,i,charge in items(g)):use(g,51,10);key='lightning-wand'
      else:g.press('A',wait=90);key='attack'
     elif hp<m.u16[p+0x86]-1 or (nearby_monsters(g,4) and narrow_passage(g)):
      g.press('A',wait=90);key='wait/heal'
     else:
      q=path[0];key=direction(q[0]-before[0],q[1]-before[1]);g.press(key,wait=90)
     turns.append({'before':before,'after':position(g),'key':key,'hp':hp,'hp_after':m.u16[p+0x84],'items':items(g),'enemies':enemies})
     require(m.u16[p+0x84]>0,'Castle route defeated')
    else:raise ValueError('Castle route turn limit')
    g.capture('stairs');g.snapshot().save(OUT/'stairs');g.press('A',wait=600);g.capture('floor-seven')
   except Exception as exc:error=str(exc);print('ERROR',error)
  g.capture('end');g.snapshot().save(OUT/'end')
  report={'passed':error is None,'error':error,'source_rom_sha256':digest(rom),'status':status(g),'turns':turns,'inputs':g.inputs,'entries':o.entries,'unknown':o.unknown}
  (OUT/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(report['status'])
if __name__=='__main__':run()
