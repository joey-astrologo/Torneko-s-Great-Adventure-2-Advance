"""Exercise both native well acknowledgements and all ten private level labels."""
import argparse,json, struct
import mgba.log
from tools.rom import ROOT, digest, require
from tools.emulator import Session, Debugger, ffi
from tools.well_level_text import add_well_level, CAPACITY
from tools.bakery_playtest import service_ready
from tools.dialogue_checks import TextChecks
from tools.opening_text import BANK_RAM
from tools.lz77 import decompress
from tools.verify_service_ui import materialize
from tools.verify_bank import balance
from tools.holy_flame_playtest import items

OUT = ROOT/'build/well-level-prototype'

def candidate():
    import tools.build_english as english
    prior = english.add_combat; well = None
    def add(build):
        nonlocal well
        result = prior(build); well = add_well_level(build); return result
    try:
        english.add_combat = add; rom, build = english.build_rom(include_story=False)
    finally:
        english.add_combat = prior
    build['well_level'] = well; OUT.mkdir(parents=True, exist_ok=True)
    (OUT/'game.gba').write_bytes(rom)
    (OUT/'build.json').write_text(json.dumps(build, indent=2)+'\n')
    return rom, build

def run(cumulative=False):
    global OUT
    mgba.log.silence()
    if cumulative:
        from tools.build_english import build_rom
        OUT=ROOT/'build/english/well-level-validation';rom,build=build_rom()
    else:rom,build=candidate()
    fixture=service_ready(rom,OUT)
    well = build['well_level']; results = []
    for row in well['entries']:
        bank = next(b for b in well['banks'] if b['id'] == row['bank'])
        data, _ = decompress(rom, bank['offset']); data = bytearray(data)
        for word in range(4):
            struct.pack_into('<I', data, word*4, (struct.unpack_from('<I',data,word*4)[0]+BANK_RAM)&0xFFFFFFFF)
        for level in range(1, 11):
            for initial_flag in (0xA1, 0xA5):
                case = f"{row['bank']}-level-{level}-flag-{initial_flag:02x}"
                print('Well acknowledgement', case, flush=True)
                label = next(r for r in well['labels'] if r['value'] == level)
                with Session(rom, OUT/case) as game:
                    game.restore(fixture); m = game.core.memory
                    saved_bank = bytes(m[BANK_RAM:BANK_RAM+len(data)])
                    for i, value in enumerate(data): m.u8[BANK_RAM+i] = value
                    old_level, old_flag = m.u16[0x02005674], m.u8[0x0201020E]
                    temporary = bytes(m[0x0202F44C:0x0202F4ED])
                    before_items, before_gold = items(game), balance(game)
                    check = TextChecks(game, {}); entries, formats, returned = [], [], []
                    pending = None
                    def callback(event):
                        nonlocal pending
                        a, r = event['address'], event['registers']
                        if a == 0x0801DFAC:
                            require(not entries, 'Repeated well service entry')
                            entries.append(event)
                            m.u16[0x02005674] = level; m.u8[0x0201020E] = initial_flag
                            for reg, value in ((b'r0',row['group']), (b'r1',row['index']), (b'pc',0x08050C14)):
                                require(game.core._core.writeRegister(game.core._core,reg,ffi.new('uint32_t*',value)),
                                        'Controlled well entry failed')
                            return
                        if a == 0x08000FB8 and r[14] == well['formatted']+1:
                            require(r[1] == row['offset']+0x08000000 and r[2] == label['offset']+0x08000000,
                                    'Well getter/level label selected incorrectly')
                            require(r[0] == r[13] and 0x03007000 <= r[13]
                                    and r[0]+CAPACITY <= entries[0]['registers'][13], 'Well buffer outside owned stack')
                            expected = materialize(bytes.fromhex(row['encoded_hex']), [r[2]], m)
                            require(len(expected) <= row['layout']['maximum_formatted_bytes'] <= CAPACITY,
                                    'Well formatted text exceeds bound')
                            pending = (r[0],expected,bytes(m[r[0]+CAPACITY:r[0]+CAPACITY+16]),r[4:12],r[13])
                        if a == well['formatted']:
                            require(pending is not None, 'Missing well formatter entry')
                            dest, expected, guard, regs, sp = pending
                            require(bytes(m[dest:dest+len(expected)]) == expected, 'Well format output differs')
                            require(bytes(m[dest+CAPACITY:dest+CAPACITY+16]) == guard
                                    and r[4:12] == regs and r[13] == sp, 'Well formatter guard/ABI differs')
                            check.resources[dest] = row | {'encoded_hex':expected.hex()}
                            formats.append({'dest':dest,'bytes':len(expected),'expected_hex':expected.hex(),
                                            'capacity':CAPACITY,'guard_and_abi_preserved':True}); pending = None
                        if a == well['returned']:
                            require(r[4:12] == entries[0]['registers'][4:12] and r[13] == entries[0]['registers'][13]
                                    and r[0] == entries[0]['registers'][14], 'Well return ABI differs')
                            require(check.completed(row['id']) and check.active is None, 'Well returned before text finished')
                            require(m.u8[0x0201020E] == initial_flag | 4, 'Well native completion flag differs')
                            require(bytes(m[BANK_RAM:BANK_RAM+len(data)]) == data, 'Well changed supplied bank')
                            for i, value in enumerate(saved_bank): m.u8[BANK_RAM+i] = value
                            returned.append(event['frame'])
                        if a in check.ADDRESSES: check.callback(event)
                    with Debugger(game, callback, max_events=100000) as debug:
                        for address in set(check.ADDRESSES+(0x0801DFAC,0x08000FB8,well['formatted'],well['returned'])):
                            debug.breakpoint(address)
                        game.press('A', wait=120); game.capture('page-0')
                        for page in range(1,8):
                            if returned: break
                            game.press('A',wait=120); game.capture(f'page-{page}')
                        require(returned and len(formats) == 1 and pending is None,
                                f'Well acknowledgement did not finish: entries={len(entries)}, formats={len(formats)}, '
                                f'reads={len(check.reads)}, returned={returned}, pc={int(game.core.cpu.gprs[15]):08x}')
                    require(bytes(m[0x0202F44C:0x0202F4ED]) == temporary, 'Well overwrote original shared temporary storage')
                    require(items(game) == before_items and balance(game) == before_gold, 'Well changed items/gold')
                    require(game.snapshot().battery == fixture.battery, 'Well probe wrote battery')
                    results.append({'case':case,'id':row['id'],'level':level,'initial_flag':initial_flag,
                                    'controlled_level_before':old_level,'controlled_flag_before':old_flag,
                                    'controlled_entry':{'pc':0x08050C14,'r0':row['group'],'r1':row['index']},
                                    'bank_bytes':len(data),'entries':entries,'formats':formats,
                                    'reads':check.reads,'glyph_checks':check.glyph_checks,'inputs':game.inputs,
                                    'bank_restored':True,'shared_temporary_preserved':True})
    report = {'passed':True,'rom_sha256':digest(rom),'cases':results,
              'scope':'40 controlled native well acknowledgement calls: both banks, all ten levels and completion bit initially clear/set. Private labels, exact format, 256-byte stack buffer, guard/ABI, pixels/paging, original shared temporary bytes, items/gold and battery pass. Original level menu and ordinary well progression remain separate.'}
    (OUT/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Well acknowledgements:',len(results),'native cases passed')

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--cumulative',action='store_true');run(parser.parse_args().cumulative)
