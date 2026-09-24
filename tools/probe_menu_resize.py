"""Native early-menu feasibility from a cold, genuine Japanese suspend."""
import json
import mgba.log
from tools.audit_menu_layouts import Observer,parent_image,CASES
from tools.emulator import Session,Debugger,Snapshot
from tools.menu_text import prototype
from tools.menu_checks import MenuChecks
from tools.compact_font import load_font,COMPACT_ASSET
from tools.rom import ROOT,require,digest
from tools.trace_mansion import SourceTrace,finish
from tools.mansion_playtest import walk_to_stairs
from tools.name_entry_playtest import MAP

OUT=ROOT/'build/menu-resize/prototype'

def cold_fixture(rom,out):
    battery=(ROOT/'build/mansion/native/floor-five-native.sav').read_bytes()
    with Session(rom,out,initial_save=battery) as game:
        trace=SourceTrace(game)
        with Debugger(game,trace.callback,max_events=80000) as debug:
            for a in trace.ADDRESSES:debug.breakpoint(a)
            game.frames(600);game.press('START',wait=180);game.frames(204)
            finish(game,trace,'rom.0006afe0','cold-resume');game.press('A',wait=120)
            require(game.core.memory.u16[0x02005674]==6,'Did not resume on 6F')
        game.capture('quest-room');game.snapshot().save(out/'quest-room')
        (out/'cold-inputs.json').write_text(json.dumps({'rom_sha256':digest(rom),'save_sha256':digest(battery),'inputs':game.inputs},indent=2)+'\n')
    return Snapshot.load(out/'quest-room')


def run(english=False):
    mgba.log.silence()
    if english:
        from tools.build_english import build_rom
        rom,build=build_rom();menus=build['menus'];out=ROOT/'build/english/menu-validation'
        fixture=Snapshot.load(ROOT/'build/english/mansion-validation/quest-room-entrance')
    else:
        rom,menus=prototype();out=OUT;fixture=cold_fixture(rom,out)
    routes=[]
    for name,_,actions in CASES:
        if name=='bank':continue
        with Session(rom,out/name) as game:
            game.restore(fixture);observer=Observer(game);checks=MenuChecks(game,menus,load_font(COMPACT_ASSET));cursors=[];parents=[];stacks=[];pending=[]
            def callback(e):
                a,r=e['address'],e['registers'];m=game.core.memory
                observer.callback(e);checks.callback(e)
                if a==0x0801570c:cursors.append({'frame':e['frame'],'x':r[0],'y':r[1]})
                if a==0x08019184:pending.append((r[13],r[4:12],bytes(m[r[13]:r[13]+32])))
                if a==0x080194aa:
                    sp,regs,guard=pending.pop();require(r[13]==sp and r[4:12]==regs and bytes(m[sp:sp+32])==guard,'Action producer damaged stack/callee registers')
                    stacks.append({'sp':sp,'preserved':True})
            with Debugger(game,callback,max_events=60000) as debug:
                for a in set(observer.ADDRESSES+checks.ADDRESSES+(0x0801570c,)):debug.breakpoint(a)
                for i,action in enumerate(actions):
                    if name.startswith('inventory-') and i==len(actions)-1:
                        baseline=parent_image(game);game.capture('parent-before-open')
                    key,hold=action if isinstance(action,tuple) else (action,3)
                    game.press(key,hold=hold,wait=240);game.capture(f'step-{i:02}')
                game.capture('menu');menu_end=len(observer.reads)
                if name.startswith('inventory-'):
                    for cycle in range(3):
                        game.press('DOWN',wait=30);game.press('UP',wait=30)
                        game.press('B',wait=120);after=parent_image(game)
                        parents.append({'cycle':cycle,'preserved':after==baseline,'before':baseline,'after':after})
                        game.capture(f'parent-after-{cycle}')
                        if cycle<2:game.press('A',wait=120)
            routes.append({'id':name,'menu_read_count':menu_end,'capture':str((game.output/'menu.png').relative_to(ROOT)),'reads':observer.reads,'creates':observer.creates,'cursors':cursors,'stack_checks':stacks,'glyph_checks':checks.glyph_checks,'checked_reads':checks.reads,'producer_checks':checks.producer_stacks,'parent_checks':parents,'inputs':game.inputs})
    border_checks=[]
    for route in routes:
        reads=route['reads'][:route['menu_read_count']]
        # Native borders extend four pixels beyond each content rectangle.
        root=[r for r in reads if r['screen_x']==8 and r['window_width']==40 and r['initial_x']==6]
        banner=[r for r in reads if r['screen_x']==64 and r['window_width']==168]
        require(root and banner,'Original main-menu/banner geometry missing')
        gap=banner[-1]['screen_x']-4-(root[-1]['screen_x']+root[-1]['window_width']+4)
        require(gap==8,'Main-menu border gap changed')
        border_checks.append({'route':route['id'],'panels':'main/banner','gap_px':gap})
        if route['id'].startswith('inventory-') or route['id']=='ground-arrows':
            parent=[r for r in reads if r['screen_x']==8 and r['window_width']==168]
            action=[r for r in reads if r['screen_x']==192 and r['window_width']==40 and r['initial_x']==4]
            require(parent and action,'Original item/action geometry missing')
            gap=action[-1]['screen_x']-4-(parent[-1]['screen_x']+parent[-1]['window_width']+4)
            require(gap==8,'Item/action border gap changed')
            border_checks.append({'route':route['id'],'panels':'item/actions','gap_px':gap})
    report={'passed':all(p['preserved'] for r in routes for p in r['parent_checks']),
            'border_checks':border_checks,
            'rom_sha256':digest(rom),'source_rom_sha256':digest(__import__('tools.rom',fromlist=['load_base']).load_base()),'routes':routes,'scope':'Cold native suspend continuation; ordinary menu buttons, no RAM or state injection.'}
    (out/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print('Parent preservation:',[(r['id'],[p['preserved'] for p in r['parent_checks']]) for r in routes])
    return report
if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--english',action='store_true');run(p.parse_args().english)
