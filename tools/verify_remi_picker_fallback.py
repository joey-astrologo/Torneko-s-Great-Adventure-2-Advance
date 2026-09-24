"""Unknown picker templates retain the original fixed12px behavior."""
import argparse
from tools.service_validation import load_candidate
import json
import mgba.log
from tools.rom import digest,require
from tools.emulator import Session,Debugger,Snapshot
from tools.audit_menu_layouts import Observer
from tools.verify_remi import OUT
from tools.town_text import entries,RAM


def run(cumulative=False):
    global OUT
    mgba.log.silence();OUT,rom,build=load_candidate('remi',cumulative);fixture=Snapshot.load(OUT/'native/picker')
    require(fixture.rom_sha256==digest(rom),'Remi picker fallback fixture differs');results=[]
    for index in (129,140,176):
        case=f'picker-fallback-{index}';print('Remi:',case,flush=True)
        with Session(rom,OUT/case) as game:
            game.restore(fixture);m=game.core.memory;sp=int(game.core.cpu.gprs[13]);pointer=RAM+entries()[index]['start']
            old=int(game.core.cpu.gprs[2]);game.core.cpu.gprs[2]=pointer
            initial=[int(v)&0xffffffff for v in game.core.cpu.gprs];guard=bytes(m[sp:sp+32]);returned=[];closed=[];o=Observer(game)
            def cb(e):
                r=e['registers']
                if e['address']==0x0801E9CC:
                    require(r[0]==0xffffffff and r[4:12]==initial[4:12] and r[13]==sp and bytes(m[sp:sp+32])==guard,'Original picker return differs');returned.append(e)
                if e['address']==0x0801F062:closed.append(e)
                o.callback(e)
            with Debugger(game,cb,max_events=140000) as d:
                for a in set(o.ADDRESSES+(0x0801E9CC,0x0801F062)):d.breakpoint(a)
                for _ in range(12):
                    game.frames(90)
                    if any(r['window_width']==88 for r in o.reads):break
                    game.press('A',wait=0)
                game.capture('original-picker');game.press('B',wait=90)
                for _ in range(18):
                    if closed:break
                    game.press('B',wait=90)
            native=[r for r in o.reads if r['window_width']==88]
            require(native and all(r['fixed_advance']==12 and r['spacing']==0 for r in native),'Unknown picker template changed advance')
            for read in native:
                positions=[g['x'] for g in read['glyph_positions']]
                require(positions==list(range(0,12*len(positions),12)),'Original picker cell positions differ')
            require(len(returned)==len(closed)==1 and game.snapshot().battery==fixture.battery,'Original picker completion/battery differs')
            results.append({'case':case,'override':{'register':2,'before':old,'after':pointer},'native_reads':native,'inputs':game.inputs,
                'images':{'original-picker.png':digest((game.output/'original-picker.png').read_bytes())}})
    (OUT/'picker-fallbacks.json').write_text(json.dumps({'passed':True,'rom_sha256':digest(rom),'cases':results,
        'scope':'All three original Japanese templates through the shared picker retain12px fixed advance because their pointers are outside the three private English formats. Native cancellation, positions, original88px panel, ABI/guard and unchanged battery pass.'},indent=2)+'\n')
    print('Remi picker fallbacks:',len(results),'cases passed',flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--cumulative',action='store_true');run(parser.parse_args().cumulative)
