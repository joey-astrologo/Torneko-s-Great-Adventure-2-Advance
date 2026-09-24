"""Verify the native four-way floor selector with an owned stack text buffer."""
import argparse,json,struct
import mgba.log
from tools.rom import ROOT,digest,require
from tools.emulator import Session,Debugger,ffi
from tools.floor_progress_text import add_progress,CAPACITY
from tools.bakery_playtest import service_ready
from tools.dialogue_checks import TextChecks,player_layout_cases
from tools.name_entry import HERO
from tools.opening_text import BANK_RAM
from tools.lz77 import decompress
from tools.verify_service_ui import materialize
from tools.verify_bank import balance
from tools.holy_flame_playtest import items

OUT=ROOT/'build/floor-progress-prototype'

def candidate():
    import tools.build_english as english
    prior=english.add_combat;progress=None
    def add(build):
        nonlocal progress
        result=prior(build);progress=add_progress(build);return result
    try:english.add_combat=add;rom,build=english.build_rom(include_story=False)
    finally:english.add_combat=prior
    build['floor_progress']=progress;OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'game.gba').write_bytes(rom);(OUT/'build.json').write_text(json.dumps(build,indent=2)+'\n')
    return rom,build

def run(cumulative=False):
    global OUT
    mgba.log.silence()
    if cumulative:
        from tools.build_english import build_rom
        OUT=ROOT/'build/english/floor-progress-validation';rom,build=build_rom()
    else:rom,build=candidate()
    fixture=service_ready(rom,OUT)
    data,_=decompress(rom,build['floor_progress']['bank_rom_offset']);data=bytearray(data)
    for word in range(4):struct.pack_into('<I',data,word*4,(struct.unpack_from('<I',data,word*4)[0]+BANK_RAM)&0xFFFFFFFF)
    targets={r['offset']+0x08000000:r for r in build['floor_progress']['entries']};results=[]
    for floor in (0,9,10,19,20,26,27,28,255):
        index=8 if floor==27 else 5 if floor<=9 else 6 if floor<=19 else 7
        row=next(r for r in targets.values() if r['index']==index)
        for label,name in player_layout_cases():
            case=f'{floor}-{label}';print('Floor progress',case,flush=True)
            with Session(rom,OUT/case) as game:
                game.restore(fixture);m=game.core.memory
                for i,v in enumerate(name.ljust(16,b'\0')):m.u8[HERO+i]=v
                original_floor=m.u8[0x0200FF1B];m.u8[0x0200FF1B]=floor
                saved_bank=bytes(m[BANK_RAM:BANK_RAM+len(data)])
                for i,v in enumerate(data):m.u8[BANK_RAM+i]=v
                before_items,before_gold=items(game),balance(game)
                check=TextChecks(game,{});entries=[];formats=[];returned=[];pending=None
                def callback(event):
                    nonlocal pending
                    a,r=event['address'],event['registers']
                    if a==0x0801DFAC:
                        require(not entries,'Repeated controlled floor service entry')
                        entries.append({'original_registers':r,'frame':event['frame'],'controlled_pc':0x080501DC})
                        game.core._core.writeRegister(game.core._core,b'pc',ffi.new('uint32_t*',0x080501DC));return
                    if a==0x08000FB8 and r[14]==0x0805021D:
                        require(r[1] in targets and targets[r[1]]['id']==row['id'],'Native floor selector chose wrong text')
                        require(r[0]==r[13]+8 and r[2]==floor,'Floor output is not its owned stack region')
                        require(0x03007000<=r[13] and r[0]+CAPACITY<=entries[0]['original_registers'][13],'Expanded floor frame outside checked native stack')
                        expected=materialize(bytes.fromhex(row['encoded_hex']),[floor],m)
                        require(len(expected)<=row['layout']['maximum_formatted_bytes']<=CAPACITY,'Floor output exceeds capacity')
                        pending=(r[0],expected,bytes(m[r[0]+CAPACITY:r[0]+CAPACITY+16]),bytes(m[r[13]:r[13]+8]),r[4:12],r[13])
                    if a==0x0805021C:
                        require(pending is not None,'Missing floor formatter entry')
                        dest,expected,guard,prefix,regs,sp=pending
                        require(bytes(m[dest:dest+len(expected)])==expected,'Floor text expansion differs')
                        require(bytes(m[dest+CAPACITY:dest+CAPACITY+16])==guard and bytes(m[sp:sp+8])==prefix,'Floor formatter crossed owned stack region')
                        require(r[4:12]==regs and r[13]==sp,'Floor formatter ABI differs')
                        check.resources[dest]=row|{'encoded_hex':expected.hex()}
                        formats.append({'id':row['id'],'dest':dest,'sp':sp,'bytes':len(expected),'capacity':CAPACITY,'expected_hex':expected.hex(),'guards_and_abi_preserved':True});pending=None
                    if a==0x08050254:
                        require(r[4:12]==entries[0]['original_registers'][4:12] and r[13]==entries[0]['original_registers'][13]
                                and r[0]==entries[0]['original_registers'][14],'Floor service did not restore native caller ABI')
                        require(check.completed(row['id']) and check.active is None,'Floor service returned before text completed')
                        require(bytes(m[BANK_RAM:BANK_RAM+len(data)])==data,'Floor service changed supplied bank')
                        # Restore the probe's bank before the original bank caller
                        # resumes its own event script. No game ROM implements this.
                        for i,v in enumerate(saved_bank):m.u8[BANK_RAM+i]=v
                        returned.append(event['frame'])
                    if a in check.ADDRESSES:check.callback(event)
                with Debugger(game,callback,max_events=100000) as debug:
                    for a in set(check.ADDRESSES+(0x0801DFAC,0x08000FB8,0x0805021C,0x08050254)):debug.breakpoint(a)
                    game.press('A',wait=120);game.capture('page-0')
                    for page in range(1,16):
                        if returned:break
                        game.press('A',wait=120);game.capture(f'page-{page}')
                    require(returned and len(formats)==1 and not pending,'Floor service failed to complete')
                require(items(game)==before_items and balance(game)==before_gold,'Floor dialogue changed items/gold')
                require(game.snapshot().battery==fixture.battery,'Floor dialogue probe saved')
                results.append({'case':case,'floor':floor,'selected_index':index,'selected_id':row['id'],'player_hex':name.hex(),
                                'controlled_floor_before':original_floor,'controlled_event_bank_bytes':len(data),'service_entries':entries,
                                'formats':formats,'reads':check.reads,'glyph_checks':check.glyph_checks,'inputs':game.inputs,'bank_restored':True})
    report={'passed':True,'rom_sha256':digest(rom),'cases':results,'scope':'27 controlled native floor-selector calls with bank-five text, floor-byte boundaries and three player-name extremes. The specific consumer uses an owned 288-byte stack message region. Exact formatted bytes, paging/pixels, leading/trailing guards, return ABI, bank restoration, items/gold and save preservation pass. Ordinary final-quest access and other temporary-buffer consumers remain unaccepted.'}
    (OUT/'report.json').write_text(json.dumps(report,indent=2)+'\n');print('Floor progress:',len(results),'native cases passed')

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--cumulative',action='store_true');run(parser.parse_args().cumulative)
