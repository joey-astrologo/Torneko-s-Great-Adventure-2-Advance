"""Native stored-name generation and the three village prose consumers."""
import argparse,json, struct
import mgba.log
from tools.rom import ROOT, digest, require
from tools.emulator import Session, Debugger, ffi
from tools.village_prose_text import add_village_prose, CAPACITY, NAME_CAPACITY
from tools.bakery_playtest import service_ready
from tools.dialogue_checks import TextChecks
from tools.name_entry import STORED, indexed
from tools.opening_text import BANK_RAM
from tools.lz77 import decompress
from tools.verify_service_ui import materialize
from tools.verify_bank import balance
from tools.holy_flame_playtest import items

OUT=ROOT/'build/village-prose-prototype'

def candidate():
    import tools.build_english as english
    prior=english.add_combat;prose=None
    def add(build):
        nonlocal prose
        result=prior(build);prose=add_village_prose(build);return result
    try:english.add_combat=add;rom,build=english.build_rom(include_story=False)
    finally:english.add_combat=prior
    build['village_prose']=prose;OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'game.gba').write_bytes(rom);(OUT/'build.json').write_text(json.dumps(build,indent=2)+'\n')
    return rom,build

def run(cumulative=False):
    global OUT
    mgba.log.silence()
    if cumulative:
        from tools.build_english import build_rom
        OUT=ROOT/'build/english/village-prose-validation';rom,build=build_rom()
    else:rom,build=candidate()
    fixture=service_ready(rom,OUT)
    prose=build['village_prose'];results=[]
    glyph_table=build['name_entry']['glyph_table']-0x08000000
    japanese=next(i for i in range(1,185) if rom[glyph_table+2*i:glyph_table+2*i+2]==b'\x82\xb0')
    names=[('required-English',indexed('Torneko')),('eight-English',indexed('A'*8,maximum=8)),
           ('eight-Japanese',bytes([japanese])*8+b'\0'*8),('empty',b'\x01'*8+b'\0'*8)]
    for row in prose['entries']:
        bank=next(b for b in prose['banks'] if b['id']==row['bank'])
        data,_=decompress(rom,bank['offset']);data=bytearray(data)
        for word in range(4):struct.pack_into('<I',data,word*4,(struct.unpack_from('<I',data,word*4)[0]+BANK_RAM)&0xFFFFFFFF)
        for name,stored in names:
            expected_name=bytearray()
            for ident in stored[:8]:
                if ident==1:break
                expected_name.extend(rom[glyph_table+2*ident:glyph_table+2*ident+2])
            expected_name.append(0)
            case=row['id']+'-'+name;print('Village prose',case,flush=True)
            with Session(rom,OUT/case) as game:
                game.restore(fixture);m=game.core.memory
                saved_bank=bytes(m[BANK_RAM:BANK_RAM+len(data)])
                for i,value in enumerate(data):m.u8[BANK_RAM+i]=value
                old_stored=bytes(m[STORED:STORED+16])
                temporary=bytes(m[0x0202F44C:0x0202F4ED])
                before_items,before_gold=items(game),balance(game)
                check=TextChecks(game,{});entries,formats,generated,returned=[],[],[],[];pending=None
                def callback(event):
                    nonlocal pending
                    a,r=event['address'],event['registers']
                    if a==0x0801DFAC:
                        require(not entries,'Repeated village prose entry');entries.append(event)
                        for i,value in enumerate(stored):m.u8[STORED+i]=value
                        for reg,value in ((b'r0',row['group']),(b'r1',row['index']),(b'pc',0x08050BC4)):
                            require(game.core._core.writeRegister(game.core._core,reg,ffi.new('uint32_t*',value)),'Controlled village entry failed')
                        return
                    if a==prose['name_ready']:
                        require(r[5]==r[13]+CAPACITY,'Village name argument outside owned stack region')
                        require(bytes(m[r[5]:r[5]+NAME_CAPACITY])==bytes(expected_name).ljust(NAME_CAPACITY,b'\0'),
                                'Native stored-name generation differs')
                        generated.append({'pointer':r[5],'expected_hex':expected_name.hex()})
                    if a==0x08000FB8 and r[14]==prose['formatted']+1:
                        require(r[1]==row['offset']+0x08000000 and r[0]==r[13] and r[2]==r[13]+CAPACITY,
                                'Village format/argument selection differs')
                        require(0x03007000<=r[13] and r[13]+CAPACITY+NAME_CAPACITY<=entries[0]['registers'][13],
                                'Village buffer outside checked native stack')
                        expected=materialize(bytes.fromhex(row['encoded_hex']),[r[2]],m)
                        require(len(expected)<=row['layout']['maximum_formatted_bytes']<=CAPACITY,'Village output exceeds bound')
                        pending=(r[0],expected,bytes(m[r[2]:r[2]+NAME_CAPACITY+20]),r[4:12],r[13])
                    if a==prose['formatted']:
                        require(pending is not None,'Village formatter entry missing')
                        dest,expected,guard,regs,sp=pending
                        require(bytes(m[dest:dest+len(expected)])==expected,'Village format bytes differ')
                        require(bytes(m[dest+CAPACITY:dest+CAPACITY+NAME_CAPACITY+20])==guard and r[4:12]==regs and r[13]==sp,
                                'Village format overwrote argument/saved registers or changed ABI')
                        check.resources[dest]=row|{'encoded_hex':expected.hex()}
                        formats.append({'dest':dest,'bytes':len(expected),'expected_hex':expected.hex(),
                                        'capacity':CAPACITY,'argument_guard_and_abi_preserved':True});pending=None
                    if a==prose['returned']:
                        require(r[4:12]==entries[0]['registers'][4:12] and r[13]==entries[0]['registers'][13]
                                and r[0]==entries[0]['registers'][14],'Village return ABI differs')
                        require(check.completed(row['id']) and check.active is None,'Village returned before text completed')
                        require(bytes(m[BANK_RAM:BANK_RAM+len(data)])==data,'Village prose changed supplied bank')
                        for i,value in enumerate(saved_bank):m.u8[BANK_RAM+i]=value
                        returned.append(event['frame'])
                    if a in check.ADDRESSES:check.callback(event)
                with Debugger(game,callback,max_events=100000) as debug:
                    for address in set(check.ADDRESSES+(0x0801DFAC,0x08000FB8,prose['name_ready'],prose['formatted'],prose['returned'])):
                        debug.breakpoint(address)
                    game.press('A',wait=120);game.capture('page-0')
                    for page in range(1,12):
                        if returned:break
                        game.press('A',wait=120);game.capture(f'page-{page}')
                    require(returned and len(formats)==len(generated)==1 and pending is None,'Village prose did not finish')
                require(bytes(m[0x0202F44C:0x0202F4ED])==temporary,'Village prose overwrote shared temporary storage')
                require(bytes(m[STORED:STORED+16])==stored,'Village producer changed stored name')
                require(items(game)==before_items and balance(game)==before_gold,'Village prose changed items/gold')
                require(game.snapshot().battery==fixture.battery,'Village probe wrote battery')
                results.append({'case':case,'id':row['id'],'controlled_stored_before':old_stored.hex(),
                                'controlled_stored_after':stored.hex(),'controlled_entry':{'pc':0x08050BC4,'r0':row['group'],'r1':row['index']},
                                'bank_bytes':len(data),'entries':entries,'generated':generated,'formats':formats,
                                'reads':check.reads,'glyph_checks':check.glyph_checks,'inputs':game.inputs,
                                'bank_restored':True,'shared_temporary_preserved':True})
    report={'passed':True,'rom_sha256':digest(rom),'cases':results,
            'scope':'12 controlled native village prose calls: three sources with Torneko, eight widest English/Japanese glyphs and the native empty-name branch. Eight-character cases exceed the current seven-character editor and deliberately test the producer bound. Exact generated name/format, separate 448-byte output and 32-byte argument stack regions, guard/ABI, pixels/paging, shared temporary bytes, items/gold and battery pass. Ordinary story access remains separate.'}
    (OUT/'report.json').write_text(json.dumps(report,indent=2)+'\n');print('Village prose:',len(results),'native cases passed')

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--cumulative',action='store_true');run(parser.parse_args().cumulative)
