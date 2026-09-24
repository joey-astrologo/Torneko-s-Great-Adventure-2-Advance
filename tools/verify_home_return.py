"""Verify bank-one English through the first evening/morning and village choices."""

import argparse
import json
from pathlib import Path

import mgba.log

from tools.build_english import build_rom
from tools.dialogue_checks import TextChecks, player_layout_cases
from tools.emulator import BIOS, Debugger, Session, Snapshot, version
from tools.event_text import table_entries
from tools.home_sale import BUFFER, ORIGINAL as SALE_ORIGINAL, materialize
from tools.lz77 import decompress
from tools.name_entry import HERO
from tools.opening_text import BANK_RAM, banks
from tools.rom import ROOT, default_rom, digest, load_base, require
from tools.town_playtest import position, face_home_roamer
from tools.trace_home_return import ROUTES
from tools.verify_compact_font import call_thumb

OUTPUT = ROOT / 'build/english/home-validation'
FIXTURE = ROOT / 'build/english/destination-validation/home-menu'
JAPANESE = ROOT / 'build/home-return/research/village'


def run(fixture=FIXTURE, output=OUTPUT, japanese_fixture=JAPANESE):
    mgba.log.silence()
    original, (rom, build) = load_base(), build_rom()
    save = default_rom().with_suffix('.sav')
    save_hash = digest(save.read_bytes())
    route_data = json.loads(ROUTES.read_text())
    snapshot = Snapshot.load(fixture)
    bank = banks()[1]
    packed = next(b for b in build['dialogue']['banks'] if b['id'] == bank['id'])
    decoded, _ = decompress(rom, packed['bank_rom_offset'])
    tables = {(r['group'], r['index']): r for r in table_entries(bank)}
    resources = {0x08000000 + r['rom_offset']: r for r in build['dialogue']['entries']
                 if r['batch'] == 'home-return' or r['id'] == 'rom.0006309c'}
    targets = {r['id']: address for address, r in resources.items()}
    sale = resources[targets['rom.0006c424']]
    expected_home = ['rom.0006c424' if x == 'generated.0202f44c' else x for x in route_data['home_reads']]
    results = []
    with Session(rom, output) as game:
        for route in [{'id': 'evening-morning', 'reads': expected_home}] + route_data['routes']:
            home = route['id'] == 'evening-morning'
            game.restore(snapshot if home else Snapshot.load(output / 'village'))
            input_start = len(game.inputs) - 1
            checks = TextChecks(game, dict(resources))
            choices, commands, loads, slots, formats = [], [], [], [], []
            choice_active, chose_no, bank_before, format_before = False, False, None, None

            def callback(event):
                nonlocal choice_active, bank_before, format_before
                r, a, m = event['registers'], event['address'], game.core.memory
                if a == 0x0804D722:
                    require(r[0] == 0x08000000 + packed['bank_rom_offset'], 'English home loaded another bank')
                    end = BANK_RAM + len(decoded)
                    bank_before = bytes(m[BANK_RAM - 64:BANK_RAM]), bytes(m[end:end + 64]), r[4:12], r[13]
                elif a == 0x0804D726:
                    end = BANK_RAM + len(decoded)
                    require(bytes(m[BANK_RAM:end]) == decoded, 'Native rebuilt bank-one bytes differ')
                    require(bank_before == (bytes(m[BANK_RAM - 64:BANK_RAM]), bytes(m[end:end + 64]), r[4:12], r[13]),
                            'Bank-one decompression changed guards or preserved registers/SP')
                    loads.append({'decoded_bytes': len(decoded), 'decoded_sha256': digest(decoded),
                                  'guards_and_registers_preserved': True, 'frame': event['frame']})
                elif a == 0x0804F938:
                    script = m.u32[0x02010138]
                    row = tables[m.u8[script + 1], m.u8[script + 2]]
                    target = targets.get(row['id'], BANK_RAM + row['start'])
                    require(r[5] == BANK_RAM + row['slot'] and r[6] + m.u32[r[3]] + m.u32[r[5]] == target,
                            'Native bank-one selector differs from owned target')
                    slots.append({k: row[k] for k in ('id', 'group', 'index', 'slot')} | {'target': target})
                elif a == 0x0805160C:
                    game.snapshot().save(output / 'sale-entry')
                elif a == 0x08051614:
                    require(r[0] == BUFFER and r[1] == targets['rom.0006c424'], 'English sale formatter arguments differ')
                    payload = materialize(bytes.fromhex(sale['encoded_hex']), r[2])
                    old = materialize(SALE_ORIGINAL, r[2])
                    require(len(payload) <= len(old), 'English sale exceeds original output footprint')
                    format_before = bytes(m[BUFFER - 32:BUFFER]), bytes(m[BUFFER + len(payload):BUFFER + len(payload) + 32]), r[4:12], r[13]
                    checks.resources[BUFFER] = sale | {'encoded_hex': payload.hex()}
                    formats.append({'amount': r[2], 'output_hex': payload.hex(), 'output_bytes': len(payload),
                                    'original_output_bytes': len(old), 'frame': event['frame']})
                elif a == 0x08051618:
                    payload = bytes.fromhex(formats[-1]['output_hex'])
                    require(bytes(m[BUFFER:BUFFER + len(payload)]) == payload, 'Native English sale formatting differs')
                    require(format_before == (bytes(m[BUFFER - 32:BUFFER]), bytes(m[BUFFER + len(payload):BUFFER + len(payload) + 32]), r[4:12], r[13]),
                            'English formatter changed guards or preserved registers/SP')
                    formats[-1]['guards_and_registers_preserved'] = True
                elif a == 0x08051664:
                    commands.append({'command': bytes(m[r[0]:r[0] + 3]).decode('ascii'),
                                     'before_flags': m.u8[0x0201020E], 'frame': event['frame']})
                elif a == 0x080516AE:
                    commands[-1]['after_flags'] = m.u8[0x0201020E]
                elif a == 0x08015CE8:
                    choice_active = True
                elif a == 0x08015E28:
                    choice_active = False
                    choices.append(r[0])
                elif a == 0x080021B4:
                    require(r[1] in checks.resources or (checks.active is not None and r[1] == HERO),
                            f'Untranslated source on English home route: {r[1]:08x}')
                checks.callback(event)

            with Debugger(game, callback, max_events=100000) as trace:
                for a in checks.ADDRESSES + (0x0804D722, 0x0804D726, 0x0804F938, 0x0805160C,
                        0x08051614, 0x08051618, 0x08051664, 0x080516AE, 0x08015CE8, 0x08015E28):
                    trace.breakpoint(a)
                for step in route.get('steps', []):
                    game.press(step['key'], hold=step['hold'], wait=30)
                facing = face_home_roamer(game) if route['id'] == 'mansion-rumour' else None
                approach = position(game)
                game.capture(route['id'] + '-approach')
                game.press('A', wait=600 if home else 240)
                for page in range(100):
                    game.capture(route['id'] + f'-{page:03}')
                    if [r['id'] for r in checks.reads] == route['reads'] and checks.active is None:
                        break
                    if choice_active and route.get('choice') == 'no' and not chose_no:
                        game.press('RIGHT', wait=30)
                        chose_no = True
                        game.capture(route['id'] + '-choice-no')
                    game.press('A', wait=240)
                require([r['id'] for r in checks.reads] == route['reads'] and checks.active is None,
                        'English home conversation did not complete: ' + route['id'])
                require(choices == ([int(route['choice'] == 'yes')] if 'choice' in route else []), 'English Ed choice changed')
                game.press('A', wait=360 if home else 30)
                require([r['id'] for r in checks.reads] == route['reads'] and checks.active is None, 'Closing reopened English dialogue')
                game.capture(route['id'] + '-closed')
                if home:
                    require(list(position(game)) == route_data['village_position'], 'English village arrival differs')
                    require(len(loads) == len(formats) == 1, 'Missing home load/sale evidence')
                    require([(x['command'], x['before_flags'], x['after_flags']) for x in commands] == [('@A@', 12, 12)],
                            'Sale callback side effects differ from native Japanese route')
                    game.snapshot().save(output / 'village')
                    before = position(game)
                    game.press('DOWN', hold=8, wait=30)
                    require(position(game) != before, 'English village movement did not resume')
            results.append({'route': route['id'], 'reads': checks.reads, 'choices': choices, 'commands': commands,
                            'roaming_npc_facing': facing,
                            'bank_loads': loads, 'slots': slots, 'formatter_calls': formats,
                            'approach_position': approach, 'native_glyph_checks': checks.glyph_checks,
                            'inputs': game.inputs[input_start:]})
    getters = check_getters(rom, build, output, japanese_fixture)
    probes = check_sale_layouts(rom, sale, output)
    require(digest(save.read_bytes()) == save_hash and digest(load_base()) == digest(original), 'Original files changed')
    report = {'passed': True, 'output_rom_sha256': digest(rom), 'source_rom_sha256': digest(original),
              'source_save_sha256': save_hash, 'original_files_unchanged': True, 'emulator': version(), 'bios': BIOS,
              'fixture_state_sha256': digest(snapshot.state), 'routes_sha256': digest(ROUTES.read_bytes()),
              'routes': results, 'controlled_table_getters': getters, 'controlled_sale_layouts': probes,
              'scope': 'Natural first evening/morning, sale proceeds and village movement, plus three nearby NPCs and both Ed answers from the resulting checkpoint. All 214 bank-one getters checked in each ROM; separate controlled name/amount layout probes. Other village states, books and mansion quest remain outside this acceptance.'}
    (output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print('English home return:', len(results), 'routes,', sum(r['native_glyph_checks'] for r in results),
          'natural glyphs,', len(getters), 'controlled getters,', len(probes), 'sale layout probes')
    return report


def check_getters(rom, build, output, japanese_fixture):
    targets = {r['id']: 0x08000000 + r['rom_offset'] for r in build['dialogue']['entries']}
    reports = []
    for label, data, fixture in [('japanese', load_base(), japanese_fixture), ('english', rom, output / 'village')]:
        with Session(data, output / ('getter-' + label)) as game:
            snapshot = Snapshot.load(fixture)
            game.restore(snapshot)
            for row in table_entries(banks()[1]):
                expected = targets.get(row['id'], BANK_RAM + row['start']) if label == 'english' else BANK_RAM + row['start']
                result = call_thumb(game, 0x08050270, row['group'], row['index'])
                require(result['r0'] == expected, 'Native bank-one getter differs')
                reports.append({'rom': label, 'id': row['id'], 'group': row['group'], 'index': row['index'],
                                'expected': expected, 'result': result, 'fixture_state_sha256': digest(snapshot.state)})
    return reports


def check_sale_layouts(rom, sale, output):
    reports = []
    fixture = Snapshot.load(output / 'sale-entry')
    template = bytes.fromhex(sale['encoded_hex'])
    with Session(rom, output / 'sale-layouts') as game:
        for label, name in player_layout_cases():
            for amount in (0, 1, 100, 0x7FFFFFFF):
                game.restore(fixture)
                input_start = len(game.inputs) - 1
                before_name = bytes(game.core.memory[HERO - 16:HERO]), bytes(game.core.memory[HERO + 16:HERO + 32])
                for i, value in enumerate(name.ljust(16, b'\0')):
                    game.core.memory.u8[HERO + i] = value
                game.core.cpu.gprs[7] = amount  # The verified formatter argument move at 08051612.
                payload = materialize(template, amount)
                checks = TextChecks(game, {BUFFER: sale | {'encoded_hex': payload.hex()}})
                before = None
                formatted = False
                def callback(event):
                    nonlocal before, formatted
                    r, a, m = event['registers'], event['address'], game.core.memory
                    if a == 0x08051614:
                        require(r[0] == BUFFER and r[1] == 0x08000000 + sale['rom_offset'] and r[2] == amount,
                                'Controlled sale argument differs')
                        before = bytes(m[BUFFER - 32:BUFFER]), bytes(m[BUFFER + len(payload):BUFFER + len(payload) + 32]), r[4:12], r[13]
                    elif a == 0x08051618:
                        require(bytes(m[BUFFER:BUFFER + len(payload)]) == payload, 'Controlled native sale format differs')
                        require(before == (bytes(m[BUFFER - 32:BUFFER]), bytes(m[BUFFER + len(payload):BUFFER + len(payload) + 32]), r[4:12], r[13]),
                                'Controlled sale formatter changed guards or registers/SP')
                        formatted = True
                    checks.callback(event)
                with Debugger(game, callback, max_events=10000) as trace:
                    for a in checks.ADDRESSES + (0x08051614, 0x08051618):
                        trace.breakpoint(a)
                    game.frames(240)
                    require(formatted and checks.active is None and checks.completed(sale['id']), 'Sale layout did not finish')
                    game.capture(label + '-' + str(amount))
                require(before_name == (bytes(game.core.memory[HERO - 16:HERO]), bytes(game.core.memory[HERO + 16:HERO + 32])),
                        'Controlled sale changed adjacent name fields')
                reports.append({'case': label, 'controlled_name_hex': name.hex(), 'controlled_amount': amount,
                                'reads': checks.reads, 'native_glyph_checks': checks.glyph_checks,
                                'fixture_state_sha256': digest(fixture.state), 'inputs': game.inputs[input_start:],
                                'formatter_and_name_guards_preserved': True,
                                'scope': 'Controlled formatter/display continuation; no assertion that this amount was earned in gameplay.'})
    return reports


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fixture', type=Path, default=FIXTURE)
    parser.add_argument('--output', type=Path, default=OUTPUT)
    parser.add_argument('--japanese-fixture', type=Path, default=JAPANESE)
    args = parser.parse_args()
    run(args.fixture.resolve(), args.output.resolve(), args.japanese_fixture.resolve())
