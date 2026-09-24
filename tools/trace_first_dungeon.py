"""Trace native Japanese floor tutorials/stairs, optionally continuing to the King."""

import argparse
import json
from pathlib import Path

import mgba.log

from tools.emulator import Debugger, Session
from tools.name_entry_playtest import walk_to_stairs
from tools.opening_text import BANK_RAM, banks
from tools.rom import ROOT, digest, load_base, require
from tools.text_codec import tokenize, readable

OUTPUT = ROOT / 'build/first-dungeon/research'
SAVE = ROOT / 'build/english/name-entry-validation/japanese-save/native-save.sav'


def run(save=SAVE, output=OUTPUT, castle=False):
    mgba.log.silence()
    original, battery = load_base(), save.read_bytes()
    reads, calls, pointers = [], [], []
    fields = (0x141318, 0x14131C, 0x141320, 0x1412F8, 0x1413B4, 0x14723C, 0x147240, 0x178C0)
    known_banks = {0x08000000 + b['rom_offset']: b for b in banks()}
    active_bank = pending_bank = None
    bank_loads, castle_walk = [], []
    with Session(original, output, initial_save=battery) as game:
        def callback(event):
            nonlocal active_bank, pending_bank
            r = event['registers']
            if event['address'] == 0x0804D722:
                pending_bank = known_banks[r[0]]
                return
            if event['address'] == 0x0804D726:
                active_bank = pending_bank
                require(bytes(game.core.memory[BANK_RAM:BANK_RAM + len(active_bank['data'])]) == active_bank['data'], 'Natural bank load differs')
                bank_loads.append({'frame': event['frame'], 'bank': active_bank['id']})
                return
            if event['kind'] == 'watchpoint':
                pointers.append({'field': event['address'], 'pc': r[15], 'frame': event['frame']})
                return
            if event['address'] == 0x0801B620:
                calls.append({'frame': event['frame'], 'help_index': r[1]})
                return
            pointer = r[1]
            if 0x08000000 <= pointer < 0x08800000:
                start = pointer - 0x08000000
                tokens, end = tokenize(original, start, min(len(original), start + 4096))
                ident, raw = f'rom.{start:08x}', original[start:end]
                source = {'kind': 'rom', 'offset': start, 'end_exclusive': end}
            elif active_bank and BANK_RAM <= pointer < BANK_RAM + len(active_bank['data']):
                start = pointer - BANK_RAM
                tokens, end = tokenize(active_bank['data'], start)
                ident, raw = f"{active_bank['id']}.{start:04x}", active_bank['data'][start:end]
                source = {'kind': 'compressed-bank', 'bank': active_bank['id'], 'offset': start,
                          'end_exclusive': end, 'compressed_rom_offset': active_bank['rom_offset']}
                require(bytes(game.core.memory[pointer:pointer + len(raw)]) == raw, 'Native event string differs')
            else:
                return
            reads.append({'id': ident, 'source': source,
                              'raw_hex': raw.hex(), 'source_sha256': digest(raw),
                              'tokens': tokens, 'japanese': readable(tokens),
                              'evidence': [{'frame': event['frame'], 'reader': event['address'], 'source': pointer,
                                            'window': r[0], 'window_hex': bytes(game.core.memory[r[0]:r[0] + 24]).hex(),
                                            'route': 'first-dungeon-japanese-save-resume'}]})
        with Debugger(game, callback, max_events=10000) as trace:
            trace.breakpoint(0x080021B4)
            trace.breakpoint(0x0801B620)
            trace.breakpoint(0x0804D722)
            trace.breakpoint(0x0804D726)
            for field in fields:
                trace.watchpoint(0x08000000 + field)
            game.frames(600)
            game.press('START', wait=180)
            for _ in range(3):
                game.press('A', wait=600)
            game.capture('floor-two-help')
            game.press('A', wait=120)
            game.press('A', wait=120)
            walk = walk_to_stairs(game)
            game.capture('stairs-menu')
            game.press('A', wait=600)
            game.capture('floor-three-help')
            game.press('A', wait=120)
            game.press('A', wait=120)
            game.snapshot().save(output / 'floor-three')
            require(any(r['id'] == 'rom.0006b080' for r in reads) and
                    any(r['id'] == 'rom.0006b03c' for r in reads), 'Second/third-floor help not reached')
            if castle:
                castle_walk = walk_to_stairs(game)
                game.capture('floor-three-stairs')
                game.press('A', wait=600)
                for i in range(36):
                    game.capture(f'castle-{i:02}')
                    game.press('A', wait=240)
                game.snapshot().save(output / 'castle')
        inputs = game.inputs
    report = {'passed': True, 'source_rom_sha256': digest(original), 'initial_save_sha256': digest(battery),
              'initial_save': str(save), 'reads': reads, 'help_calls': calls, 'pointer_reads': pointers,
              'inputs': inputs, 'walk': walk, 'castle_walk': castle_walk,
              'bank_loads': bank_loads, 'castle_extension': castle,
              'scope': 'Native Japanese save resume on floor two, ordinary movement to stairs, descent to floor three.' +
                       (' Continue through floor three to the first royal audience.' if castle else '') + ' No state overrides.'}
    (output / 'trace.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print('passed', len(reads), 'reads; help indices', sorted({row['help_index'] for row in calls}),
          '; castle extension:', castle)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--save', type=Path, default=SAVE)
    parser.add_argument('--output', type=Path, default=OUTPUT)
    parser.add_argument('--castle', action='store_true')
    args = parser.parse_args()
    run(args.save.resolve(), args.output.resolve(), args.castle)
