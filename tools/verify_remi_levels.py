"""Native Remi level-up costs, cancellation and availability changes."""
import argparse
from tools.service_validation import load_candidate
import json,struct
import mgba.log
from tools.rom import digest,require
from tools.emulator import Session,Debugger,Snapshot
from tools.remi_checks import RemiChecks
from tools.verify_remi import OUT


def run(cumulative=False):
    global OUT
    mgba.log.silence();OUT,rom,build=load_candidate('remi',cumulative)
    require(digest(rom)==build['output_sha256'],'Remi level ROM differs')
    fixture=Snapshot.load(OUT/'native/entry');results=[]
    for case in ('level-two','level-five','decline','cancel-picker','poor'):
        print('Remi levels:',case,flush=True)
        with Session(rom,OUT/('levels-'+case)) as game:
            game.restore(fixture);m=game.core.memory;hero=m.u32[0x02001624];overrides=[]
            def write(a,data):
                overrides.append({'address':a,'before':bytes(m[a:a+len(data)]).hex(),'after':data.hex()})
                for i,v in enumerate(data):m.u8[a+i]=v
            write(hero+0x88,b'\x01\0');write(hero+0x5c,bytes(4));gold=2000 if case=='level-two' else 1999 if case=='poor' else 1000000;write(hero+0x60,struct.pack('<I',gold))
            initial=[int(v)&0xffffffff for v in game.core.cpu.gprs];guard=bytes(m[initial[13]:initial[13]+32]);inventory=bytes(m[0x0200DF28:0x0200DF28+2400])
            check=RemiChecks(game,build);returned=[];images=[]
            def capture(name):game.capture(name);images.append(name+'.png')
            def cb(e):
                r=e['registers']
                if e['address']==0x0801F062:
                    require(r[4:12]==initial[4:12] and r[13]==initial[13] and r[0]==initial[14] and bytes(m[r[13]:r[13]+32])==guard,'Remi level return ABI/guard differs');returned.append(e)
                check.callback(e)
            def count(ident):return sum(r['id']==ident for r in check.reads)
            with Debugger(game,cb,max_events=200000) as d:
                for a in set(check.ADDRESSES+(0x0801F062,)):d.breakpoint(a)
                for _ in range(18):
                    game.frames(90)
                    if check.completed('remi.205') and not check.active:break
                    game.press('A',wait=0)
                game.press('DOWN',wait=25);game.press('A',wait=90)
                for page in range(40):
                    game.frames(90);capture(f'page-{page:02}')
                    if count('remi.205')==2 and not check.active:break
                    key='B' if case=='decline' and check.completed('remi.131') else 'B' if case=='cancel-picker' and check.completed('remi.129') else 'A'
                    game.press(key,wait=0)
                require(count('remi.205')==2,'Remi level did not return to root')
                game.press('B',wait=90)
                for _ in range(12):
                    if returned:break
                    game.press('A',wait=90)
            level=2 if case=='level-two' else 5 if case=='level-five' else 1;cost={1:0,2:2000,5:5000}[level]
            require(returned and not check.active and not check.pending,'Remi level incomplete')
            require(m.u16[hero+0x88]==level and m.u32[hero+0x60]==gold-cost,'Remi native level/payment differ')
            require(count('remi.204')==(1 if level>1 else 2),'Level-up availability did not follow native level')
            require(check.completed('remi.134' if level>1 else 'remi.126' if case=='poor' else 'remi.130'),'Level-up expected branch missing')
            require(bytes(m[0x0200DF28:0x0200DF28+2400])==inventory and game.snapshot().battery==fixture.battery,'Level-up changed inventory/battery')
            results.append({'case':case,'overrides':overrides,'level_after':level,'gold_before':gold,'gold_after':m.u32[hero+0x60],
                'formats':check.formats,'reads':check.reads,'glyph_checks':check.glyph_checks,'inputs':game.inputs,
                'images':{p:digest((game.output/p).read_bytes()) for p in images}})
    (OUT/'levels.json').write_text(json.dumps({'passed':True,'rom_sha256':digest(rom),'cases':results,
        'scope':'Five controlled level1/experience0/wallet cases with native service input. Raise to2for2000G or5for5000G, decline, cancel picker and insufficient gold. Native level and availability changes, complete formats/pixels, caller ABI and unchanged inventory/battery pass. Ordinary unlocking/acquisition remain separate.'},indent=2)+'\n')
    print('Remi levels:',len(results),'cases passed',flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--cumulative',action='store_true');run(parser.parse_args().cumulative)
