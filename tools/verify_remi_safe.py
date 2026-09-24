"""Native Iron safe purchases, decline and service refusal branches."""
import argparse
from tools.service_validation import load_candidate
import json,struct
import mgba.log
from tools.rom import digest,require
from tools.emulator import Session,Debugger,Snapshot
from tools.remi_checks import RemiChecks
from tools.holy_flame_playtest import items
from tools.verify_remi import OUT


def run(cumulative=False):
    global OUT
    mgba.log.silence();OUT,rom,build=load_candidate('remi',cumulative)
    require(digest(rom)==build['output_sha256'],'Remi Iron safe ROM differs')
    fixture=Snapshot.load(OUT/'native/entry');results=[];price=struct.unpack_from('<I',rom,0x143000)[0]
    require(price==2000,'Native Iron safe price differs')
    for case in ('buy','exact-gold','decline','poor','full','already-owned'):
        print('Remi Iron safe:',case,flush=True)
        with Session(rom,OUT/('safe-'+case)) as game:
            game.restore(fixture);m=game.core.memory;overrides=[]
            def write(a,data):
                overrides.append({'address':a,'before':bytes(m[a:a+len(data)]).hex(),'after':data.hex()})
                for i,v in enumerate(data):m.u8[a+i]=v
            inventory=bytearray(2400);mapping=bytes(m[0x020013D0:0x020014D0])
            ids=([1]*20 if case=='full' else [217] if case=='already-owned' else [])
            for slot,ident in enumerate(ids):
                struct.pack_into('<I',inventory,120*slot,0xC8000000);inventory[120*slot+5]=1;inventory[120*slot+8]=mapping.index(ident)
                a=0x02003BAC+ident*20;write(a,struct.pack('<I',m.u32[a]|0x40000000))
            write(0x0200DF28,inventory);ga=m.u32[0x02001624]+0x60;gold=price if case=='exact-gold' else price-1 if case=='poor' else 1000000;write(ga,struct.pack('<I',gold))
            initial=[int(v)&0xffffffff for v in game.core.cpu.gprs];guard=bytes(m[initial[13]:initial[13]+32])
            before_items=items(game);check=RemiChecks(game,build);returned=[];images=[]
            def capture(name):game.capture(name);images.append(name+'.png')
            def cb(e):
                r=e['registers']
                if e['address']==0x0801F062:
                    require(r[4:12]==initial[4:12] and r[13]==initial[13] and r[0]==initial[14] and bytes(m[r[13]:r[13]+32])==guard,'Remi safe return ABI/guard differs');returned.append(e)
                check.callback(e)
            def count(ident):return sum(r['id']==ident for r in check.reads)
            with Debugger(game,cb,max_events=180000) as d:
                for a in set(check.ADDRESSES+(0x0801F062,)):d.breakpoint(a)
                for _ in range(18):
                    game.frames(90)
                    if count('remi.205')==1 and not check.active:break
                    game.press('A',wait=0)
                game.press('A',wait=90)
                for page in range(24):
                    game.frames(90);capture(f'page-{page:02}')
                    if count('remi.205')==2 and not check.active:break
                    game.press('B' if case=='decline' else 'A',wait=0)
                require(count('remi.205')==2,'Remi safe did not reopen root')
                game.press('B',wait=90)
                for _ in range(12):
                    if returned:break
                    game.press('A',wait=90)
            require(returned and not check.active and not check.pending,'Remi safe did not finish')
            purchased=case in ('buy','exact-gold');after=items(game)
            require([i for _,i,_ in after]==([217] if purchased else ids),'Iron safe inventory result differs')
            require(m.u32[ga]==gold-(price if purchased else 0),'Iron safe charged wrong gold')
            ident={'buy':147,'exact-gold':147,'decline':148,'poor':149,'full':150,'already-owned':151}[case]
            require(check.completed(f'remi.{ident}'),'Iron safe expected branch missing')
            require(game.snapshot().battery==fixture.battery,'Iron safe probe changed battery')
            results.append({'case':case,'overrides':overrides,'before_items':before_items,'after_items':after,'gold_before':gold,'gold_after':m.u32[ga],
                'formats':check.formats,'reads':check.reads,'glyph_checks':check.glyph_checks,'inputs':game.inputs,
                'images':{p:digest((game.output/p).read_bytes()) for p in images}})
    (OUT/'safe.json').write_text(json.dumps({'passed':True,'rom_sha256':digest(rom),'cases':results,
        'scope':'Six controlled inventories/wallets, native menu input and Iron safe purchase mechanics: normal/exact-price purchase, decline, insufficient gold, full inventory and already owned. Item217 and2000G payment are verified; refusal paths preserve items/gold, caller ABI and battery. Ordinary unlocking/acquisition remain separate.'},indent=2)+'\n')
    print('Remi Iron safe:',len(results),'cases passed',flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--cumulative',action='store_true');run(parser.parse_args().cumulative)
