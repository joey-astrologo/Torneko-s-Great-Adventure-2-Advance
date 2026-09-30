import argparse,struct
from pathlib import Path
from tools.rom import ROOT,require
from tools.verify_dungeon_leaves import run as run_leaves
class Warning:
 breakpoints=()
 scope='Complete original140AC timer/actor loop runs after controlled native dispatch, with expiry timer1 and existing live player/monster flags. Both recipient profiles clear bit2 natively and display the immutable English priest notice once. Original map effects, queue, caller/ABI/pixels/battery are checked; natural acquisition of this state remains separate.'
 def case_fields(self,owner):return ('player','monster')
 def setup(self,owner,g,hero,actor,write,overrides):
  m=g.core.memory;self.timer=m.u32[0x08014140];write(self.timer,b'\1\0');self.expected={};self.selected=hero if self.field=='player' else actor
  for i in range(56):
   at=m.u32[0x02001624+4*i];value=m.u32[at+8];value=(value|2) if at==self.selected else (value&~2);write(at+8,struct.pack('<I',value));self.expected[at]=value&~2
  return (0,0,0,0)
 def event(self,*args):pass
 def return_register(self,owner):return 0
 def returned(self,owner,g,hero,actor):
  m=g.core.memory;require(m.u16[self.timer]==0 and all(m.u32[at+8]==value for at,value in self.expected.items()),'Priest timer/actor native expiry differs')

def run(source=ROOT/'build/english'):
 return run_leaves(source,owners={'priest-warning':(0x140AC,0,0x14109,0x1413C,None,0x4E0)},resource_key='priest_warning',folder='priest-warning-validation',hooks=Warning())

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,default=ROOT/'build/english');run(p.parse_args().source)
