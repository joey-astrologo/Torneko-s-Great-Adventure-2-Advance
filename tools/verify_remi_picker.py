"""Remi's native two-digit picker templates, guards and return results."""
import argparse
from tools.service_validation import load_candidate
import json,struct
import mgba.log
from tools.rom import digest,require
from tools.emulator import Session,Debugger,Snapshot
from tools.audit_menu_layouts import Observer
from tools.remi_checks import RemiChecks
from tools.verify_remi import OUT
from tools.verify_service_ui import cstring


def run(cumulative=False):
    global OUT
    mgba.log.silence();OUT,rom,build=load_candidate('remi',cumulative)
    require(digest(rom)==build['output_sha256'],'Remi picker ROM differs')
    entry=Snapshot.load(OUT/'native/entry');path=OUT/'native/picker'
    with Session(rom,OUT/'context-picker') as game:
        game.restore(entry);m=game.core.memory;gold=m.u32[0x02001624]+0x60;before=m.u32[gold];m.u32[gold]=1000000
        check=RemiChecks(game,build);saved=[]
        def cb(e):
            if e['address']==0x08016410 and not saved:game.snapshot().save(path);saved.append(e)
            check.callback(e)
        with Debugger(game,cb,max_events=120000) as d:
            for a in set(check.ADDRESSES+(0x08016410,)):d.breakpoint(a)
            for _ in range(20):
                game.frames(90)
                if check.completed('remi.205') and not check.active:break
                game.press('A',wait=0)
            game.press('DOWN',wait=25);game.press('A',wait=90)
            for _ in range(15):
                if saved:break
                game.press('A',wait=90)
        require(saved,'Native Remi level picker missing')
        (game.output/'provenance.json').write_text(json.dumps({'rom_sha256':digest(rom),'fixture':str(OUT/'native/entry'),
            'overrides':[{'address':gold,'before':before,'after':1000000}],'entry':saved,'formats':check.formats,'inputs':game.inputs},indent=2)+'\n')
    fixture=Snapshot.load(path);results=[]
    for row in (r for r in build['remi']['entries'] if r['layout']['kind']=='picker'):
        for initial_value,action in [(0,'B'),(5,'B'),(9,'B'),(10,'B'),(50,'B'),(99,'B'),(4,'A')]:
            case=f"{row['id']}-number-{initial_value}-{action}";print('Remi picker:',case,flush=True)
            with Session(rom,OUT/case) as game:
                game.restore(fixture);m=game.core.memory;sp=int(game.core.cpu.gprs[13]);overrides=[]
                def reg(i,v):overrides.append({'register':i,'before':int(game.core.cpu.gprs[i]),'after':v});game.core.cpu.gprs[i]=v
                def word(a,v):overrides.append({'address':a,'before':m.u32[a],'after':v});m.u32[a]=v
                reg(2,row['offset']+0x08000000);reg(3,0);word(sp,100 if action=='B' else 6);word(sp+4,initial_value)
                initial=[int(v)&0xffffffff for v in game.core.cpu.gprs];guard=bytes(m[sp:sp+32])
                check=RemiChecks(game,build);prompt=next(r for r in build['remi']['entries'] if r['index']==128)
                check.resources[initial[0]]=prompt|{'encoded_hex':(cstring(m,initial[0])+b'\0').hex()}
                o=Observer(game);returned=[];closed=[];images=[]
                def cb(e):
                    r=e['registers']
                    if e['address']==0x0801E9CC:
                        require(r[4:12]==initial[4:12] and r[13]==sp and bytes(m[sp:sp+32])==guard,'Remi picker ABI/guard differs')
                        returned.append(r[0])
                    if e['address']==0x0801F062:closed.append(e)
                    check.callback(e);o.callback(e)
                with Debugger(game,cb,max_events=160000) as d:
                    for a in set(check.ADDRESSES+o.ADDRESSES+(0x0801E9CC,0x0801F062)):d.breakpoint(a)
                    for _ in range(12):
                        game.frames(90)
                        if check.completed(row['id']) and not check.active:break
                        game.press('A',wait=0)
                    game.capture('picker');images.append('picker.png')
                    if action=='A':game.press('UP',wait=40);game.capture('changed');images.append('changed.png')
                    game.press(action,wait=90)
                    for _ in range(18):
                        if closed:break
                        game.press('B',wait=90)
                require(returned==([0xffffffff] if action=='B' else [5]) and closed,'Remi picker result/closure differs')
                require(not check.active and not check.pending and check.completed(row['id']),'Remi picker text incomplete')
                native=[r for r in o.reads if r['source'] in check.resources and check.resources[r['source']]['id']==row['id']]
                require(native and all((r['screen_x'],r['screen_y'],r['window_width'],r['rows'])==(144,88,88,1) for r in native),'Remi picker geometry differs')
                require(game.snapshot().battery==fixture.battery,'Remi picker changed battery')
                results.append({'case':case,'overrides':overrides,'returns':returned,'formats':check.formats,'reads':check.reads,'native_picker_reads':native,
                    'glyph_checks':check.glyph_checks,'inputs':game.inputs,'images':{p:digest((game.output/p).read_bytes()) for p in images}})
    (OUT/'pickers.json').write_text(json.dumps({'passed':True,'rom_sha256':digest(rom),'cases':results,
        'scope':'Three private Remi picker templates use the native level-service picker. Six values0/5/9/10/50/99 cancel; each template also increments4to5 and confirms, then declines service. Two-cell native number producer,128-byte format output/guards, original88px panel and caller ABI pass. Staff and warp reachability/transactions remain separate.'},indent=2)+'\n')
    print('Remi pickers:',len(results),'cases passed',flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--cumulative',action='store_true');run(parser.parse_args().cumulative)
