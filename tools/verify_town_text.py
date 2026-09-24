"""Check native shared-town decompression and all 300 pointer relocations."""

import json
import struct
from pathlib import Path

import mgba.log

from tools.emulator import Debugger, Session, Snapshot
from tools.lz77 import decompress
from tools.rom import ROOT, digest, load_base, require
from tools.town_text import COUNT, RAM, entries, relocate, resource


def verify_case(rom, fixture, output, compressed):
    decoded, end = decompress(rom, compressed)
    expected = relocate(decoded)
    snapshot = Snapshot.load(fixture)
    events, before = [], None
    with Session(rom, output) as game:
        game.restore(snapshot)
        def callback(event):
            nonlocal before
            r, a, m = event['registers'], event['address'], game.core.memory
            tail = RAM + len(decoded)
            if a == 0x0804D72E:
                require(r[:2] == [0x08000000 + compressed, RAM], 'Shared town loader arguments differ')
                before = (bytes(m[RAM - 64:RAM]), bytes(m[tail:tail + 64]), r[4:12], r[13])
            elif a == 0x0804D732:
                require(bytes(m[RAM:tail]) == decoded, 'Shared town native decode differs')
                require(before == (bytes(m[RAM - 64:RAM]), bytes(m[tail:tail + 64]), r[4:12], r[13]),
                        'Town decoder changed guards/registers/SP')
                events.append({'raw_decode_sha256': digest(decoded), 'guards_and_registers_preserved': True,
                               'frame': event['frame']})
            elif a == 0x0804D746:
                require(bytes(m[RAM:tail]) == expected, 'Shared town pointer relocation differs')
                require(before[:2] == (bytes(m[RAM - 64:RAM]), bytes(m[tail:tail + 64])), 'Town relocation changed guards')
                events[-1].update(relocated_sha256=digest(expected), relocated_pointer_count=COUNT,
                                  source_bytes_outside_pointer_table_preserved=True)
        with Debugger(game, callback) as debugger:
            for address in (0x0804D72E, 0x0804D732, 0x0804D746):
                debugger.breakpoint(address)
            game.press('A', wait=180)
        require(len(events) == 1 and events[0].get('relocated_pointer_count') == COUNT, 'Town loader was not observed once')
        return {'rom_sha256': digest(rom), 'fixture_state_sha256': digest(snapshot.state),
                'decoded_bytes': len(decoded), 'compressed_rom_offset': compressed,
                'compressed_end_exclusive': end, 'loads': events, 'inputs': game.inputs}


def run():
    mgba.log.silence()
    output = ROOT / 'build/english/town-text-validation'
    build = json.loads((ROOT / 'build/english/build.json').read_text())
    rom = (ROOT / build['output_rom']).read_bytes()
    original = resource()
    translated = build['dialogue']['town_resource']
    cases = [verify_case(load_base(), ROOT / 'build/english/home-validation/japanese-destination/home-menu',
                         output / 'japanese', original['rom_offset']),
             verify_case(rom, ROOT / 'build/english/destination-validation/home-menu',
                         output / 'english', translated['rom_offset'])]
    table = entries()
    report = {'passed': True, 'source_rom_sha256': digest(load_base()), 'output_rom_sha256': digest(rom),
              'cases': cases, 'pointer_slots': len(table), 'unique_sources': len({r['id'] for r in table}),
              'scope': 'Natural town loader in each ROM, raw decode/guards and all 300 relocated pointers. Individual table entries outside tested book routes are not claimed naturally displayed.'}
    (output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print('Shared town text: two native loads; 600 relocated pointer checks')
    return report


if __name__ == '__main__':
    run()
