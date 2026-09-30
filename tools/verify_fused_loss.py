import argparse,json,struct
from pathlib import Path
from tools.rom import ROOT,require
from tools.compact_font import encode
from tools.verify_dungeon_leaves import run
class Loss:
 def __init__(self,build):self.build=build
 breakpoints=(0x08011156,)
 scope='Complete original110FC inventory scan/ability removal after controlled Drink dispatch. Equipped Oaken club/Bronze shield and one extra ability bit select all20 sword/16 shield bits admitted by original112D0 masks. The original RNG result is explicitly set to valid0 for deterministic selection; original item search, kind/name lookup, bit removal and final synthesized-property flag updates execute. Three formatter-only item field bounds use the original64-byte scratch. Output/field/ABI guards, one-line decision, pixels and battery checked. Natural effect acquisition, other112D0 gating and four unused-by-this-wrapper shield label slots remain separate.'
 def case_fields(self,owner):return tuple(f'native-{kind}-{bit}' for kind in (0,1) for bit in range(20 if kind==0 else 16))+('stress-width','stress-bytes','stress-colour')
 def setup(self,owner,g,hero,actor,write,overrides):
  self.kind,self.bit=map(int,self.field.split('-')[1:]) if self.field.startswith('native-') else (0,6)
  m=g.core.memory;self.item=0x0200DF28+120;ident=31 if self.kind else 1;raw=bytearray(120);self.flags=0xC8A00000|(1<<self.bit);struct.pack_into('<I',raw,0,self.flags);raw[5]=1;raw[8]=bytes(m[0x020013D0:0x020014D0]).index(ident);write(self.item,raw)
  at=0x02003BAC+20*ident;write(at,struct.pack('<I',m.u32[at]|0x40000000))
  self.label=next(r for r in self.build['fused_loss']['abilities'] if r['kind']==self.kind and r['bit']==self.bit)
  return (16 if self.kind else 20,0xFFFF if self.kind else 0xFFFFF,self.kind,3 if self.kind else 6)
 def event(self,owner,e,g,hero,actor,write,overrides):
  a,r=e['address'],e['registers']
  if a==0x08011156:
   overrides.append({'event':e,'r0_after':0,'reason':'Select the first eligible fused bit with valid native RNG result0.'});g.core.cpu.gprs[0]=0
  if a==0x08000FB8 and r[14]==0x08011207:
   require(r[3]==self.label['offset']+0x08000000 and r[2]==r[13]+0x100,'Fused loss native ability/name selection differs')
   if self.field.startswith('stress-'):
    raw=encode('i'*31 if self.field=='stress-bytes' else 'W'*27)
    if self.field=='stress-colour':raw=b'\x03\x05'+raw[:-1]+b'\x05\0'
    write(r[2],raw.ljust(64,b'\0'))
 def return_register(self,owner):return 1
 def returned(self,owner,g,hero,actor):
  expected=self.flags&~(1<<self.bit)&~0x200000
  if self.bit==0:expected&=0xFDFFFFFF
  require(g.core.memory.u32[self.item]==expected,'Native fused bit/property removal differs')
def verify(source=ROOT/'build/english'):
 build=json.loads((source/'build.json').read_text())
 return run(source,owners={'fused-loss':(0x110FC,0x11206,0x1120F,0x112BC,0,0x3AC)},resource_key='fused_loss',folder='fused-loss-validation',hooks=Loss(build))

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,default=ROOT/'build/english');verify(p.parse_args().source)
