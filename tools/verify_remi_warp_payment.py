"""Native warp confirmations: exact destination, price and output record."""
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
    require(digest(rom)==build['output_sha256'],'Remi warp payment ROM differs');fixture=Snapshot.load(OUT/'native/entry')
    saved_report=json.loads((OUT/'saved-village.json').read_text());require(saved_report['passed'] and saved_report['rom_sha256']==digest(rom),'Saved-village proof differs')
    require(Snapshot.load(OUT/'native/offer').battery==fixture.battery,'Warp/name fixtures use different saves')
    name=bytes.fromhex(next(r for r in saved_report['cases'] if r['case']=='saved-village-native-save')['expected_name_hex'])
    name_pointers={r['dungeon_id']:r['offset']+0x08000000 for r in build['remi']['warp_names']['entries']}
    formats={r['offset']+0x08000000:r for r in build['remi']['entries']};results=[]
    for dungeon,answer in ((6,'yes'),(6,'no'),(6,'poor'),(8,'yes'),(8,'no')):
        case=f'dungeon-{dungeon}-{answer}';print('Remi warp payment:',case,flush=True)
        with Session(rom,OUT/('warp-payment-'+case)) as game:
            game.restore(fixture);m=game.core.memory;overrides=[]
            def write(a,data):
                overrides.append({'address':a,'before':bytes(m[a:a+len(data)]).hex(),'after':data.hex()})
                for i,v in enumerate(data):m.u8[a+i]=v
            hero=m.u32[0x02001624];gold=0 if answer=='poor' else 1000000
            write(hero+0x60,struct.pack('<I',gold));write(0x0200DF28,bytes(2400));write(0x02005646,struct.pack('<13h',*([50]*13)))
            initial=[int(v)&0xffffffff for v in game.core.cpu.gprs];guard=bytes(m[initial[13]:initial[13]+32])
            check=RemiChecks(game,build,saved_village=name);returned=[];arguments=[];images=[]
            def capture(label):game.capture(label);images.append(label+'.png')
            def cb(e):
                a,r=e['address'],e['registers']
                if a==0x08000FB8 and r[1] in formats and formats[r[1]]['index'] in (172,173,213):
                    index=formats[r[1]]['index'];arguments.append({'index':index,'arguments':r[2:4]})
                    if index==172:require(r[2]==name_pointers[dungeon],'Warp confirmation uses wrong/private dungeon name')
                if a==0x0801F062:
                    require(r[4:12]==initial[4:12] and r[13]==initial[13] and r[0]==initial[14] and bytes(m[r[13]:r[13]+32])==guard,'Warp consumer return ABI/guard differs')
                    returned.append({'event':e,'gold':m.u32[hero+0x60],'output_hex':bytes(m[0x0200FEF4:0x0200FEF7]).hex(),
                        'inventory_hex':bytes(m[0x0200DF28:0x0200DF28+2400]).hex(),'battery_sha256':digest(game.snapshot().battery)})
                    game.snapshot().save(game.output/'consumer-return')
                check.callback(e)
            def count(ident):return sum(r['id']==ident for r in check.reads)
            with Debugger(game,cb,max_events=220000) as d:
                for a in set(check.ADDRESSES+(0x0801F062,)):d.breakpoint(a)
                for _ in range(18):
                    game.frames(90)
                    if check.completed('remi.205') and not check.active:break
                    game.press('A',wait=0)
                for _ in range(3):game.press('DOWN',wait=25)
                game.press('A',wait=90)
                for _ in range(24):
                    game.frames(90)
                    if check.completed('remi-warp-name.3') and not check.active:break
                    game.press('A',wait=0)
                game.press('RIGHT',wait=90)
                for _ in range(1 if dungeon==6 else 2):game.press('DOWN',wait=25)
                game.press('A',wait=90)
                for page in range(40):
                    game.frames(90);capture(f'page-{page:02}')
                    if returned:break
                    if count('remi.205')==2 and not check.active:game.press('B',wait=0);continue
                    fee_done=check.completed('remi.213' if dungeon==8 else 'remi.173')
                    game.press('B' if answer=='no' and fee_done else 'A',wait=0)
            require(len(returned)==1 and not check.active and not check.pending,'Warp consumer did not finish')
            destination=next(a['arguments'] for a in arguments if a['index']==172);floor=destination[1]
            fee=next(a for a in arguments if a['index'] in (173,213));require(fee['index']==(213 if dungeon==8 else 173) and fee['arguments'][0]==floor*1000,'Warp price/branch differs')
            paid=answer=='yes';out=bytes.fromhex(returned[0]['output_hex'])
            require(out==(bytes([1,dungeon,floor]) if paid else bytes([0])+out[1:]),'Warp output record differs')
            require(returned[0]['gold']==gold-(floor*1000 if paid else 0),'Warp charge differs')
            require(returned[0]['inventory_hex']==bytes(2400).hex() and returned[0]['battery_sha256']==digest(fixture.battery),'Warp consumer changed items/battery')
            if answer=='poor':require(check.completed('remi.132'),'Warp insufficient-gold message missing')
            elif paid:require(check.completed('remi.175'),'Warp spell text missing')
            else:require(check.completed('remi.174'),'Warp refusal text missing')
            results.append({'case':case,'overrides':overrides,'arguments':arguments,'returned':returned,'formats':check.formats,
                'reads':check.reads,'glyph_checks':check.glyph_checks,'inputs':game.inputs,
                'images':{p:digest((game.output/p).read_bytes()) for p in images}})
    (OUT/'warp-payments.json').write_text(json.dumps({'passed':True,'rom_sha256':digest(rom),'cases':results,
        'saved_name_report_sha256':digest((OUT/'saved-village.json').read_bytes()),'fixture_battery_sha256':digest(fixture.battery),
        'scope':'Five controlled native Remi warp-consumer cases: ordinary and saved-village warning with both answers, plus insufficient funds. Exact private dungeon argument, selected floor,1000G-per-floor charge, output record, pixels, return ABI, inventory/battery pass. This stops at the owned consumer return; the later dispatcher dungeon transition and actual village overwrite/cold reload remain separate.'},indent=2)+'\n')
    print('Remi warp payment:',len(results),'cases passed',flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--cumulative',action='store_true');run(parser.parse_args().cumulative)
