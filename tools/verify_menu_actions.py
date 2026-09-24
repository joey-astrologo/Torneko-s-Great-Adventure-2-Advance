"""Normal-input selection checks for the original-sized action menus."""
import json
import mgba.log
from tools.emulator import Session,Snapshot,Debugger
from tools.menu_checks import MenuChecks
from tools.audit_menu_layouts import Observer
from tools.rom import ROOT,digest,require

SLOTS=0x0200df28

def inventory(game):
    m=game.core.memory
    return [{'slot':i,'hex':bytes(m[SLOTS+i*120:SLOTS+i*120+12]).hex(),
             'flags':m.u32[SLOTS+i*120],'code':m.u8[SLOTS+i*120+8]} for i in range(24) if m.u32[SLOTS+i*120]&0x80000000]

def run():
    from tools.build_english import build_rom
    mgba.log.silence();rom,build=build_rom();out=ROOT/'build/english/menu-action-validation'
    fixture=Snapshot.load(ROOT/'build/english/mansion-validation/quest-room-entrance');rows=[]
    for name in ['unequip','unequip-interrupt-timing','equip-arrows','details','drop-pick-up','exchange']:
        with Session(rom,out/name) as game:
            print('Checking action',name,flush=True);game.restore(fixture);before=inventory(game);checks=MenuChecks(game,build['menus']);observer=Observer(game)
            def cb(e):observer.callback(e);checks.callback(e)
            with Debugger(game,cb,max_events=40000) as debug:
                for a in set(observer.ADDRESSES+checks.ADDRESSES):debug.breakpoint(a)
                opening_wait=120 if name=='unequip-interrupt-timing' else 240
                game.press('B',hold=8,wait=opening_wait);game.press('A',wait=opening_wait)
                index=2 if name.startswith('unequip') else (0 if name=='details' else 1)
                for _ in range(index):game.press('DOWN',wait=30)
                game.press('A',wait=opening_wait)
                if name=='details':
                    for _ in range(3):game.press('DOWN',wait=30)
                    n=len(observer.reads);game.press('A',wait=240);game.capture('details')
                    require(len(observer.reads)>n,'Info did not open item information')
                    require(inventory(game)==before,'Info changed inventory')
                elif name.startswith('unequip') or name=='equip-arrows':
                    game.press('A',wait=240);after=inventory(game)
                    changed=next(x for x in after if x['code']==before[index]['code'])
                    require(bool(changed['flags']&0x800000)==(name=='equip-arrows'),'Equip action did not update native flag')
                else:
                    game.press('DOWN',wait=30);game.press('DOWN',wait=30);game.press('A',wait=240)
                    dropped=inventory(game);require(len(dropped)==len(before)-1,'Drop did not remove one item')
                    game.press('B',hold=8,wait=240);game.press('DOWN',wait=30);game.press('A',wait=240)
                    if name=='exchange':
                        game.press('DOWN',wait=30);game.press('DOWN',wait=30);game.press('A',wait=240)
                        game.capture('exchange-selection');game.press('A',wait=240)
                        after=inventory(game)
                        require(len(after)==len(dropped) and any(x['code']==before[1]['code'] for x in after) and
                                not any(x['code']==before[0]['code'] for x in after),'Swap did not swap selected items')
                    else:
                        game.press('A',wait=240);after=inventory(game)
                        game.capture('pickup-result')
                        require(sorted(x['code'] for x in after)==sorted(x['code'] for x in before),'Take did not restore dropped item')
                game.capture('after')
            require(game.snapshot().battery==fixture.battery,'Action check wrote battery')
            rows.append({'case':name,'before':before,'after':inventory(game),'glyph_checks':checks.glyph_checks,
                         'reads':checks.reads,'inputs':game.inputs,'battery_unchanged':True})
    report={'passed':True,'rom_sha256':digest(rom),'cases':rows,'scope':'Ordinary inputs from a native English checkpoint; equip/unequip, Info, drop/pickup and Swap behavior.'}
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print('Menu action selections:',len(rows));return report
if __name__=='__main__':run()
