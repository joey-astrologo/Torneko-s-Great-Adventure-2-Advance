"""Controlled full-inventory, seven-row/disabled and alternate main-menu checks."""
import json
import mgba.log
from tools.audit_menu_layouts import Observer,parent_image
from tools.emulator import Session,Snapshot,Debugger
from tools.menu_checks import MenuChecks
from tools.rom import ROOT,digest,require
from tools.menu_text import ROOT_POINTERS
from tools.name_entry_playtest import MAP,position


def run():
    from tools.build_english import build_rom
    mgba.log.silence();rom,build=build_rom();out=ROOT/'build/english/menu-edge-validation'
    fixture=Snapshot.load(ROOT/'build/english/mansion-validation/quest-room-entrance');rows=[]
    cases=[('full-inventory',None,None),('full-ground',None,None),('seven-disabled',None,None)]+[(f'root-mode-{mode}-{ground}',mode,ground) for mode in range(3) for ground in ['ground','stairs','trap']]
    for name,mode,ground in cases:
        with Session(rom,out/name) as game:
            game.restore(fixture);m=game.core.memory;checks=MenuChecks(game,build['menus']);observer=Observer(game)
            if mode is not None:m.u8[m.u32[0x02001624]+0x90]=mode
            if name in ('full-inventory','full-ground'):
                source=bytes(m[0x0200df28:0x0200df28+120])
                for slot in range(4,20):
                    for i,b in enumerate(source):m.u8[0x0200df28+slot*120+i]=b
            def cb(e):
                a,r=e['address'],e['registers']
                if name=='seven-disabled' and a==0x080193e2:
                    for i in range(7):m.u16[0x0200cdd0+i*2]=0x86
                if ground and a==0x08000fb8 and r[14] in (0x08019d33,0x08019d43):
                    site={'ground':0x19d94,'stairs':0x19d18,'trap':0x19d34}[ground]
                    ptr=next(0x8000000+x['offset'] for x in build['menus']['entries'] if x['id']==f'root.{site:06x}')
                    game.core.cpu.gprs[1]=ptr;game.core.cpu.gprs[2]=2
                    e=dict(e,registers=r[:]);e['registers'][1:3]=[ptr,2]
                observer.callback(e);checks.callback(e)
            with Debugger(game,cb,max_events=50000) as debug:
                for a in set(checks.ADDRESSES+observer.ADDRESSES+(0x080193e2,)):debug.breakpoint(a)
                game.press('B',hold=8,wait=120)
                if mode is None:
                    game.press('A',wait=120)
                    if name=='full-ground':
                        game.press('DOWN',wait=30);game.press('A',wait=240)
                        game.press('DOWN',wait=30);game.press('DOWN',wait=30);game.press('A',wait=240)
                        # Restore capacity after the normal drop in this controlled
                        # case, then let the native ground menu enforce its limit.
                        free=[i for i in range(20) if not m.u32[0x0200df28+i*120]&0x80000000]
                        require(len(free)==1,'Expected one free slot after drop')
                        for i,b in enumerate(source):m.u8[0x0200df28+free[0]*120+i]=b
                        game.press('B',hold=8,wait=240);game.press('DOWN',wait=30);game.press('A',wait=240)
                        game.capture('menu')
                        require(checks.materialized[-1]['ids'][0]&127==18,'Ground first action is not Take')
                        before_items=bytes(m[0x0200df28:0x0200df28+20*120])
                        x,y=position(game);ground_ptr=m.u32[MAP+(x*32+y)*28+16]
                        require(ground_ptr!=0,'Dropped item is missing')
                        ground_before=bytes(m[ground_ptr:ground_ptr+120])
                        game.press('A',wait=240);game.capture('full-pickup-result')
                        require(bytes(m[0x0200df28:0x0200df28+20*120])==before_items,'Full-inventory Take changed carried items')
                        require(bytes(m[ground_ptr:ground_ptr+120])==ground_before,'Full-inventory Take changed ground item')
                        require(sum(bool(m.u32[0x0200df28+i*120]&0x80000000) for i in range(20))==20,'Full inventory count changed')
                    else:
                        inventory_case(game,name,checks)
                else:game.capture('menu');game.press('B',wait=120)
            require(checks.reads and not checks.active,'Incomplete menu edge checks')
            if name=='seven-disabled':require(any(len(x['ids'])==7 and x['bytes']==112 for x in checks.materialized),'Worst seven-row stream missing')
            rows.append({'case':name,'reads':checks.reads,'glyph_checks':checks.glyph_checks,'producer_checks':checks.producer_stacks,
                         'materialized':checks.materialized,'formats':checks.formats,'inputs':game.inputs,'controlled':True,
                         'scope':'Synthetic menu arguments/item state; not later-mode gameplay acceptance.'})
    report={'passed':True,'rom_sha256':digest(rom),'cases':rows,'scope':'Controlled extremes; separate from ordinary-input route acceptance.'}
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print('Menu edges:',len(rows),'cases');return report

def inventory_case(game,name,checks):
    if name=='full-inventory':game.press('RIGHT',wait=120);game.press('RIGHT',wait=120)
    before=parent_image(game);game.press('A',wait=120);game.capture('menu')
    for _ in range(7 if name=='seven-disabled' else 4):game.press('DOWN',wait=15)
    if name=='seven-disabled':
        game.press('A',wait=30)
        require(game.core.memory.u32[0x0200cd20]!=0,'Disabled action unexpectedly closed menu')
    game.press('B',wait=120);require(parent_image(game)==before,'Edge case failed parent restoration')
if __name__=='__main__':run()
