"""Native Remi root profiles: original geometry, cursor and cancellation."""
import argparse
from tools.service_validation import load_candidate
import json
import mgba.log
from tools.rom import digest, require
from tools.emulator import Session, Debugger, Snapshot
from tools.dialogue_checks import TextChecks
from tools.audit_menu_layouts import Observer
from tools.verify_remi import OUT


def run(cumulative=False):
    global OUT
    mgba.log.silence()
    OUT,rom,build=load_candidate('remi',cumulative)
    require(digest(rom)==build['output_sha256'],'Remi menu ROM differs')
    fixture=Snapshot.load(OUT/'native/entry'); require(fixture.rom_sha256==digest(rom),'Remi fixture differs')
    rows=build['remi']['entries']; resources={r['offset']+0x08000000:r for r in rows if r['layout']['direct_rom_stream']}
    results=[]
    for profile in range(5):
        for gate in (1,2):
            case=f'root-{profile}-gate-{gate}'; print('Remi menu:',case,flush=True)
            with Session(rom,OUT/case) as game:
                game.restore(fixture); m=game.core.memory; game.core.cpu.gprs[3]=profile
                address=m.u32[0x02001624]+0x88; before=m.u16[address];m.u16[address]=gate
                initial=[int(v)&0xffffffff for v in game.core.cpu.gprs]; guard=bytes(m[initial[13]:initial[13]+32])
                inventory=bytes(m[0x0200DF28:0x0200DF28+2400]);gold_address=m.u32[0x02001624]+0x60;gold=m.u32[gold_address]
                check=TextChecks(game,dict(resources));o=Observer(game);returned=[];images=[]
                expected=[201,204] if profile<2 else [201,204,202] if profile==2 else [201,204,202,203] if profile==3 else [201,204,202,203,205]
                if gate>1:expected.remove(204)
                def cb(e):
                    r=e['registers']
                    if e['address']==0x0801F062:
                        require(r[4:12]==initial[4:12] and r[13]==initial[13] and r[0]==initial[14]
                            and bytes(m[r[13]:r[13]+32])==guard,'Remi menu return ABI/guard differs')
                        returned.append(e)
                    check.callback(e);o.callback(e)
                def capture(name):game.capture(name);images.append(name+'.png')
                with Debugger(game,cb,max_events=160000) as debug:
                    for a in set(check.ADDRESSES+o.ADDRESSES+(0x0801F062,)):debug.breakpoint(a)
                    for _ in range(15):
                        game.frames(90)
                        if all(check.completed(f'remi.{i}') for i in expected) and not check.active:break
                        game.press('A',wait=0)
                    capture('root')
                    for i in range(len(expected)):
                        game.press('DOWN',wait=25);capture(f'cursor-{i}')
                    game.press('B',wait=90)
                    for _ in range(12):
                        if returned:break
                        game.press('A',wait=90)
                require(returned and not check.active and check.completed('remi.124'),'Remi cancellation incomplete')
                native=[r for r in o.reads if r['source'] in resources and resources[r['source']]['index'] in expected]
                require([resources[r['source']]['index'] for r in native]==expected,'Remi profile choices differ')
                for i,read in enumerate(native):
                    require((read['screen_x'],read['screen_y'],read['window_width'],read['rows'],read['initial_x'],read['initial_row'])==(8,24,112,len(expected),0,i),'Remi root geometry differs')
                    require([g['x'] for g in read['glyph_positions'][:3]]==[0,6,12],'Remi cursor padding differs')
                require(bytes(m[0x0200DF28:0x0200DF28+2400])==inventory and m.u32[gold_address]==gold and game.snapshot().battery==fixture.battery,'Remi cancellation changed inventory/gold/battery')
                results.append({'case':case,'controlled_overrides':[{'register':3,'before':4,'after':profile},{'address':address,'before':before,'after':gate}],
                    'expected_choices':expected,'reads':check.reads,'native_menu_reads':native,'glyph_checks':check.glyph_checks,'inputs':game.inputs,
                    'images':{p:digest((game.output/p).read_bytes()) for p in images}})
    (OUT/'menus.json').write_text(json.dumps({'passed':True,'rom_sha256':digest(rom),'cases':results,
        'scope':'Ten controlled Remi profiles/gate states. Original112px root,12px structural cursor reserve and100px labels; native movement through all rows and cancellation; complete caller ABI, inventory/gold/battery. Actual service selection and nested panels remain separate.'},indent=2)+'\n')
    print('Remi menus:',len(results),'cases passed',flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--cumulative',action='store_true');run(parser.parse_args().cumulative)
