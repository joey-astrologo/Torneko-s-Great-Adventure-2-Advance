"""Native item discovery, monster revelation/transformation and decoy timers."""
import argparse,struct
from pathlib import Path
from tools.rom import ROOT,require,load_base
from tools.emulator import ffi
from tools.verify_dungeon_leaves import run as check
OWNERS={
 'grab-six':(0x2C258,0x2C354,0x2C35D,0x2C366,0x1C,0x35C),
 'grab-five':(0x2C258,0x2C354,0x2C35D,0x2C366,0x1C,0x35C),
 'monster-reveal':(0x29EB8,0x29FC2,0x29FCB,0x2A01A,0,0x7E0),
 'actor-transform':(0x39928,0x399DA,0x399E3,0x399E8,0,0x230),
 'identify-use':(0x32E4C,0x32EB6,0x32EBF,0x32ECA,0x80,0x74),
 'identify-scroll':(0x33B10,0x33BD0,0x33BDB,0x33BE0,0x80,0x74),
 'identify-spell':(0x40B7C,0x40C14,0x40C1D,0x40C22,0,0x74),
 'identify-all':(0x33B10,0x33B6C,0x33BDB,0x33BE0,0x80,0x1AC),
 'decoy-form':(0x2D5C8,0x2D982,0x2D9B5,0x2DE7C,0,0x9C8),
 'decoy-other':(0x2D5C8,0x2D9AC,0x2D9B5,0x2DE7C,0,0x95C),
}

class Discovery:
    breakpoints=(0x08039954,0x08033B1A,0x08033B22,0x08033B28,0x08040B86,0x0802D940)
    allow_scrolled=True
    scope='Ten native identification/revelation/transformation/grabbing/decoy branches. Controlled existing items/actor fields and RNG/selection values are recorded. Native knowledge flags, species changes, grabbing state and decoy expiry are checked. Sprite movement in the decoy path is skipped before timer expiry, with full caller ABI retained. Two conditional breaks can scroll three synthetic maximum-field lines in the two-row log; every glyph is checked while drawn and final pixels cover visible rows. Other consumers and ordinary acquisition/encounters remain separate.'
    def setup(self,owner,g,hero,actor,write,overrides):
        m=g.core.memory;self.owner=owner;self.actor=actor;self.target=0x0200DF28+120
        write(actor+8,struct.pack('<I',0x80000000));write(actor+0x91,bytes([6 if owner=='grab-six' else 5 if owner=='grab-five' else 1]));write(actor+0x95,bytes(12));write(actor+0xA9,b'\0')
        if owner.startswith('grab'):
            write(hero+0xA3,b'\0');return(actor,0,0,0)
        if owner=='monster-reveal':
            pointer=m.u32[m.u32[0x08029EFC]+0x30]+28*m.u8[actor+0x91]+0x13;write(pointer,b'\1');self.species_flag=pointer;return(actor,0,0,0)
        if owner=='actor-transform':return(actor,0,0,0)
        if owner.startswith('identify'):
            item=bytearray(120);struct.pack_into('<I',item,0,0x80000000);item[4:6]=b'\1\1';item[8]=bytes(m[0x020013D0:0x020014D0]).index(169);write(self.target,item)
            at=0x02003BAC+20*169;write(at,struct.pack('<I',m.u32[at]&~0x40000000));self.knowledge=at
            return(self.target,0,0,0)
        if owner.startswith('decoy'):
            write(actor+0x91,bytes([140 if owner=='decoy-form' else 1]));write(actor+0xA9,b'\1')
            self.decoy_pointer=m.u32[0x0802D984];self.original_pointer=m.u32[0x0802D988]
            write(self.decoy_pointer,struct.pack('<I',actor));write(self.original_pointer,struct.pack('<I',hero));return(actor,0,0,0)
        raise ValueError(owner)
    def event(self,owner,e,g,hero,actor,write,overrides):
        a,r=e['address'],e['registers'];m=g.core.memory
        if a==0x08039954 and owner=='actor-transform':
            overrides.append({'event':e,'register':0,'after':2,'reason':'Choose valid native species2, distinct from original1 and excluded87.'});g.core.cpu.gprs[0]=2
        for at,value,reason in [(0x08033B1A,self.target,'Choose existing inventory item through original selector return.'),(0x08033B22,0 if owner=='identify-all' else 98,'Select native all-items/one-item RNG branch.'),(0x08033B28,1,'Control one eligible selection to retain the native RNG decision.')]:
            if a==at and owner in ('identify-all','identify-scroll'):overrides.append({'event':e,'register':0,'after':value,'reason':reason});g.core.cpu.gprs[0]=value
        if owner=='decoy-form' or owner=='decoy-other':
            if a==0x08029B24 and r[0]==actor:
                overrides.append({'event':e,'pc_after':r[14]&~1,'reason':'Skip visual decoy movement only; native timer decrement, reset and message still run.'});require(g.core._core.writeRegister(g.core._core,b'pc',ffi.new('uint32_t*',r[14]&~1)),'Decoy movement skip failed')
    def field_address(self,owner,role,index,r,g):
        if role=='actor':return 0x02008D08  # Existing getter scratch; level1 may originally return its immutable ROM name.
        sp=r[13]
        expected=sp+0x100 if owner=='actor-transform' else sp+0x100+(index-2)*64 if owner=='identify-spell' else sp+(index-2)*64
        require(r[index]==expected,'Identification name scratch differs');return expected
    def verify_draws(self,owner,field,c):
        if hasattr(c,'breaks'):
            require(len(c.breaks)==2,'Discovery native break count differs');c.queued['one_line']=not any(b['wraps'] for b in c.breaks)
            if field=='native' and owner in ('identify-use','identify-scroll','identify-spell','actor-transform'):require(c.queued['one_line'],'Ordinary discovery should fit one line')
    def return_register(self,owner):return 0
    def returned(self,owner,g,hero,actor):
        m=g.core.memory
        if owner.startswith('grab'):require(m.u8[hero+0xA3]==(99 if owner=='grab-six' else 98) and m.u32[hero+0xC0]==actor and m.u32[actor+8]&0x40,'Native grabbing state differs')
        if owner=='monster-reveal':require(m.u8[self.species_flag]==0,'Native monster revelation flag unchanged')
        if owner=='actor-transform':require(m.u8[actor+0x91]==2,'Native transformation species differs')
        if owner.startswith('identify'):require(m.u32[self.knowledge]&0x40000000,'Native item identification did not mark type known')
        if owner.startswith('decoy'):require(m.u8[actor+0xA9]==0 and m.u32[self.decoy_pointer]==hero,'Native decoy expiry differs')


def run(source,only=None):
    hooks=Discovery();hooks.breakpoints=hooks.breakpoints+(0x08029B24,)
    check(source,only,owners=OWNERS,resource_key='discovery_messages',folder='discovery-messages-validation',hooks=hooks)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,default=ROOT/'build/discovery-prototype');p.add_argument('--only');a=p.parse_args();run(a.source,a.only)
