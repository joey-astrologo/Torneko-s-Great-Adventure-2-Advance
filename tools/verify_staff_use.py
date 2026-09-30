"""Native staff announcements and empty-charge outcomes with complete names."""
import argparse,struct
from pathlib import Path
from tools.rom import ROOT,require
from tools.emulator import ffi
from tools.verify_dungeon_leaves import run as check
from tools.verify_monster_interactions import Interactions
OWNERS={
 'wave':(0x263F8,0x264A6,0x264AF,0x267DC,8,0x3D8),
 'empty':(0x263F8,0x264D6,0x264DF,0x267DC,8,0x228),
}
class StaffUse(Interactions):
    breakpoints=(0x08026410,0x080264AE)
    scope='Native staff-wave and zero-charge branches entered from the controlled Drink hook. The existing first inventory record and original selected-item getter are checked. Empty-staff flow completes normally. For the wave announcement, subsequent projectile targeting/effects are skipped to the original charge-decrement block so final text stays visible. All changes, inputs, names, output guards, native wraps, coloured pixels and caller/battery checks are recorded; ordinary targeting/effect outcomes are separate.'
    def setup(self,owner,g,hero,actor,write,overrides):
        m=g.core.memory;self.owner=owner;self.item=0x0200DF28
        item=bytearray(120);struct.pack_into('<I',item,0,0xC8000000);item[4:6]=bytes([3 if owner=='wave' else 0,1]);item[8]=bytes(m[0x020013D0:0x020014D0]).index(48);write(self.item,item)
        at=0x02003BAC+20*48;write(at,struct.pack('<I',m.u32[at]|0x40000000))
        write(hero+8,struct.pack('<I',(m.u32[hero+8]|0x4000) if owner=='wave' else m.u32[hero+8]&~0x4000))
        return(self.item,0,0,0)
    def event(self,owner,e,g,hero,actor,write,overrides):
        if e['address']==0x08026410:require(e['registers'][0]==self.item,'Native selected staff differs')
        if e['address']==0x080264AE and owner=='wave':
            overrides.append({'event':e,'pc_after':0x080267BA,'reason':'Preserve announcement for pixel checks; skip projectile targeting/effects and execute native charge decrement.'})
            require(g.core._core.writeRegister(g.core._core,b'pc',ffi.new('uint32_t*',0x080267BA)),'Staff effect skip failed')
    def field_address(self,owner,role,index,r,g):
        if role=='player':return super().field_address(owner,role,index,r,g)
        require(role=='item' and r[index]==r[13]+0x108,'Staff item-name scratch differs');return r[index]
    def returned(self,owner,g,hero,actor):require(g.core.memory.u8[self.item+4]==(2 if owner=='wave' else 0),'Staff use charge result differs')
    def verify_draws(self,owner,field,c):pass

def run(source,only=None):check(source,only,owners=OWNERS,resource_key='staff_use',folder='staff-use-validation',hooks=StaffUse())
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,default=ROOT/'build/staff-use-prototype');p.add_argument('--only');a=p.parse_args();run(a.source,a.only)
