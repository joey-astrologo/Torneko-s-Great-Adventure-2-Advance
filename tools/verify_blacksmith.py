"""Controlled native blacksmith entry, prose, format and question checks."""
import argparse
import json
import struct
import mgba.log
from tools.rom import ROOT, digest, require
from tools.emulator import Session, Debugger, Snapshot, ffi
from tools.blacksmith_text import add_blacksmith
from tools.bakery_playtest import service_ready
from tools.dialogue_checks import TextChecks, player_layout_cases
from tools.name_entry import HERO
from tools.verify_service_ui import materialize

OUT = ROOT / 'build/blacksmith-prototype'


def candidate():
    from tools import build_english as english
    prior = english.add_combat
    resource = None
    def add(build):
        nonlocal resource
        result = prior(build)
        resource = add_blacksmith(build)
        return result
    try:
        english.add_combat = add
        rom, build = english.build_rom(include_story=False, include_extra_consumers=False)
    finally:
        english.add_combat = prior
    build['blacksmith'] = resource
    build['reviewed_resource_counts']['blacksmith'] = len(resource['entries'])
    build['total_reviewed_inserted_resources'] += len(resource['entries'])
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'game.gba').write_bytes(rom)
    (OUT / 'build.json').write_text(json.dumps(build, indent=2) + '\n')
    return rom, build


def contexts(rom):
    fixture = service_ready(rom, OUT)
    paths = {name: OUT / 'native' / name for name in ('entry', 'offer', 'farewell')}
    if all(p.with_suffix('.json').exists() and Snapshot.load(p).rom_sha256 == digest(rom) for p in paths.values()):
        return {name: Snapshot.load(path) for name, path in paths.items()}
    for answer in ('yes', 'no'):
        with Session(rom, OUT / ('context-' + answer)) as game:
            game.restore(fixture)
            events, saved = [], set()
            def callback(event):
                a, r = event['address'], event['registers']
                if a == 0x0801DFAC:
                    events.append(event | {'redirected_pc': 0x0801D110, 'r1_after': 0})
                    game.core.cpu.gprs[1] = 0
                    require(game.core._core.writeRegister(game.core._core, b'pc', ffi.new('uint32_t*', 0x0801D110)), 'Blacksmith redirect failed')
                    game.snapshot().save(paths['entry'])
                    saved.add('entry')
                name = ('entry' if a == 0x0801D110 else 'offer' if a == 0x08000FB8 and r[14] in (0x0801D181, 0x0801D1A7)
                        else 'farewell' if a == 0x0801D0A0 and r[14] == 0x0801D313 else None)
                if name and name not in saved:
                    game.snapshot().save(paths[name])
                    events.append(event | {'snapshot': name})
                    saved.add(name)
            with Debugger(game, callback, max_events=10000) as debug:
                for a in (0x0801DFAC, 0x0801D110, 0x08000FB8, 0x0801D0A0):
                    debug.breakpoint(a)
                game.press('A', wait=120)
                for _ in range(30):
                    if ('offer' if answer == 'yes' else 'farewell') in saved:
                        break
                    game.press('A' if answer == 'yes' else 'B', wait=120)
                game.capture('context')
            (game.output / 'provenance.json').write_text(json.dumps({'rom_sha256': digest(rom), 'events': events, 'inputs': game.inputs}, indent=2) + '\n')
            require(('offer' if answer == 'yes' else 'farewell') in saved, 'Blacksmith context missing: ' + answer)
    return {name: Snapshot.load(path) for name, path in paths.items()}


def run(cumulative=False):
    global OUT
    mgba.log.silence()
    if cumulative:
        OUT = ROOT / 'build/english/blacksmith-validation'
        rom = (ROOT / 'build/english/torneko-2-english.gba').read_bytes()
        build = json.loads((ROOT / 'build/english/build.json').read_text())
        require(digest(rom) == build['output_sha256'], 'Blacksmith cumulative ROM differs')
    else:
        rom, build = candidate()
    fixtures = contexts(rom)
    rows = build['blacksmith']['entries']
    with Session(rom, OUT / 'entry-inspection') as game:
        game.restore(fixtures['entry'])
        original_regs = [int(v) & 0xFFFFFFFF for v in game.core.cpu.gprs]
        original_guard = bytes(game.core.memory[original_regs[13]:original_regs[13] + 32])
    # ROM-backed base names reserve80px/30 content bytes, independent of item rows.
    item_names = [r for r in build['items']['entries'] if r['id'].startswith('item.name.')]
    from tools.compact_font import measure
    widest = max(item_names, key=lambda r: measure(r['english']))
    longest = max(item_names, key=lambda r: len(bytes.fromhex(r['encoded_hex'])))
    results = []
    for row in rows:
        formatted = not row['layout']['direct_rom_stream']
        names = player_layout_cases() if '{player}' in row['english'] else [('native', None)]
        fields = [('wide', widest, 120), ('bytes', longest, 0)] if formatted else [('plain', None, None)]
        for label, player in names:
            for variant, item, count in fields:
                case = row['id'] + '-' + label + '-' + variant
                print('Blacksmith:', case, flush=True)
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
                        args = ([count & 0xFFFFFFFF] if '{count}' in row['english'] else
                                [item['offset'] + 0x08000000] * expected.count(b'%s'))
                        for i, value in enumerate(args):
                            reg(i + 2, value)
                        expected = materialize(expected, args, m)
                        dest = int(game.core.cpu.gprs[0]); sp = int(game.core.cpu.gprs[13])
                        saved = [int(game.core.cpu.gprs[i]) for i in range(4, 12)]
                        end = int(game.core.cpu.gprs[14]) & ~1
                        require(dest == sp and len(expected) <= row['layout']['maximum_formatted_bytes'] <= 512, 'Blacksmith output reserve differs')
                        guard = bytes(m[dest + 512:dest + 544])
                        dynamic = row | {'encoded_hex': expected.hex()}
                    else:
                        reg(0, target)
                        dest, end, dynamic = target, None, row
                    resources = {r['offset'] + 0x08000000: r for r in rows if r['layout']['direct_rom_stream']}
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
                            require(bytes(m[dest:dest + len(expected)]) == expected and bytes(m[dest + 512:dest + 544]) == guard,
                                    'Blacksmith formatted bytes/guard differ')
                            require(r[13] == sp and r[4:12] == saved, 'Blacksmith formatter ABI differs')
                            formats.append({'expected_hex': expected.hex(), 'bytes': len(expected), 'capacity': 512, 'guard_preserved': True})
                        if a == 0x0801D542:
                            require(r[4:12] == original_regs[4:12] and r[13] == original_regs[13] and r[0] == original_regs[14],
                                    'Blacksmith whole-consumer return ABI differs')
                            require(bytes(m[r[13]:r[13] + 32]) == original_guard, 'Blacksmith caller guard changed')
                            returned.append(event)
                        check.callback(event)
                    with Debugger(game, callback, max_events=160000) as debug:
                        for address in set(check.ADDRESSES + (0x0801D542,) + ((end,) if end else ())):
                            debug.breakpoint(address)
                        for page in range(30):
                            game.frames(90)
                            name = f'page-{page:02}'
                            game.capture(name); images.append(name + '.png')
                            if returned:
                                break
                            game.press('B', wait=0)
                    require(returned and check.active is None and check.completed(row['id']), 'Blacksmith text/return incomplete')
                    require(not formatted or len(formats) == 1, 'Blacksmith format missing')
                    require(bytes(m[0x0200DF28:0x0200DF28 + 20 * 120]) == inventory and m.u32[gold_address] == gold,
                            'Declined blacksmith probe changed inventory/gold')
                    require(game.snapshot().battery == fixture.battery, 'Blacksmith probe wrote battery')
                    results.append({'case': case, 'id': row['id'], 'controlled_overrides': overrides, 'formats': formats,
                                    'reads': check.reads, 'glyph_checks': check.glyph_checks, 'inputs': game.inputs,
                                    'images': {p: digest((game.output / p).read_bytes()) for p in images}})
    report = {'passed': True, 'rom_sha256': digest(rom), 'sources': len(rows), 'cases': results,
              'scope': 'Controlled bank invocation reaches the private blacksmith consumer. Plain sources replace its farewell argument; formatted sources replace the actual512-byte offer formatter arguments. Native source rendering, paging, player-name and item-name extremes, valid native job counts0/120, output guards, whole-consumer return ABI and unchanged inventory/gold/battery are checked. Ordinary unlocking, successful exchanges, tip branching and unowned sources1/2/68 remain separate. Corrupt negative counters are not supported or claimed.'}
    (OUT / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print('Blacksmith:', len(results), 'cases passed', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cumulative', action='store_true')
    run(parser.parse_args().cumulative)
