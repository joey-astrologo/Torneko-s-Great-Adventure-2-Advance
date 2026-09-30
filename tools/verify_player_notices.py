"""Direct player-name controls, full recovery and empty staff-drain outcomes."""
import argparse,struct
from pathlib import Path
from tools.rom import ROOT,require
from tools.dialogue_checks import rendered_codes,player_layout_cases
from tools.inventory_action_text import CONTROL
from tools.name_entry import HERO
from tools.verify_service_ui import cstring
from tools.verify_inventory_action_prototype import ActionCheck
from tools.verify_dungeon_leaves import run as check
OWNERS={'no-staffs':(0x2F9C4,0,0x2FA3B,0x2FAB4,None,0x47C),'hp-status':(0x3CB64,0,0x3CBC5,0x3CBCA,None,0x9C0)}

class PlayerQueue(ActionCheck):
    def width(self,raw):
        m=self.game.core.memory
        return sum(self.glyph_record(c)[0]['advance'] for c in rendered_codes(raw+b'\0',bytes(m[HERO:HERO+16])))
    def callback(self,e):
        a,r=e['address'],e['registers'];m=self.game.core.memory
        if a==0x080158CE and self.queue_abi and self.queued is None:
            raw=cstring(m,r[6]);require(m.u32[r[13]+12]==self.queue_return and raw==self.expected_payload,'Player notice queue owner/bytes differ')
            if self.capacity:require(len(raw)+1<=self.capacity and bytes(m[r[6]+self.capacity:r[6]+self.capacity+16])==self.guard,'Player notice output guard differs')
            parts=raw.split(CONTROL) if CONTROL in raw else raw.split(b'\r');widths=[self.width(p) for p in parts]
            require(len(parts)<=2 and max(widths)<=216,'Player notice line bounds differ')
            if CONTROL in raw and sum(widths)<=215:widths=[sum(widths)]
            self.queued={'hex':raw.hex(),'line_widths':widths,'one_line':len(widths)==1,'bytes':len(raw)+1}
            self.expected=rendered_codes(raw.replace(CONTROL,b'')+b'\0',bytes(m[HERO:HERO+16]));self.window=0x02000000
        super().callback(e)

class Notices:
    breakpoints=();queue_checker=PlayerQueue
    scope='Native no-eligible-staff and full HP/status restoration handlers through controlled existing inventory/actor state. Required seven-letter English, widest English and widest Japanese player names run through the real7E renderer control. Native HP/strength/timer changes, empty-inventory preservation, immutable-ROM queues, one-line decisions, glyphs/pixels, caller ABI and battery pass. Natural encounters and skill availability remain separate.'
    def case_fields(self,owner):return tuple(n for n,_ in player_layout_cases())
    def setup(self,owner,g,hero,actor,write,overrides):
        m=g.core.memory;write(HERO,dict(player_layout_cases())[self.field].ljust(16,b'\0'))
        if owner=='no-staffs':
            write(0x0200DF28,bytes(2400));write(actor+8,struct.pack('<I',0x80000000));return(actor,0,0,0)
        write(hero+0x76,struct.pack('<HH',2,8));self.timers=(0x96,0xAB,0x98,0x95,0xA1,0x9F,0xA0,0x9E,0x9D)
        for offset in self.timers:write(hero+offset,b'\1')
        return(hero,0,0,0)
    def event(self,*args):pass
    def return_register(self,owner):return 0 if owner=='no-staffs' else 1
    def returned(self,owner,g,hero,actor):
        m=g.core.memory
        if owner=='no-staffs':require(bytes(m[0x0200DF28:0x0200DF28+2400])==bytes(2400),'No-staff branch changed inventory')
        else:require(m.u16[hero+0x84]==m.u16[hero+0x86] and m.u16[hero+0x76]==m.u16[hero+0x78] and all(m.u8[hero+o]==0 for o in self.timers),'Native HP/status restoration differs')

def run(source,only=None):check(source,only,owners=OWNERS,resource_key='player_notices',folder='player-notices-validation',hooks=Notices())
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,default=ROOT/'build/player-notices-prototype');p.add_argument('--only');a=p.parse_args();run(a.source,a.only)
