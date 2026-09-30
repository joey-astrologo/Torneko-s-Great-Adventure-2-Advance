"""Native battle-result readers with decimal and actor/player name bounds."""
import argparse,struct
from pathlib import Path
from tools.emulator import ffi
from tools.rom import ROOT,require
from tools.name_entry import HERO
from tools.dialogue_checks import player_layout_cases
from tools.verify_player_notices import PlayerQueue
from tools.verify_dungeon_leaves import run as check
OWNERS={
 'absorption':(0xBCBC,0xC93E,0xC947,0xCC94,0x1C,0x7D0),
 'cop-out':(0xBCBC,0,0xBE2D,0xCC94,None,0x898),
 'area-monsters':(0x33BE8,0x33D40,0x33D49,0x33DC4,4,0x954),
 'area-priests':(0x33BE8,0x33D40,0x33D49,0x33DC4,4,0x958),
 'area-exp':(0x33BE8,0x33D68,0x33D71,0x33DC4,4,0x82C),
 'area-level':(0x33BE8,0x33D8E,0x33D97,0x33DC4,4,0x830),
 'spell-monsters':(0x40FD0,0x4175E,0x41767,0x41A40,0x138,0x954),
 'spell-priests':(0x40FD0,0x4175E,0x41767,0x41A40,0x138,0x958),
 'spell-exp':(0x40FD0,0x41788,0x41791,0x41A40,0x138,0x82C),
 'spell-level':(0x40FD0,0x417B2,0x417BB,0x41A40,0x138,0x830),
}
class Results:
    breakpoints=(0x0800BCCA,0x08033BF4,0x08040FDE);queue_checker=PlayerQueue
    scope='Nine numeric battle-result readers and one direct-ROM Cop Out announcement. Controlled native message blocks execute after their actual original prologues and return through original epilogues. Native table/format selections and numeric argument order retained; zero/max-nonnegative decimal substitutions are explicitly formatter-only, with maximum actor/player names and colours. Full256-byte output, field guards, ABI, one/two-line behavior, glyphs/final pixels and battery checked. Damage absorption, kill counts, XP/level changes and battle outcomes are not inferred from these message preflights.'
    def case_fields(self,owner):return ('native',) if owner=='cop-out' else ('native','maximum-width','maximum-bytes','coloured')
    def setup(self,owner,g,hero,actor,write,overrides):
        names=dict(player_layout_cases());name=names['widest-Japanese' if self.field=='maximum-width' else 'widest-English' if self.field=='maximum-bytes' else 'required-English'];write(HERO,name.ljust(16,b'\0'));return(hero,actor,0,0)
    def integer_value(self,owner,field,value):
        require(value==17,'Original controlled battle formatter value differs')
        return 0x7FFFFFFF if field in ('maximum-width','maximum-bytes') else 0 if field=='coloured' else value
    def event(self,owner,e,g,hero,actor,write,overrides):
        a,r=e['address'],e['registers'];m=g.core.memory
        def reg(index,value):overrides.append({'event':e,'register':index,'after':value});g.core.cpu.gprs[index]=value
        def jump(target,reason):overrides.append({'event':e,'pc_after':target+0x08000000,'reason':reason});require(g.core._core.writeRegister(g.core._core,b'pc',ffi.new('uint32_t*',target+0x08000000)),'Battle result block dispatch failed')
        prologue=0xBCCA if owner in ('absorption','cop-out') else 0x33BF4 if owner.startswith('area') else 0x40FDE
        if a==prologue+0x08000000:
            if owner=='absorption':reg(7,actor);reg(5,17);start=0xC922
            elif owner=='cop-out':start=0xBE1E
            elif owner.endswith(('monsters','priests')):
                area=owner.startswith('area');count_ptr=m.u32[0x08033DC8 if area else 0x080417D8];priest_ptr=m.u32[0x08033DD0 if area else 0x080417E0]
                write(count_ptr,struct.pack('<h',17));write(priest_ptr,bytes([int(owner.endswith('priests'))]));start=0x33D1A if area else 0x41736
            elif owner.endswith('exp'):
                if owner.startswith('area'):reg(10,17);start=0x33D58
                else:write(r[13]+0x23C,struct.pack('<I',17));start=0x41776
            else:reg(2,17);start=0x33D7E if owner.startswith('area') else 0x417A0
            jump(start,'Controlled original message block after full native prologue; gameplay calculation excluded.')
        if a==(OWNERS[owner][2]&~1)+0x08000000:jump(0xCC82 if owner in ('absorption','cop-out') else 0x33DB6 if owner.startswith('area') else 0x41A2C,'Native text completed; execute original epilogue without gameplay effects.')
    def return_register(self,owner):return 0 if owner.startswith('area') else 1
    def returned(self,*args):pass
    def verify_draws(self,owner,field,c):
        if owner=='cop-out' or owner.endswith(('monsters','exp')):require(c.queued['one_line'],'Bounded battle total should fit one line')

def run(source,only=None):check(source,only,owners=OWNERS,resource_key='battle_results',folder='battle-results-validation',hooks=Results())
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,default=ROOT/'build/english');p.add_argument('--only');a=p.parse_args();run(a.source,a.only)
