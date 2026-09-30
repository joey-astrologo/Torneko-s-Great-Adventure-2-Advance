"""All skill-name selectors through the four original attack-announcement blocks."""
import argparse,struct
from pathlib import Path
from tools.emulator import ffi
from tools.rom import ROOT,require
from tools.verify_dungeon_leaves import run as check
OWNERS={
 'attack':(0x3D894,0x3DAF4,0x3DB45,0x3E252,0x80,0x774),
 'finisher':(0x3D894,0x3DB3C,0x3DB45,0x3E252,0x80,0x764),
 'retaliation':(0x3D894,0x3DF78,0x3DFC3,0x3E252,0x2A0,0x774),
 'retaliation-finisher':(0x3D894,0x3DFBA,0x3DFC3,0x3E252,0x2A0,0x764),
}
class Shouts:
    breakpoints=(0x0803D8A2,)
    scope='All128 skill-name selectors through four independently owned native format/queue blocks. Original408hex-byte frame and256-byte output regions atSP+80/SP+2A0 retained. Explicit message-block dispatch after the actual prologue, followed by original epilogue; attack conditions and skill effects excluded. Complete English names, exact native indexed definition pointers, one-line fit, field/stack guards, ABI, visible glyphs/pixels and battery checked.'
    def case_fields(self,owner):return tuple(str(i) for i in range(128))
    def field_capacity(self,role):require(role=='skill','Unexpected skill shout field');return 49
    def setup(self,owner,g,hero,actor,write,overrides):self.ident=int(self.field);return(hero,0,0,0)
    def event(self,owner,e,g,hero,actor,write,overrides):
        a,r=e['address'],e['registers'];m=g.core.memory
        def reg(index,value):overrides.append({'event':e,'register':index,'after':value});g.core.cpu.gprs[index]=value
        def jump(target,reason):overrides.append({'event':e,'pc_after':target+0x08000000,'reason':reason});require(g.core._core.writeRegister(g.core._core,b'pc',ffi.new('uint32_t*',target+0x08000000)),'Skill shout block dispatch failed')
        if a==0x0803D8A2:
            if owner in ('attack','finisher'):reg(8,self.ident)
            else:
                reg(2,self.ident);reg(4,m.u32[0x0803DFA0]);reg(5,m.u32[0x0803DF9C]);reg(7,m.u32[0x0803DF9C]-16)
            jump({'attack':0x3DAD8,'finisher':0x3DB24,'retaliation':0x3DF66,'retaliation-finisher':0x3DFA8}[owner],'Render original skill-message block after full native prologue; natural attack selection excluded.')
        if a==0x08000FB8 and r[14]==OWNERS[owner][1]+0x08000001:
            base=m.u32[0x0803DB20 if owner=='attack' else 0x0803DC08 if owner=='finisher' else 0x0803DFA0]
            require(r[2]==m.u32[base+36*self.ident],'Native skill shout name selector differs')
        if a==(OWNERS[owner][2]&~1)+0x08000000:jump(0x3E240,'Native announcement completed; original epilogue returns without skill effects.')
    def return_register(self,owner):return 0
    def returned(self,*args):pass
    def verify_draws(self,owner,field,c):require(c.queued['one_line'],'Skill shouts must fit one line')

def run(source,only=None):check(source,only,owners=OWNERS,resource_key='skill_messages',folder='skill-shouts-validation',hooks=Shouts())
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,default=ROOT/'build/english');p.add_argument('--only');a=p.parse_args();run(a.source,a.only)
