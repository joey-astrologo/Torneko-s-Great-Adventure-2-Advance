"""Owned item-loss and pot-result frames, fields and native visible output."""
import argparse,struct
from pathlib import Path
from tools.emulator import ffi
from tools.rom import ROOT,require
from tools.verify_dungeon_leaves import run as check
OWNERS={
 'skill-item':(0x287E8,0x2883C,0x28845,0x28860,0,0x1E0),
 'attack':(0xBCBC,0xC3B0,0xC3B9,0xCC94,0x11C,0x1E0),
 'floor':(0x14150,0x1429A,0x142A3,0x1430E,0,0x1E0),
 'warrior':(0x3D894,0x3E1EC,0x3E1F5,0x3E252,0x78,0x1E0),
 'skill':(0x3E278,0x3E7C8,0x3E7D1,0x3E804,0x108,0x1E0),
 'timer':(0x3E93C,0x3EA3E,0x3EA47,0x3EA6A,0,0x1E0),
 'pot-break':(0x38834,0x388A8,0x388B1,0x38D02,0x1C,0x1D8),
 'pot-explode':(0x38834,0x38CBE,0x38CC7,0x38D02,0x1C,0x34C),
}
# Preserve the actual prologue/epilogue and invoke its real name/format/queue
# block. These are render preflights, not reconstructed natural battle states.
BLOCKS={
 'attack':(0xBCCA,0xC392,0xCC82,6),
 'floor':(0x1415A,0x1427E,0x14302,6),
 'warrior':(0x3D8A2,0x3E1D0,0x3E240,None),
 'skill':(0x3E286,0x3E7A2,0x3E7F2,6),
 'timer':(0x3E948,0x3EA22,0x3EA5A,5),
 'pot-break':(0x38842,0x38888,0x38CEE,None),
 'pot-explode':(0x38842,0x38C9E,0x38CEE,None),
}
class Loss:
    breakpoints=tuple({0x08000000+b[0] for b in BLOCKS.values()})+(0x0805CF54,0x08028848)
    scope='Six independently owned loss readers and two pot announcements. The skill-item reader runs its actual assigned-skill predicate and native item removal. Other cases explicitly preserve their real prologue/epilogue and jump to the owned name/format/queue block, then skip remaining gameplay. The separate skill name-cache copy is skipped and recorded; no new global buffer claim is made. Full256-byte output/64-byte name guards, maximum names, one-line fit, colours, final pixels, caller ABI and battery are checked. Natural battle/skill/pot outcomes and the skipped global cache remain separate.'
    def setup(self,owner,g,hero,actor,write,overrides):
        self.owner=owner;self.item=0x0200DF28+120;self.removed=False;m=g.core.memory
        ident=162 if owner=='pot-explode' else 154 if owner=='pot-break' else 1
        item=bytearray(120);struct.pack_into('<I',item,0,0xC8000000);item[4:6]=b'\3\1' if owner.startswith('pot') else b'\0\1';item[8]=bytes(m[0x020013D0:0x020014D0]).index(ident);write(self.item,item)
        at=0x02003BAC+20*ident;write(at,struct.pack('<I',m.u32[at]|0x40000000))
        if owner=='skill-item':write(0x02004CF0+3*ident,b'\1\0\0')
        return(self.item,0,0,0)
    def event(self,owner,e,g,hero,actor,write,overrides):
        if owner=='skill-item' and e['address']==0x08028848:
            require(g.core.memory.u32[self.item]==0,'Native skill-item clear differs');self.removed=True
        if owner not in BLOCKS:return
        a,r=e['address'],e['registers'];prologue,start,epilogue,register=BLOCKS[owner]
        def jump(target,reason):
            overrides.append({'event':e,'pc_after':target+0x08000000,'reason':reason});require(g.core._core.writeRegister(g.core._core,b'pc',ffi.new('uint32_t*',target+0x08000000)),'Item loss controlled block dispatch failed')
        if a==prologue+0x08000000:
            if register is not None:g.core.cpu.gprs[register]=self.item;overrides.append({'event':e,'register':register,'after':self.item})
            if owner=='warrior':write(r[13]+0x3A4,struct.pack('<I',self.item));write(r[13]+0x3F0,struct.pack('<I',r[13]+0x78))
            if owner=='timer':write(r[13]+0x140,bytes(4))
            if owner.startswith('pot'):write(r[13]+0x644,struct.pack('<I',self.item))
            jump(start,'Controlled rendering entry after original full prologue; natural event conditions/gameplay are outside this preflight.')
        if a==(OWNERS[owner][2]&~1)+0x08000000:jump(epilogue,'Native message completed; retain final pixels and execute original full epilogue, excluding gameplay outcome.')
        if owner=='skill' and a==0x0805CF54 and r[14]==0x0803E7B5:jump(0x3E7B4,'Skip separate global name-cache write; the owned stack name was produced natively and its message still executes.')
    def field_address(self,owner,role,index,r,g):
        offset={'skill-item':0x100,'attack':0x21C,'floor':0x100,'warrior':0x178,'skill':0x208,'timer':0x100,'pot-break':0x11C,'pot-explode':0x11C}[owner]
        require(role=='item' and r[index]==r[13]+offset,'Loss item field ownership differs');return r[index]
    def return_register(self,owner):return 1 if owner in ('attack','floor','timer','pot-break','pot-explode') else 0
    def returned(self,owner,g,hero,actor):
        # The subsequent10228 inventory cleanup can move another record into
        # this slot, so verify the actual removal before that cleanup.
        if owner=='skill-item':require(self.removed,'Native skill-item removal was not observed')
    def verify_draws(self,owner,field,c):require(c.queued['one_line'],'Item loss/breakage maximum should fit one line')

def run(source,only=None):check(source,only,owners=OWNERS,resource_key='item_loss',folder='item-loss-validation',hooks=Loss())
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,default=ROOT/'build/item-loss-prototype');p.add_argument('--only');a=p.parse_args();run(a.source,a.only)
