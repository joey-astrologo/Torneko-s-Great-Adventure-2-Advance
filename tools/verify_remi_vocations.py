"""Original-sized vocation choices and native change/decline transactions."""
import argparse
from tools.service_validation import load_candidate
import json
import mgba.log
from tools.rom import digest,require
from tools.emulator import Session,Debugger,Snapshot
from tools.audit_menu_layouts import Observer
from tools.remi_checks import RemiChecks
from tools.verify_remi import OUT


def run(cumulative=False):
    global OUT
    mgba.log.silence();OUT,rom,build=load_candidate('remi',cumulative)
    require(digest(rom)==build['output_sha256'],'Remi vocation ROM differs')
    fixture=Snapshot.load(OUT/'native/entry');results=[]
    for vocation in range(3):
        for action in ('cancel','leave','first-no','second-no','first-yes','second-yes'):
            case=f'vocation-{vocation}-{action}';print('Remi:',case,flush=True)
            with Session(rom,OUT/case) as game:
                game.restore(fixture);m=game.core.memory;va=m.u32[0x02001624]+0x90;before=m.u8[va];m.u8[va]=vocation
                initial=[int(v)&0xffffffff for v in game.core.cpu.gprs];guard=bytes(m[initial[13]:initial[13]+32])
                ga=m.u32[0x02001624]+0x60;gold=m.u32[ga];inventory=bytes(m[0x0200DF28:0x0200DF28+2400])
                check=RemiChecks(game,build);o=Observer(game);choices=[];returned=[];images=[]
                def capture(name):game.capture(name);images.append(name+'.png')
                def cb(e):
                    r=e['registers']
                    if e['address']==0x0801EDA2:choices.append(r[0])
                    if e['address']==0x0801F062:
                        require(r[4:12]==initial[4:12] and r[13]==initial[13] and r[0]==initial[14]
                            and bytes(m[r[13]:r[13]+32])==guard,'Remi vocation ABI/guard differs')
                        returned.append(e)
                    check.callback(e);o.callback(e)
                def count(ident):return sum(r['id']==ident for r in check.reads)
                def reach(ident,n=1,key='A'):
                    for _ in range(24):
                        game.frames(90)
                        if count(ident)>=n and not check.active:return
                        game.press(key,wait=0)
                    raise ValueError('Remi vocation did not reach '+ident)
                with Debugger(game,cb,max_events=180000) as d:
                    for a in set(check.ADDRESSES+o.ADDRESSES+(0x0801EDA2,0x0801F062)):d.breakpoint(a)
                    reach('remi.205');capture('root')
                    for _ in range(4):game.press('DOWN',wait=25)
                    game.press('A',wait=90);reach(f'remi.{154+vocation}');capture('choices')
                    if action=='cancel':game.press('B',wait=90)
                    elif action=='leave':
                        game.press('DOWN',wait=25);game.press('DOWN',wait=25);capture('leave-selected');game.press('A',wait=90)
                    else:
                        if action.startswith('second'):game.press('DOWN',wait=25)
                        capture('vocation-selected');game.press('A',wait=90);reach('remi.160');capture('confirmation')
                        game.press('A' if action.endswith('yes') else 'B',wait=90)
                    reach('remi.205',2);capture('reopened');game.press('B',wait=90)
                    for _ in range(12):
                        if returned:break
                        game.press('A',wait=90)
                choice=(1 if action.startswith('second') else 0)
                expected=[[1,2],[0,2],[0,1]][vocation][choice] if action.endswith('yes') else vocation
                require(m.u8[va]==expected and returned and not check.active and not check.pending,'Remi vocation result incomplete/different')
                require(choices==[0xffffffff if action=='cancel' else 2 if action=='leave' else choice],'Remi vocation selection order differs')
                menu=next(r for r in build['remi']['entries'] if r['index']==154+vocation)
                native=[r for r in o.reads if r['raw_hex']==menu['encoded_hex']]
                require(len(native)==1 and native[0]['window_width']==72 and native[0]['rows']==3 and native[0]['initial_x']==0,'Remi vocation menu geometry differs')
                for line in range(3):
                    glyphs=[g for g in native[0]['glyph_positions'] if g['row']==line]
                    require([g['x'] for g in glyphs[:3]]==[0,6,12],'Remi vocation cursor reserve differs')
                require(bytes(m[0x0200DF28:0x0200DF28+2400])==inventory and m.u32[ga]==gold and game.snapshot().battery==fixture.battery,'Vocation service changed items/gold/battery')
                results.append({'case':case,'overrides':[{'address':va,'before':before,'after':vocation}],
                    'selection':choices,'vocation_before':vocation,'vocation_after':expected,'formats':check.formats,'reads':check.reads,
                    'native_menu_reads':native,'glyph_checks':check.glyph_checks,'inputs':game.inputs,
                    'images':{p:digest((game.output/p).read_bytes()) for p in images}})
    (OUT/'vocations.json').write_text(json.dumps({'passed':True,'rom_sha256':digest(rom),'cases':results,
        'scope':'Three controlled current vocations; cancel, Leave and each offered vocation with both confirmation answers. Eighteen native service cases retain72px/three-row menus with12px cursor reserve, change the original vocation byte only when confirmed, and preserve caller ABI, inventory/gold/battery. Ordinary availability/unlocking is separate.'},indent=2)+'\n')
    print('Remi vocations:',len(results),'cases passed',flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--cumulative',action='store_true');run(parser.parse_args().cumulative)
