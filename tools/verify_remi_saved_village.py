"""Remi's overwrite warning: native saved-village control and bounded printf."""
import argparse
from tools.service_validation import load_candidate
import json
import mgba.log
from tools.rom import digest,require
from tools.emulator import Session,Debugger,Snapshot
from tools.audit_menu_layouts import Observer
from tools.dialogue_checks import TextChecks,rendered_codes
from tools.name_entry import HERO,indexed
from tools.verify_service_ui import materialize
from tools.verify_remi import OUT


from tools.saved_village_checks import SavedVillageChecks


def run(cumulative=False):
    global OUT
    mgba.log.silence();OUT,rom,build=load_candidate('remi',cumulative)
    require(digest(rom)==build['output_sha256'],'Remi saved-village ROM differs')
    fixture=Snapshot.load(OUT/'native/offer');row=next(r for r in build['remi']['entries'] if r['index']==213)
    table=build['name_entry']['glyph_table']-0x08000000
    japanese=next(i for i in range(1,185) if rom[table+2*i:table+2*i+2]==b'\x82\xb0')
    # Observe the real save-read result first, without changing save bytes or its result.
    with Session(rom,OUT/'saved-village-reference') as game:
        game.restore(fixture);game.core.cpu.gprs[1]=row['offset']+0x08000000;game.core.cpu.gprs[2]=40
        m=game.core.memory;o=Observer(game);headers=[]
        def cb(e):
            if e['address']==0x0801FAC8:
                r=e['registers'];headers.append({'result':r[0],'buffer_hex':bytes(m[r[13]:r[13]+64]).hex(),'event':e})
            o.callback(e)
        with Debugger(game,cb,max_events=100000) as d:
            for a in set(o.ADDRESSES+(0x0801FAC8,)):d.breakpoint(a)
            for _ in range(20):
                game.frames(90)
                if headers:break
                game.press('B',wait=0)
        require(len(headers)==1 and headers[0]['result']==0,'Native saved village not available in fixture')
        native_ids=bytes.fromhex(headers[0]['buffer_hex'])[20:28]
        (game.output/'provenance.json').write_text(json.dumps({'rom_sha256':digest(rom),'fixture':str(OUT/'native/offer'),
            'register_overrides':{'r1':row['offset']+0x08000000,'r2':40},'headers':headers,'inputs':game.inputs},indent=2)+'\n')
    names=[('native-save',native_ids),('required-English',indexed('Torneko')[:8]),
           ('eight-English',indexed('W'*8,maximum=8)[:8]),('eight-Japanese',bytes([japanese])*8),
           ('empty',b'\x01'*8),('read-failure',b'\x01'*8)]
    results=[]
    for label,ids in names:
        expected_name=bytearray()
        for ident in ids:
            if ident==1:break
            expected_name.extend(rom[table+ident*2:table+ident*2+2])
        expected_name.append(0);expected_name=bytes(expected_name)
        case='saved-village-'+label;print('Remi:',case,flush=True)
        with Session(rom,OUT/case) as game:
            game.restore(fixture);m=game.core.memory;sp=int(game.core.cpu.gprs[13]);dest=int(game.core.cpu.gprs[0]);cost=2147483647 if label.startswith('eight') else 40
            game.core.cpu.gprs[1]=row['offset']+0x08000000;game.core.cpu.gprs[2]=cost
            expected=materialize(bytes.fromhex(row['encoded_hex']),[cost],m);guard=bytes(m[dest+256:dest+288])
            initial=[int(v)&0xffffffff for v in game.core.cpu.gprs]
            resources={r['offset']+0x08000000:r for r in build['remi']['entries'] if r['layout']['direct_rom_stream']}
            resources[dest]=row|{'encoded_hex':expected.hex()}
            choice=next(r for r in build['dialogue']['entries'] if r['id']=='rom.0006309c');resources[choice['rom_offset']+0x08000000]=choice
            check=SavedVillageChecks(game,resources,dest,expected_name);overrides=[];produced=[];formats=[];returned=[];images=[]
            def cb(e):
                a,r=e['address'],e['registers']
                if a==0x0801ECCA:
                    require(bytes(m[dest:dest+len(expected)])==expected and bytes(m[dest+256:dest+288])==guard,
                            'Saved-village formatter output/guard differs')
                    require(r[4:12]==initial[4:12] and r[13]==sp,'Saved-village formatter ABI differs');formats.append(e)
                if a==0x0801FAC8:
                    require(r[0]==0,'Native save read unexpectedly failed')
                    if label=='read-failure':
                        overrides.append({'register':0,'before':r[0],'after':0xffffffff});game.core.cpu.gprs[0]=-1
                    elif label!='native-save':
                        address=r[13]+20;overrides.append({'address':address,'before':bytes(m[address:address+8]).hex(),'after':ids.hex()})
                        for i,v in enumerate(ids):m.u8[address+i]=v
                    else:require(bytes(m[r[13]+20:r[13]+28])==ids,'Native saved header differs from reference')
                if a==0x0801FB12:
                    require(r[0]==(0 if label=='read-failure' else 0x0200CEE8),'Saved-name pointer/failure differs')
                    require(bytes(m[0x0200CEE8:0x0200CEFC])==expected_name.ljust(20,b'\0'),'Native saved-name generation differs')
                    produced.append(e)
                if a==0x0801F062:returned.append(e)
                if a in check.ADDRESSES:check.callback(e)
            inventory=bytes(m[0x0200DF28:0x0200DF28+2400]);ga=m.u32[0x02001624]+0x60;gold=m.u32[ga]
            with Debugger(game,cb,max_events=150000) as d:
                for a in set(check.ADDRESSES+(0x0801ECCA,0x0801FAC8,0x0801FB12,0x0801F062)):d.breakpoint(a)
                for page in range(24):
                    game.frames(90);image=f'page-{page:02}';game.capture(image);images.append(image+'.png')
                    if returned:break
                    game.press('B',wait=0)
            require(len(produced)==len(formats)==len(returned)==1 and check.completed(row['id']) and not check.active,'Saved-village warning incomplete')
            require(bytes(m[0x0200DF28:0x0200DF28+2400])==inventory and m.u32[ga]==gold and game.snapshot().battery==fixture.battery,'Declined warning changed items/gold/battery')
            results.append({'case':case,'cost':cost,'saved_ids_hex':ids.hex(),'expected_name_hex':expected_name.hex(),
                'register_overrides':{'r1':row['offset']+0x08000000,'r2':cost},'read_result_overrides':overrides,
                'producer_events':produced,'formats':formats,'reads':check.reads,'glyph_checks':check.glyph_checks,'inputs':game.inputs,
                'images':{p:digest((game.output/p).read_bytes()) for p in images}})
    (OUT/'saved-village.json').write_text(json.dumps({'passed':True,'rom_sha256':digest(rom),'cases':results,
        'scope':'Actual saved-header name plus five controlled save-reader-result cases. Native1F producer decodes eight indexed cells into its existing20-byte scratch buffer; failure/empty and maximum English/Japanese names pass. The256-byte printf output retains1F and paired price colours; pixels/paging, declined question and unchanged battery pass. The special warp branch and actual overwrite transaction remain separate.'},indent=2)+'\n')
    print('Remi saved village:',len(results),'cases passed',flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--cumulative',action='store_true');run(parser.parse_args().cumulative)
