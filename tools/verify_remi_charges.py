"""Native staff charging, capacity boundary, decline and refusal paths."""
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
    require(digest(rom)==build['output_sha256'],'Remi charges ROM differs')
    fixture=Snapshot.load(OUT/'native/entry');results=[]
    for case in ('charge-five','charge-to-cap','decline','cancel-item','poor','no-staff'):
        print('Remi charges:',case,flush=True)
        with Session(rom,OUT/('charges-'+case)) as game:
            game.restore(fixture);m=game.core.memory;overrides=[]
            def write(a,data):
                overrides.append({'address':a,'before':bytes(m[a:a+len(data)]).hex(),'after':data.hex()})
                for i,v in enumerate(data):m.u8[a+i]=v
            ident=1 if case=='no-staff' else 51;charges=98 if case=='charge-to-cap' else 5
            inventory=bytearray(2400);struct.pack_into('<I',inventory,0,0xC8000000)
            inventory[4]=charges;inventory[5]=1;inventory[8]=bytes(m[0x020013D0:0x020014D0]).index(ident)
            write(0x0200DF28,inventory);a=0x02003BAC+ident*20;write(a,struct.pack('<I',m.u32[a]|0x40000000))
            ga=m.u32[0x02001624]+0x60;gold=4999 if case=='poor' else 1000000;write(ga,struct.pack('<I',gold))
            initial=[int(v)&0xffffffff for v in game.core.cpu.gprs];guard=bytes(m[initial[13]:initial[13]+32])
            before=items(game);check=RemiChecks(game,build);returned=[];images=[]
            def capture(name):game.capture(name);images.append(name+'.png')
            def cb(e):
                r=e['registers']
                if e['address']==0x0801F062:
                    require(r[4:12]==initial[4:12] and r[13]==initial[13] and r[0]==initial[14] and bytes(m[r[13]:r[13]+32])==guard,'Remi staff return ABI/guard differs');returned.append(e)
                check.callback(e)
            def count(ident):return sum(r['id']==ident for r in check.reads)
            with Debugger(game,cb,max_events=200000) as d:
                for a in set(check.ADDRESSES+(0x0801F062,)):d.breakpoint(a)
                for _ in range(18):
                    game.frames(90)
                    if check.completed('remi.205') and not check.active:break
                    game.press('A',wait=0)
                game.press('DOWN',wait=25);game.press('DOWN',wait=25);game.press('A',wait=90)
                for page in range(40):
                    game.frames(90);capture(f'page-{page:02}')
                    if count('remi.205')==2 and not check.active:break
                    answer='B' if case=='decline' and check.completed('remi.142') else 'B' if case=='cancel-item' and check.completed('remi.138') else 'A'
                    game.press(answer,wait=0)
                require(count('remi.205')==2,'Remi charging did not return to root')
                game.press('B',wait=90)
                for _ in range(12):
                    if returned:break
                    game.press('A',wait=90)
            require(returned and not check.active and not check.pending,'Remi charging incomplete')
            added=5 if case=='charge-five' else 1 if case=='charge-to-cap' else 0
            require(items(game)==[(0,ident,charges+added)] and m.u32[ga]==gold-added*5000,'Staff charges/payment differ')
            expected={'charge-five':145,'charge-to-cap':145,'decline':143,'cancel-item':139,'poor':126,'no-staff':136}[case]
            require(check.completed(f'remi.{expected}'),'Staff service branch missing')
            require(game.snapshot().battery==fixture.battery,'Staff charge probe changed battery')
            results.append({'case':case,'overrides':overrides,'before_items':before,'after_items':items(game),'gold_before':gold,'gold_after':m.u32[ga],
                'formats':check.formats,'reads':check.reads,'glyph_checks':check.glyph_checks,'inputs':game.inputs,
                'images':{p:digest((game.output/p).read_bytes()) for p in images}})
    (OUT/'charges.json').write_text(json.dumps({'passed':True,'rom_sha256':digest(rom),'cases':results,
        'scope':'Six controlled item/wallet cases use native menu/item/number selection. Add5charges or cap98to99, decline price, cancel selection, insufficient funds and no staff. The existing charge byte and5000G per charge, complete format/pixels, caller ABI and unchanged battery pass. Ordinary unlocking/acquisition remain separate.'},indent=2)+'\n')
    print('Remi charges:',len(results),'cases passed',flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--cumulative',action='store_true');run(parser.parse_args().cumulative)
