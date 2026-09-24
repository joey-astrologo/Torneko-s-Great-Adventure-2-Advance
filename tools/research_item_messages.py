"""Capture shared formatter contexts through controlled native item-use actions."""
import json
import struct
import mgba.log
from tools.rom import ROOT, digest, require
from tools.emulator import Session, Debugger
from tools.build_english import build_rom
from tools.service_fixtures import dungeon
from tools.extract_shared_text import extract
from tools.verify_service_ui import cstring

OUT = ROOT / 'build/shared-text/item-use'


def run():
    mgba.log.silence()
    rom, build = build_rom()
    fixture = dungeon(rom, build)
    source = {r['source']['offset'] + 0x08000000: r for r in extract()['entries']}
    names = {r['id']: r['name'] for r in json.loads((ROOT / 'translations/items-review.json').read_text())['entries']}
    results = []
    for ident in (169, 170, 171, 172, 173, 174, 175, 176, 177, 178, 180, 182, 189, 190):
        out = OUT / str(ident)
        with Session(rom, out) as game:
            game.restore(fixture)
            memory = game.core.memory
            slot = 0x0200DF28
            original = bytes(memory[slot:slot + 120])
            replacement = bytearray(original)
            mapping = bytes(memory[0x020013D0:0x020014D0])
            struct.pack_into('<I', replacement, 0, 0xC8000000)
            replacement[8] = mapping.index(ident)
            replacement[4] = replacement[5] = 1
            replacement[24:] = bytes(96)
            for index, value in enumerate(replacement):
                memory.u8[slot + index] = value
            type_address = 0x02003BAC + ident * 20
            original_type = memory.u32[type_address]
            memory.u32[type_address] = original_type | 0x40000000
            formats, queues = [], []
            seen = set()

            def callback(event):
                registers, address = event['registers'], event['address']
                if address == 0x08000FB8 and registers[1] in source:
                    row = source[registers[1]]
                    key = f"shared.{row['table_offset']:03x}-{registers[14]:08x}"
                    if key in seen:
                        return
                    seen.add(key)
                    game.snapshot().save(out / key)
                    values = registers[2:4] + [memory.u32[registers[13] + n * 4] for n in range(4)]
                    strings = []
                    for value in values:
                        if 0x02000000 <= value < 0x02040000 or 0x08000000 <= value < 0x08000000 + len(rom):
                            try:
                                strings.append(cstring(memory, value, 256).hex())
                            except ValueError:
                                strings.append(None)
                        else:
                            strings.append(None)
                    formats.append({'source': row, 'snapshot': str((out / key).relative_to(ROOT)),
                                    'frame': event['frame'], 'registers': registers,
                                    'argument_words': values, 'possible_string_arguments_hex': strings})
                elif address == 0x0801588C:
                    queues.append({'frame': event['frame'], 'pointer': registers[0],
                                   'return': registers[14], 'raw_hex': cstring(memory, registers[0], 512).hex()})

            with Debugger(game, callback, max_events=20000) as debug:
                debug.breakpoint(0x08000FB8)
                debug.breakpoint(0x0801588C)
                game.press('B', hold=8, wait=30)
                game.press('A', wait=30)
                game.press('A', wait=30)
                actions = []
                for index in range(7):
                    value = memory.u16[0x0200CDD0 + index * 2]
                    if not value:
                        break
                    actions.append(value)
                require(13 in actions, 'Native Drink action missing: ' + str(ident))
                for _ in range(actions.index(13)):
                    game.press('DOWN', wait=20)
                game.capture('before-drink')
                game.press('A', wait=180)
                game.capture('effect')
            require(formats or queues, 'No native item-use messages observed')
            results.append({'item_id': ident, 'item_name': names[ident],
                            'controlled_record': {'address': slot, 'before': original.hex(), 'after': replacement.hex()},
                            'controlled_type_flags': {'address': type_address, 'before': original_type, 'after': original_type | 0x40000000},
                            'actions': actions, 'formats': formats, 'queues': queues, 'inputs': game.inputs})
            print('Item-use messages:', ident, names[ident], [hex(r['source']['table_offset']) for r in formats], flush=True)
    report = {'rom_sha256': digest(rom), 'source_fixture_sha256': digest(fixture.state),
              'cases': results, 'scope': 'Controlled replacement of one disposable inventory record and its identification bit. The original native Drink action and effects execute through ordinary inputs thereafter. No natural item acquisition or English insertion claimed. Captured formatter arguments and snapshots establish consumers for further buffer/control investigation.'}
    (OUT / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    return report


if __name__ == '__main__':
    run()
