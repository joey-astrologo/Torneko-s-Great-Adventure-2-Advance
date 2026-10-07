"""Check the baker producer's dungeon gate and native floor-exit predicate.

Bounds the recovered generation/exit path. This is not a proof about arbitrary
actor mutations, edited saves or every writer of the floor field.
"""
import json
from pathlib import Path
import struct

import mgba.log
from tools.audit_reader_routes import direct_calls
from tools.bakery_playtest import service_ready
from tools.emulator import Session
from tools.research_event_relocation import invoke
from tools.rom import ROOT, default_rom, digest, load_base, require


def run():
    mgba.log.silence()
    out = ROOT/'build/oct07-text/companion-domain'
    out.mkdir(parents=True, exist_ok=True)
    original = load_base()
    source_save = default_rom().with_suffix('.sav')
    save_hash = digest(source_save.read_bytes())
    rom = (ROOT/'build/torneko-2-english.gba').read_bytes()
    build = json.loads((ROOT/'build/english/build.json').read_text())
    require(digest(rom) == build['output_sha256'], 'Root build identity differs')
    guards = []
    for lo, hi in ((0x28EC4, 0x28F00), (0x41D10, 0x41D20),
                   (0x58CC, 0x59F0), (0x59F0, 0x5AC8),
                   (0x54CC, 0x54E6), (0x1BACC, 0x1BC24),
                   (0x1417EE, 0x141808), (0x1481B4, 0x14825C)):
        require(original[lo:hi] == rom[lo:hi], 'Companion producer/exit code changed')
        guards.append(dict(start=lo, end_exclusive=hi,
                           sha256=digest(original[lo:hi])))
    u32 = lambda at: struct.unpack_from('<I', original, at)[0]
    require(u32(0x28F00) == 0x02003B6C and u32(0x41D1C) == 0x0200160C,
            'Baker spawn gate fields differ')
    require(u32(0x59E4) == u32(0x5AC4) == 0x081417EE and
            struct.unpack_from('<h', original, 0x1417F0)[0] == 7,
            'Cemetery exit threshold differs')
    require(u32(0x59E8) == u32(0x5538) == 0x020037CA,
            'Exit owner/loop flag differs')
    require(direct_calls(original[:0x5E000], 0x080058CC) == [0x080054CE] and
            direct_calls(original[:0x5E000], 0x0801BACC) == [0x08005994],
            'Floor progression has another direct caller')
    # The disassembled producer compares dungeon 1, tests completion bit 1
    # clear, and passes species 86h to 28D34. Completion at the threshold clears
    # all 55 non-player actors before its scene and sets the main loop exit byte.
    require(original[0x28EC8:0x28ED2] == bytes.fromhex('01281bd1012018f01fff') and
            original[0x28EFA:0x28EFC] == bytes.fromhex('8621'),
            'Reinspect baker spawn condition')
    table = u32(0x1BC1C)-0x08000000
    require(table == 0x1481B4 and all(struct.unpack_from('<h', original, table+12*i)[0]
                                    for i in (1, 13)), 'Exit metadata missing')
    texts = []
    private = build['companion']['table_offset']
    for row in build['companion']['entries']:
        floor = row['floor']
        at = private+4*(0x1DF+floor)
        pointer = struct.unpack_from('<I', rom, at)[0]
        raw = bytes.fromhex(row['encoded_hex'])
        require(pointer == 0x08000000+row['offset'] and
                rom[row['offset']:row['offset']+len(raw)] == raw, 'Companion English binding differs')
        texts.append(dict(floor=floor, id=row['id'], pointer=pointer))
    require({r['floor'] for r in texts} == set(range(1, 7)), 'Companion floor domain differs')

    fixture = service_ready(rom, out)
    cases = []
    with Session(rom, out/'native') as game:
        for complete in (0, 1):
            for mode in (0, 2):
                for floor in range(1, 7):
                    game.restore(fixture)
                    m = game.core.memory
                    controls = []
                    fields = [(0x02003B6C, 4, 1), (0x02005674, 2, floor),
                              (0x02001594, 4, 0xFFFFFFFF), (0x020037C4, 2, mode),
                              (0x0200160C, 4, (m.u32[0x0200160C] & ~2) | (complete*2))]
                    for address, size, value in fields:
                        before = bytes(m[address:address+size]).hex()
                        raw = value.to_bytes(size, 'little')
                        for i, byte in enumerate(raw):
                            m.u8[address+i] = byte
                        controls.append(dict(address=address, before=before, after=raw.hex()))
                    result = invoke(game, 0x080059F0, [])
                    next_floor = floor+(5 if mode == 2 else 1)
                    require(result == int(next_floor >= 7), 'Native floor-exit predicate differs')
                    require(game.snapshot().battery == fixture.battery, 'Floor probe wrote battery')
                    cases.append(dict(floor=floor, progression_mode=mode, complete=bool(complete),
                        candidate_floor=next_floor, exits=bool(result), controls=controls,
                        abi_preserved=True, battery_preserved=True))
    require(digest(default_rom().read_bytes()) == digest(original) and
            digest(source_save.read_bytes()) == save_hash, 'Source files changed')
    report = dict(passed=True, rom_sha256=digest(rom), source_sha256=digest(original),
        source_save_sha256=save_hash, tool_sha256=digest(Path(__file__).read_bytes()),
        checked_code=guards, native_exit_cases=cases, english_bindings=texts,
        producer=dict(dungeon=1, completion_bit=1, required_bit_value=0, species=0x86,
                      site=0x08028EFA, allocator=0x08028D34),
        threshold=dict(table=0x081417EE, value=7, normal_play_floors=[1, 2, 3, 4, 5, 6]),
        scope='The recovered baker generator requires Cemetery Dungeon and its completion '
              'bit clear. Floor progression reaches completion at candidate floor >=7; '
              '24 native exit-predicate cases cover +1/+5 modes and both completion states. '
              'Six existing English bindings match this domain. Isolated predicate calls '
              'do not replay the completion scene, prove every actor/floor writer or '
              'establish arbitrary save-state validity. No ROM patch.')
    (out/'report.json').write_text(json.dumps(report, indent=2)+'\n')
    print('Companion domain:', len(cases), 'native exit cases;', len(texts), 'English bindings')


if __name__ == '__main__':
    run()
