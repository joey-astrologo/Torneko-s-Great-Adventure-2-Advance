"""Compare native house/stair save, soft reset and resume in both ROMs.

Uses retained ordinary-input routes and disposable battery copies. No state,
RAM, ROM, register or gameplay overrides; this is mGBA built-in-BIOS evidence,
not an Analogue Pocket or external-BIOS compatibility test.
"""

import argparse
import json
from pathlib import Path

import mgba.log

from tools.emulator import BIOS, Debugger, Session, version
from tools.name_entry import HERO, STORED
from tools.rom import ROOT, default_rom, digest, load_base, require
from tools.town_playtest import position as town_position
from tools.verify_name_entry import cold_load, save_fields


ADDRESSES = (0x08000354, 0x08015374, 0x08015354, 0x0800140C,
             0x0805B4AC, 0x0805B4BC, 0x0805B4BE)
UNCHANGED = ((0x140C, 0x1440), (0x54E6, 0x5520), (0x15348, 0x15434),
             (0x1FB90, 0x1FBEC), (0x5B4AC, 0x5B4C8))


def replay(game, inputs):
    for step in inputs:
        if 'key' in step:
            game.press(step['key'], hold=step['hold'], wait=step['released'])
        else:
            require('frames' in step, 'Route contains a non-input operation')
            game.frames(step['frames'])


def load_house(game, expected):
    restored = []

    def callback(event):
        fields = save_fields(game.core.memory, event['registers'][0])
        require(fields == expected, 'House main save fields changed')
        restored.append(event | {'fields': fields})

    with Debugger(game, callback) as debugger:
        debugger.breakpoint(0x08014FF2)
        game.press('A', wait=300)
    require(len(restored) == 1, 'House main record was not restored once')
    require(town_position(game) == (288, 224), 'House reload position differs')
    require(bytes(game.core.memory[HERO:HERO + 16]).hex() == expected['player_body']
            and bytes(game.core.memory[STORED:STORED + 16]).hex()
            == expected['indexed_body'], 'House name records changed')
    game.press('DOWN', hold=8, wait=30)
    require(town_position(game) == (288, 256), 'House controls did not resume')
    game.capture('resumed-movement')
    return {'restores': restored, 'position_after_movement': town_position(game)}


def run(output, english_path):
    mgba.log.silence()
    original, english = load_base(), english_path.read_bytes()
    source_save = default_rom().with_suffix('.sav')
    source_save_hash = digest(source_save.read_bytes())
    protected = {english_path: digest(english), source_save: source_save_hash}
    output.mkdir(parents=True, exist_ok=True)
    ranges = []
    for start, end in UNCHANGED:
        require(english[start:end] == original[start:end], 'Quit code changed')
        ranges.append({'rom_start': start, 'rom_end_exclusive': end,
                       'original_hex': original[start:end].hex(), 'identical': True})
    name_report_path = ROOT / 'build/english/name-entry-validation/report.json'
    name_report = json.loads(name_report_path.read_text())
    protected[name_report_path] = digest(name_report_path.read_bytes())
    cases = []
    for label, rom in [('japanese', original), ('english', english)]:
        for route in ('house', 'stairs'):
            print('Save/quit:', label, route, flush=True)
            case_dir = output / (label + '-' + route)
            initial_save = None
            provenance = {}
            if route == 'house':
                folder = ROOT / 'build/english/books-validation'
                report_path = folder / 'report.json'
                if label == 'japanese':
                    folder /= 'japanese'
                    report_path = folder / 'trace.json'
                save_path = folder / 'save-quit.sav'
                initial_save = save_path.read_bytes()
                receipt = json.loads(report_path.read_text())
                prior = next(r for r in receipt['routes'] if r['route'] == 'save-quit')
                require(digest(initial_save) == prior['after_battery_sha256'],
                        'Historical house battery differs from its receipt')
                for p in (save_path, report_path):
                    protected[p] = digest(p.read_bytes())
                provenance = {'battery_path': str(save_path.relative_to(ROOT)),
                              'battery_sha256': digest(initial_save),
                              'receipt_sha256': digest(report_path.read_bytes())}
            else:
                key = 'japanese_native_save' if label == 'japanese' else 'english_save'
                schedule = name_report[key]['normal_inputs']
                provenance = {'schedule_receipt': str(name_report_path.relative_to(ROOT)),
                              'receipt_sha256': protected[name_report_path], 'route_key': key,
                              'historical_rom_sha256': name_report[
                                  'source_rom_sha256' if label == 'japanese' else 'output_rom_sha256']}
            events, expected = [], None
            with Session(rom, case_dir, initial_save=initial_save) as game:
                def callback(event):
                    nonlocal expected
                    if event['address'] == 0x08015354:
                        expected = save_fields(game.core.memory, event['registers'][0])
                        event = event | {'serialized_fields': expected}
                    if event['address'] in (0x0805B4BC, 0x0805B4BE):
                        event = event | {'reset_flag': game.core.memory.u8[0x03007FFA],
                                         'ime': game.core.memory.u16[0x04000208]}
                        require(event['reset_flag'] == event['ime'] == 0,
                                'Reset flag/interrupt state differs')
                        require(event['registers'][13] == 0x03007F00,
                                'Reset stack differs')
                    events.append(event)

                with Debugger(game, callback, max_events=1000) as debugger:
                    for address in ADDRESSES:
                        debugger.breakpoint(address)
                    if route == 'house':
                        game.frames(600)
                        game.press('START', wait=180)
                        game.press('A', wait=300)
                        require(town_position(game) == (288, 224), 'House fixture differs')
                        game.press('UP', wait=30)
                        game.press('A', wait=240)
                        game.capture('book-menu')
                        for _ in range(3):
                            game.press('DOWN', wait=30)
                        game.press('A', wait=240)
                        game.capture('overwrite')
                        game.press('A', wait=240)
                    else:
                        replay(game, schedule)
                    game.capture('save-complete')
                    require(expected is not None, 'Native serializer was not reached')
                    battery = game.snapshot().battery
                    game.snapshot().save(case_dir / 'before-quit')
                    game.press('A', wait=900)
                    game.capture('after-soft-reset')
                    game.snapshot().save(case_dir / 'after-soft-reset')
                    require(game.snapshot().battery == battery, 'Quit changed completed save')
                addresses = [e['address'] for e in events]
                require(addresses == list(ADDRESSES) + [ADDRESSES[0]],
                        'Save/reset/startup sequence differs: ' + repr(addresses))
                reset = next(e for e in events if e['address'] == 0x0800140C)
                require(reset['registers'][14] == (0x0801FBE7 if route == 'house' else 0x0800551F),
                        'Unexpected quit caller')
                require(events[1]['registers'][1] == 2 and events[4]['registers'][0] == 255,
                        'Save mode/reset mask differs')
                game.press('START', wait=180)
                game.capture('working-continue-menu')
                require(bytes(game.core.memory[STORED:STORED + 16]).hex()
                        == expected['indexed_header'], 'Reset did not reach save preview')
                warm_house = load_house(game, expected) if route == 'house' else None
                inputs = game.inputs
            require(game.disk_save == battery, 'Native disk save differs')
            (case_dir / 'native-save.sav').write_bytes(battery)
            if route == 'house':
                with Session(rom, case_dir / 'cold-load', initial_save=battery) as cold:
                    cold.frames(600)
                    cold.press('START', wait=180)
                    resumed = load_house(cold, expected) | {'inputs': cold.inputs}
            else:
                resumed = cold_load(rom, battery, expected, case_dir / 'cold-load')
            cases.append({'rom': label, 'route': route, 'rom_sha256': digest(rom),
                          'provenance': provenance, 'overrides': [], 'events': events,
                          'inputs': inputs, 'save_sha256': digest(battery),
                          'quit_preserved_battery': True, 'native_disk_save_exact': True,
                          'warm_house_resume': warm_house, 'cold_resume': resumed})
    require(load_base() == original and all(digest(p.read_bytes()) == h
            for p, h in protected.items()), 'Source ROM/save/fixtures changed')
    report = {'passed': True, 'source_rom_sha256': digest(original),
              'output_rom_sha256': digest(english), 'source_save_sha256': source_save_hash,
              'emulator': version(), 'bios': BIOS, 'unchanged_rom_ranges': ranges,
              'original_files_and_fixtures_unchanged': True, 'cases': cases,
              'scope': 'Four ordinary-input house/stair routes in original and current English ROMs. '
                       'Native save, BIOS RAM reset, soft reset, cartridge restart and responsive '
                       'Continue menu; house warm resume and all four cold resumes with movement. '
                       'No external BIOS, Pocket core, flashcart, user save or audio diagnosis.'}
    (output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print('Save/quit: all four reset and cold-resume routes passed', flush=True)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'build/save-quit/validation')
    parser.add_argument('--rom', type=Path, default=ROOT / 'build/torneko-2-english.gba')
    args = parser.parse_args()
    run(args.output.resolve(), args.rom.resolve())
