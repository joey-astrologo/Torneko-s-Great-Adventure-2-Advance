"""Verify English travel labels, long names, native cursor, Cancel and Home."""

import argparse
import json
from pathlib import Path

import mgba.log

from tools.build_english import build_rom
from tools.dialogue_checks import TextChecks, player_layout_cases
from tools.emulator import Debugger, Session, Snapshot
from tools.name_entry import HERO
from tools.lz77 import decompress
from tools.opening_text import BANK_RAM, banks
from tools.rom import ROOT, default_rom, digest, load_base, require
from tools.text_codec import tokenize
from tools.town_playtest import position

OUTPUT = ROOT / 'build/english/destination-validation'
FIXTURE = ROOT / 'build/english/castle-validation/audience-complete'


def run(fixture=FIXTURE, output=OUTPUT):
    mgba.log.silence()
    rom, build = build_rom()
    original, source_save = load_base(), default_rom().with_suffix('.sav')
    save_hash = digest(source_save.read_bytes())
    rows = {0x08000000 + r['rom_offset']: r for r in build['dialogue']['entries'] if r['batch'] == 'destination-menu'}
    home_bank = banks()[1]
    _, end = tokenize(home_bank['data'], 0x400)
    home_text = home_bank['data'][0x400:end]
    home_pointer = BANK_RAM + 0x400
    bank_pointer, bank_data = 0x08000000 + home_bank['rom_offset'], home_bank['data']
    inserted_bank = next((b for b in build['dialogue']['banks'] if b['id'] == home_bank['id']), None)
    if inserted_bank:
        bank_pointer = 0x08000000 + inserted_bank['bank_rom_offset']
        bank_data, _ = decompress(rom, inserted_bank['bank_rom_offset'])
        home_row = next(r for r in build['dialogue']['entries'] if r['id'] == 'event-bank-1.0400')
        home_pointer, home_text = 0x08000000 + home_row['rom_offset'], bytes.fromhex(home_row['encoded_hex'])
    results = []
    with Session(rom, output) as game:
        fixture_state = Snapshot.load(fixture)
        for label, controlled_name, action in [('native-cancel', None, 'B'), ('native-home', None, 'A')] + [
                (label, name, 'B') for label, name in player_layout_cases()]:
            game.restore(fixture_state if controlled_name is None else Snapshot.load(output / 'menu-entry'))
            input_start = len(game.inputs) - 1
            before_name = bytes(game.core.memory[HERO - 16:HERO])
            after_name = bytes(game.core.memory[HERO + 16:HERO + 32])
            if controlled_name is not None:
                for i, value in enumerate(controlled_name.ljust(16, b'\0')):
                    game.core.memory.u8[HERO + i] = value
            checks, returns, cursor_calls, home_loads = TextChecks(game, rows), [], [], []
            preserved = None
            home_seen = False
            pending_bank = None
            def callback(event):
                nonlocal preserved, home_seen, pending_bank
                r, address = event['registers'], event['address']
                if address == 0x0804CB10:
                    preserved = r[4:12], r[13]
                    if controlled_name is None:
                        game.snapshot().save(output / 'menu-entry')
                    return
                if address == 0x0804CC4E:
                    if preserved is not None:
                        require(preserved == (r[4:12], r[13]), 'Destination function changed preserved registers/SP')
                    returns.append(r[0])
                    return
                if address == 0x0804CE0C:
                    require(r[1] == 80 and r[2] == 24, 'Destination cursor differs from moved first row')
                    cursor_calls.append({'x': r[1], 'y': r[2], 'frame': event['frame']})
                    return
                if address == 0x0804D722:
                    pending_bank = r[0]
                    return
                if address == 0x0804D726:
                    require(pending_bank == bank_pointer and
                            bytes(game.core.memory[BANK_RAM:BANK_RAM + len(bank_data)]) == bank_data,
                            'Home did not load the expected bank one')
                    home_loads.append({'bank': home_bank['id'], 'all_decoded_bytes_match': True, 'frame': event['frame']})
                    return
                if address == 0x080021B4 and r[1] == home_pointer:
                    require(bytes(game.core.memory[r[1]:r[1] + len(home_text)]) == home_text, 'Home source differs')
                    home_seen = True
                checks.callback(event)
            with Debugger(game, callback, max_events=10000) as trace:
                for address in checks.ADDRESSES + (0x0804CB10, 0x0804CC4E, 0x0804CE0C, 0x0804D722, 0x0804D726):
                    trace.breakpoint(address)
                if controlled_name is None:
                    game.press('DOWN', hold=140, wait=240)
                else:
                    # The snapshot is at entry before push; restored execution
                    # continues past that breakpoint. Capture preserved values
                    # from the still-unmodified register/stack context here.
                    preserved = ([int(game.core.cpu.gprs[i]) & 0xFFFFFFFF for i in range(4, 12)],
                                 int(game.core.cpu.gprs[13]) & 0xFFFFFFFF)
                    game.frames(240)
                require([r['id'] for r in checks.reads] == ['rom.0006c524', 'rom.0006c14c'] and
                        checks.active is None and cursor_calls, 'English destination labels not completed')
                game.frames(16)  # Capture the next blink phase as well as native cursor coordinates.
                game.capture(label + '-menu')
                if label == 'native-home':
                    game.snapshot().save(output / 'home-menu')
                game.press(action, wait=600)
                require(returns == ([255] if action == 'B' else [1]), 'English destination outcome differs')
                if action == 'A':
                    require(home_seen and len(home_loads) == 1, 'Native Home continuation not reached')
                else:
                    before = position(game)
                    game.press('UP', hold=16, wait=60)
                    require(position(game)[1] < before[1], 'Cancel did not resume town movement')
                game.capture(label + '-result')
            if controlled_name is not None:
                require(bytes(game.core.memory[HERO - 16:HERO]) == before_name and
                        bytes(game.core.memory[HERO + 16:HERO + 32]) == after_name, 'Name probe changed adjacent fields')
            results.append({'case': label, 'controlled_name_hex': controlled_name.hex() if controlled_name else None,
                            'passed': True, 'reads': checks.reads, 'native_glyph_checks': checks.glyph_checks,
                            'cursor_calls': cursor_calls, 'returns': returns, 'callee_saved_and_sp_preserved': True,
                            'home_bank_loads': home_loads, 'home_dialogue_seen': home_seen,
                            'inputs': game.inputs[input_start:]})
    require(digest(source_save.read_bytes()) == save_hash, 'Original save changed')
    report = {'passed': True, 'output_rom_sha256': digest(rom), 'source_rom_sha256': digest(original),
              'source_save_sha256': save_hash, 'original_files_unchanged': True, 'cases': results,
              'scope': 'Native first-castle travel menu: Cancel/movement and Home/bank-one dialogue entry; three separate controlled name-record layout probes. Full home dialogue has its own acceptance report; later destination entries remain separate.'}
    (output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print('English destination menu:', len(results), 'cases; Cancel/Home and native cursor passed')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fixture', type=Path, default=FIXTURE)
    parser.add_argument('--output', type=Path, default=OUTPUT)
    args = parser.parse_args()
    run(args.fixture.resolve(), args.output.resolve())
