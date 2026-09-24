"""Remi warp names, native filtering, paging/restoration and floor cancellation."""
import argparse
from tools.service_validation import load_candidate
import json,struct
import mgba.log
from tools.rom import digest,require
from tools.emulator import Session,Debugger,Snapshot
from tools.audit_menu_layouts import Observer
from tools.verify_selection_prompt import window_snapshot
from tools.remi_checks import RemiChecks
from tools.verify_remi import OUT


def run(cumulative=False):
    global OUT
    mgba.log.silence();OUT,rom,build=load_candidate('remi',cumulative)
    require(digest(rom)==build['output_sha256'],'Remi warp ROM differs')
    fixture=Snapshot.load(OUT/'native/entry');results=[]
    scenarios=[(f'pages-{v}-{flag}',v,flag,None) for v in range(3) for flag in (0,1)]
    scenarios+=[('none',0,0,None)]+[(f'select-{i}',1 if i==9 else 2 if i==10 else 0,0,i) for i in (0,1,2,3,4,5,6,8,9,10)]
    for case,vocation,flag,selected in scenarios:
        print('Remi warp:',case,flush=True)
        with Session(rom,OUT/('warp-'+case)) as game:
            game.restore(fixture);m=game.core.memory;overrides=[]
            def write(a,data):
                overrides.append({'address':a,'before':bytes(m[a:a+len(data)]).hex(),'after':data.hex()})
                for i,v in enumerate(data):m.u8[a+i]=v
            hero=m.u32[0x02001624];write(hero+0x90,bytes([vocation]));write(hero+0x60,bytes(4));write(0x0200DF28,bytes(2400))
            write(0x02005646,struct.pack('<13h',*([0 if case=='none' else 50]*13)))
            write(int(game.core.cpu.gprs[13]),struct.pack('<I',flag))
            initial=[int(v)&0xffffffff for v in game.core.cpu.gprs];guard=bytes(m[initial[13]:initial[13]+32])
            check=RemiChecks(game,build);o=Observer(game);choices=[];returned=[];images=[];restorations=[]
            expected=[0,2,1,4,3,5]+([] if flag else [6])+[8]+([9] if vocation==1 else [10] if vocation==2 else [])
            def capture(name):game.capture(name);images.append(name+'.png')
            def cb(e):
                r=e['registers']
                if e['address']==0x0801EE40:choices.append(r[0])
                if e['address']==0x0801F062:
                    require(r[4:12]==initial[4:12] and r[13]==initial[13] and r[0]==initial[14] and bytes(m[r[13]:r[13]+32])==guard,'Remi warp return ABI/guard differs');returned.append(e)
                check.callback(e);o.callback(e)
            def count(ident):return sum(r['id']==ident for r in check.reads)
            with Debugger(game,cb,max_events=220000) as d:
                for a in set(check.ADDRESSES+o.ADDRESSES+(0x0801EE40,0x0801F062)):d.breakpoint(a)
                for _ in range(18):
                    game.frames(90)
                    if check.completed('remi.205') and not check.active:break
                    game.press('A',wait=0)
                for _ in range(3):game.press('DOWN',wait=25)
                game.press('A',wait=90)
                for _ in range(24):
                    game.frames(90)
                    if any(r['id'].startswith('remi-warp-name.') for r in check.reads) and not check.active:break
                    if count('remi.205')==2 and not check.active:break
                    game.press('A',wait=0)
                if case!='none':
                    native=[r for r in o.reads if r['window_width']==128]
                    require(native,'English warp menu missing');first=window_snapshot(game,native[-1]['window']);capture('first-page')
                    if selected is None:
                        for cycle in range(3):
                            game.press('RIGHT',wait=90);capture(f'second-page-{cycle}')
                            game.press('LEFT',wait=90);capture(f'restored-page-{cycle}')
                            latest=[r for r in o.reads if r['window_width']==128][-1]
                            after=window_snapshot(game,latest['window']);require(after==first,'Warp first-page pixels/descriptor did not restore')
                            restorations.append({'before':first,'after':after})
                        game.press('B',wait=90)
                    else:
                        position=expected.index(selected)
                        if position>=5:game.press('RIGHT',wait=90);position-=5
                        for _ in range(position):game.press('DOWN',wait=25)
                        capture('selected');game.press('A',wait=90)
                        for _ in range(24):
                            game.frames(90)
                            if check.completed('remi.176') and not check.active:break
                            game.press('A',wait=0)
                        require(check.completed('remi.176'),'Selected dungeon did not reach native floor picker')
                        capture('floor-picker');game.press('B',wait=90)
                for _ in range(24):
                    game.frames(90)
                    if count('remi.205')==2 and not check.active:break
                    game.press('B',wait=0)
                require(count('remi.205')==2,'Warp did not return to Remi root');capture('root-reopened');game.press('B',wait=90)
                for _ in range(12):
                    if returned:break
                    game.press('A',wait=90)
            require(returned and not check.active and not check.pending,'Warp menu text/return incomplete')
            require(choices==[0xfffffffe if case=='none' else 0xffffffff if selected is None else selected],'Warp selection result differs')
            native=[r for r in o.reads if r['window_width']==128]
            if case=='none':require(not native and check.completed('remi.170'),'Empty warp destinations branch differs')
            else:
                require(all((r['screen_x'],r['screen_y'],r['initial_x'],r['fixed_advance'],r['spacing'])==(8,24,6,0,0) and r['rows'] in (4,5) for r in native),'Warp original geometry differs')
                if selected is None:
                    actual=[int(r['id'].split('.')[-1]) for r in check.reads if r['id'].startswith('remi-warp-name.')]
                    require(actual[:len(expected)]==expected and set(actual)==set(expected),'Warp filtering/order differs')
            require(m.u32[hero+0x60]==0 and bytes(m[0x0200DF28:0x0200DF28+2400])==bytes(2400) and game.snapshot().battery==fixture.battery,'Cancelled warp changed gold/items/battery')
            results.append({'case':case,'overrides':overrides,'expected_destinations':expected,'selection':choices,'restorations':restorations,
                'formats':check.formats,'reads':check.reads,'native_menu_reads':native,'glyph_checks':check.glyph_checks,'inputs':game.inputs,
                'images':{p:digest((game.output/p).read_bytes()) for p in images}})
    (OUT/'warp-menus.json').write_text(json.dumps({'passed':True,'rom_sha256':digest(rom),'cases':results,
        'scope':'Seventeen controlled availability/vocation/inventory cases. Six profiles test both128px pages and three exact first-page pixel restorations; no destinations and all ten native selection IDs/floor cancellation pass. Original6px inset leaves122px for names. Native filtering/order, format/pixels, ABI and unchanged items/gold/battery are verified; actual warp/save transactions remain separate.'},indent=2)+'\n')
    print('Remi warp menus:',len(results),'cases passed',flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--cumulative',action='store_true');run(parser.parse_args().cumulative)
