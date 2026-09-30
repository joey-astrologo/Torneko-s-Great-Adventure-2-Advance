"""Native staff charge removal and player pull, including three format arguments."""
import argparse,struct
from pathlib import Path
from tools.rom import ROOT,require
from tools.verify_dungeon_leaves import run as check
from tools.verify_player_messages import player_layout_cases,HERO
OWNERS={
 'staff-drain':(0x2F9C4,0x2FA8A,0x2FA93,0x2FAB4,0x54,0x478),
 'pull-player':(0x3181C,0x31882,0x3188B,0x3191A,0,0x470),
}

class Interactions:
    breakpoints=(0x0802FA4E,)
    allow_scrolled=True
    scope='Controlled native staff-draining and player-pulling handlers from Drink. Existing actor/inventory state and staff selection RNG are recorded. Actual charge decrement and player movement execute. Synthetic field cases preserve the real seven-character player-name capacity and the third outgoing stack argument. Native conditional wrapping, glyphs, visible pixels, guards, ABI and battery are checked; ordinary AI encounters remain separate.'
    def setup(self,owner,g,hero,actor,write,overrides):
        m=g.core.memory;self.owner=owner;self.item=0x0200DF28+120
        write(actor+8,struct.pack('<I',0x80000000));write(actor+0x91,b'\1');write(actor+0x95,bytes(12))
        if owner=='staff-drain':
            write(0x0200DF28,bytes(2400));item=bytearray(120);struct.pack_into('<I',item,0,0xC8000000);item[4:6]=b'\3\1';item[8]=bytes(m[0x020013D0:0x020014D0]).index(48);write(self.item,item)
            at=0x02003BAC+20*48;write(at,struct.pack('<I',m.u32[at]|0x40000000))
        else:
            # Native facing vector and existing dungeon position determine destination.
            table=m.u32[0x08031920]+8*m.u8[actor+0x42]
            self.destination=tuple(m.s16[actor+0x66+i*2]+m.s32[table+i*4] for i in range(2))
        return(actor,0,0,0)
    def event(self,owner,e,g,hero,actor,write,overrides):
        if e['address']==0x0802FA4E and owner=='staff-drain':
            overrides.append({'event':e,'register':0,'after':0,'reason':'Select the sole eligible staff through the original RNG result.'});g.core.cpu.gprs[0]=0
    def field_capacity(self,role):return 16 if role=='player' else 64
    def field_data(self,role,field,raw):
        if role=='player':return dict(player_layout_cases())['widest-Japanese' if field=='maximum-width' else 'widest-English' if field=='maximum-bytes' else 'required-English']
        return raw
    def field_address(self,owner,role,index,r,g):
        if role=='actor':return 0x02008D08
        if role=='player':require(r[index]==HERO,'Native player getter differs');return HERO
        at=g.core.memory.u32[r[13]];require(owner=='staff-drain' and index==4 and at==r[13]+0x154,'Staff field scratch differs');return at
    def return_register(self,owner):return 0
    def returned(self,owner,g,hero,actor):
        m=g.core.memory
        if owner=='staff-drain':require(m.u8[self.item+4]==2,'Native staff charge was not decremented')
        else:require(tuple(m.s16[hero+0x66+i*2] for i in range(2))==self.destination,'Native pull destination differs')
    def verify_draws(self,owner,field,c):
        if hasattr(c,'breaks'):require(len(c.breaks)==2,'Staff drain conditional-break count differs')

def run(source,only=None):check(source,only,owners=OWNERS,resource_key='monster_interactions',folder='monster-interactions-validation',hooks=Interactions())
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,default=ROOT/'build/monster-interactions-prototype');p.add_argument('--only');a=p.parse_args();run(a.source,a.only)
