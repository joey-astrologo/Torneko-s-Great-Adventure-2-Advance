"""Controlled native gaibara entry, prose, format and question checks."""
import argparse
import json
import struct
import mgba.log
from tools.rom import ROOT, digest, require
from tools.emulator import Session, Debugger, Snapshot, ffi
from tools.gaibara_text import add_gaibara
from tools.selection_prompt_text import add_selection_prompt
from tools.bakery_playtest import service_ready
from tools.dialogue_checks import TextChecks, player_layout_cases
from tools.name_entry import HERO
from tools.verify_service_ui import materialize

OUT = ROOT / 'build/gaibara-prototype'


def candidate():
    from tools import build_english as english
    prior = english.add_combat
    resource = heading = None
    def add(build):
        nonlocal resource, heading
        result = prior(build)
        resource = add_gaibara(build)
        heading = add_selection_prompt(build)
        return result
    try:
        english.add_combat = add
        rom, build = english.build_rom(include_story=False, include_extra_consumers=False)
    finally:
        english.add_combat = prior
    build['gaibara'] = resource
    build['selection_prompt'] = heading
    build['reviewed_resource_counts']['gaibara'] = len(resource['entries'])
    build['total_reviewed_inserted_resources'] += len(resource['entries'])
    build['reviewed_resource_counts']['selection_prompt'] = len(heading['entries'])
    build['total_reviewed_inserted_resources'] += len(heading['entries'])
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'game.gba').write_bytes(rom)
    (OUT / 'build.json').write_text(json.dumps(build, indent=2) + '\n')
    return rom, build


def contexts(rom):
    fixture = service_ready(rom, OUT)
    paths = {name: OUT / 'native' / name for name in ('entry', 'offer', 'farewell')}
    revision_path = OUT / 'native/context-revision.txt'
    revision = digest((ROOT / 'tools/verify_gaibara.py').read_bytes())
    if revision_path.exists() and revision_path.read_text() == revision and all(p.with_suffix('.json').exists() and Snapshot.load(p).rom_sha256 == digest(rom) for p in paths.values()):
        return {name: Snapshot.load(path) for name, path in paths.items()}
    for answer in ('yes', 'no'):
        with Session(rom, OUT / ('context-' + answer)) as game:
            game.restore(fixture)
            m = game.core.memory
            overrides = []
            def write(address, data):
                overrides.append({'address': address, 'before': bytes(m[address:address + len(data)]).hex(), 'after': data.hex()})
                for i, value in enumerate(data): m.u8[address + i] = value
            mapping = bytes(m[0x020013D0:0x020014D0])
            inventory = bytearray(20 * 120)
            for slot, ident in enumerate((1, 2)):
                struct.pack_into('<I', inventory, slot * 120, 0xC8000000)
                inventory[slot * 120 + 5] = 1
                inventory[slot * 120 + 8] = mapping.index(ident)
                address = 0x02003BAC + ident * 20
                write(address, struct.pack('<I', m.u32[address] | 0x40000000))
            write(0x0200DF28, inventory)
            write(0x02002C17, b'\x01')
            events, saved = [], set()
            def callback(event):
                a, r = event['address'], event['registers']
                if a == 0x0801DFAC:
                    events.append(event | {'redirected_pc': 0x0801D544, 'r1_after': 0, 'r2_after': 0})
                    game.core.cpu.gprs[1] = 0
                    game.core.cpu.gprs[2] = 0
                    require(game.core._core.writeRegister(game.core._core, b'pc', ffi.new('uint32_t*', 0x0801D544)), 'Gaibara redirect failed')
                    game.snapshot().save(paths['entry'])
                    saved.add('entry')
                name = ('entry' if a == 0x0801D544 else 'offer' if a == 0x08000FB8 and r[14] == 0x0801D661
                        else 'farewell' if a == 0x0801D0A0 and r[14] == 0x0801D773 else None)
                if name and name not in saved:
                    game.snapshot().save(paths[name])
                    events.append(event | {'snapshot': name})
                    saved.add(name)
            with Debugger(game, callback, max_events=10000) as debug:
                for a in (0x0801DFAC, 0x0801D544, 0x08000FB8, 0x0801D0A0):
                    debug.breakpoint(a)
                game.press('A', wait=120)
                for _ in range(60):
                    if ('offer' if answer == 'yes' else 'farewell') in saved:
                        break
                    game.press('A' if answer == 'yes' else 'B', wait=120)
                game.capture('context')
            (game.output / 'provenance.json').write_text(json.dumps({'rom_sha256': digest(rom), 'events': events, 'controlled_overrides': overrides, 'inputs': game.inputs}, indent=2) + '\n')
            require(('offer' if answer == 'yes' else 'farewell') in saved, 'Gaibara context missing: ' + answer)
    revision_path.write_text(revision)
    return {name: Snapshot.load(path) for name, path in paths.items()}


def run(cumulative=False):
    global OUT
    mgba.log.silence()
    if cumulative:
        OUT = ROOT / 'build/english/gaibara-validation'
        rom = (ROOT / 'build/english/torneko-2-english.gba').read_bytes()
        build = json.loads((ROOT / 'build/english/build.json').read_text())
        require(digest(rom) == build['output_sha256'], 'Gaibara cumulative ROM differs')
    else:
        rom, build = candidate()
    fixtures = contexts(rom)
    rows = build['gaibara']['entries']
    with Session(rom, OUT / 'entry-inspection') as game:
        game.restore(fixtures['entry'])
        original_regs = [int(v) & 0xFFFFFFFF for v in game.core.cpu.gprs]
        original_guard = bytes(game.core.memory[original_regs[13]:original_regs[13] + 32])
    # The synthesis formatter receives the complete native64-byte item field.
    results = []
    for row in rows:
        if row['index'] == 112: continue  # Separate root-menu checks.
        formatted = not row['layout']['direct_rom_stream']
        names = player_layout_cases() if '{player}' in row['english'] else [('native', None)]
        fields = [('native', None, 10), ('wide', None, 2147483647), ('bytes', None, 0)] if formatted else [('plain', None, None)]
        for label, player in names:
            for variant, item, count in fields:
                case = row['id'] + '-' + label + '-' + variant
                print('Gaibara:', case, flush=True)
                with Session(rom, OUT / case) as game:
                    fixture = fixtures['offer' if formatted else 'farewell']
                    game.restore(fixture)
                    m = game.core.memory
                    overrides = []
                    def reg(index, value):
                        overrides.append({'register': index, 'before': int(game.core.cpu.gprs[index]), 'after': value})
                        value &= 0xFFFFFFFF
                        game.core.cpu.gprs[index] = value if value < 0x80000000 else value - 0x100000000
                    if player:
                        overrides.append({'address': HERO, 'before': bytes(m[HERO:HERO + 16]).hex(), 'after': player.ljust(16, b'\0').hex()})
                        for i, value in enumerate(player.ljust(16, b'\0')):
                            m.u8[HERO + i] = value
                    target = row['offset'] + 0x08000000
                    formats, returned, reads, images = [], [], [], []
                    expected = bytes.fromhex(row['encoded_hex'])
                    if formatted:
                        reg(1, target)
                        if row['index'] == 52:
                            args = [count]
                        else:
                            name_pointer = int(game.core.cpu.gprs[2])
                            require(name_pointer == int(game.core.cpu.gprs[13]) + 0x1F8, 'Synthesis item field differs')
                            if variant != 'native':
                                from tools.compact_font import encode
                                name_payload = encode('W' * 27) if variant == 'wide' else encode('i' * 31)[:-1] + b' \0'
                                require(len(name_payload) <= 64, 'Synthesis controlled item field overflow')
                                overrides.append({'address': name_pointer, 'before': bytes(m[name_pointer:name_pointer + 64]).hex(), 'after': name_payload.ljust(64, b'\0').hex()})
                                for i, value in enumerate(name_payload.ljust(64, b'\0')): m.u8[name_pointer + i] = value
                            args = [name_pointer]
                        for i, value in enumerate(args):
                            reg(i + 2, value)
                        expected = materialize(expected, args, m)
                        dest = int(game.core.cpu.gprs[0]); sp = int(game.core.cpu.gprs[13])
                        saved = [int(game.core.cpu.gprs[i]) & 0xFFFFFFFF for i in range(4, 12)]
                        end = int(game.core.cpu.gprs[14]) & ~1
                        require(dest == sp + 0xF8 and len(expected) <= row['layout']['maximum_formatted_bytes'] <= 256, 'Gaibara output reserve differs')
                        guard = bytes(m[dest + 256:dest + 288])
                        dynamic = row | {'encoded_hex': expected.hex()}
                    else:
                        reg(0, target)
                        dest, end, dynamic = target, None, row
                    resources = {r['offset'] + 0x08000000: r for r in rows if r['layout']['direct_rom_stream']}
                    resources.update({r['offset'] + 0x08000000: r for r in build['selection_prompt']['entries']})
                    resources[dest] = dynamic
                    choice = next(r for r in build['dialogue']['entries'] if r['id'] == 'rom.0006309c')
                    resources[choice['rom_offset'] + 0x08000000] = choice
                    check = TextChecks(game, resources)
                    inventory = bytes(m[0x0200DF28:0x0200DF28 + 20 * 120])
                    gold_address = m.u32[0x02001624] + 0x60
                    gold = m.u32[gold_address]
                    def callback(event):
                        a, r = event['address'], event['registers']
                        if formatted and a == end and not formats:
                            require(bytes(m[dest:dest + len(expected)]) == expected and bytes(m[dest + 256:dest + 288]) == guard,
                                    'Gaibara formatted bytes/guard differ')
                            require(r[13] == sp and r[4:12] == saved, 'Gaibara formatter ABI differs')
                            formats.append({'expected_hex': expected.hex(), 'bytes': len(expected), 'capacity': 256, 'guard_preserved': True})
                        if a == 0x0801D822:
                            require(r[4:12] == original_regs[4:12] and r[13] == original_regs[13] and r[0] == original_regs[14],
                                    'Gaibara whole-consumer return ABI differs')
                            require(bytes(m[r[13]:r[13] + 32]) == original_guard, 'Gaibara caller guard changed')
                            returned.append(event)
                        check.callback(event)
                    with Debugger(game, callback, max_events=160000) as debug:
                        for address in set(check.ADDRESSES + (0x0801D822,) + ((end,) if end else ())):
                            debug.breakpoint(address)
                        for page in range(30):
                            game.frames(90)
                            name = f'page-{page:02}'
                            game.capture(name); images.append(name + '.png')
                            if returned:
                                break
                            game.press('B', wait=0)
                    require(returned and check.active is None and check.completed(row['id']), 'Gaibara text/return incomplete')
                    require(not formatted or len(formats) == 1, 'Gaibara format missing')
                    require(bytes(m[0x0200DF28:0x0200DF28 + 20 * 120]) == inventory and m.u32[gold_address] == gold,
                            'Declined gaibara probe changed inventory/gold')
                    require(game.snapshot().battery == fixture.battery, 'Gaibara probe wrote battery')
                    results.append({'case': case, 'id': row['id'], 'controlled_overrides': overrides, 'formats': formats,
                                    'reads': check.reads, 'glyph_checks': check.glyph_checks, 'inputs': game.inputs,
                                    'images': {p: digest((game.output / p).read_bytes()) for p in images}})
    report = {'passed': True, 'rom_sha256': digest(rom), 'sources': len(rows) - 1, 'cases': results,
              'scope': 'Controlled native synthesis consumer. Plain sources replace the farewell pointer; three formats replace the actual256-byte base-confirmation formatter arguments. Existing64-byte item field, native and maximum width/byte cases, positive32-bit cost stress bounds, paired price colour controls, paging, output and whole-consumer return ABI, inventory/gold/battery are checked. The root menu, actual synthesis and ordinary unlocking have separate evidence.'}
    (OUT / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print('Gaibara:', len(results), 'cases passed', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cumulative', action='store_true')
    run(parser.parse_args().cumulative)
