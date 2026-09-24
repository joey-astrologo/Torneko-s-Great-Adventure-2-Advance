"""Disposable mansion exploration; record ordinary inputs and native text sources."""

import argparse
import json
from pathlib import Path

import mgba.log

from tools.emulator import Debugger, Session, Snapshot
from tools.name_entry_playtest import ACTORS, position
from tools.mansion_playtest import walk_to_stairs
from tools.opening_text import BANK_RAM, banks
from tools.rom import ROOT, digest, load_base
from tools.text_codec import readable, tokenize
from tools.town_text import RAM as COMMON_RAM, resource as town_resource


class Discovery:
    ADDRESSES = (0x080021B4, 0x0801588C)

    def __init__(self, game, verbose=True):
        self.game = game
        self.original = load_base()
        self.banks = list(banks())
        self.common = town_resource()
        self.entries, self.unknown = [], []
        self.verbose = verbose

    def callback(self, event):
        r = event['registers']
        pointer = r[0] if event['address'] == 0x0801588C else r[1]
        memory = self.game.core.memory
        candidates = []
        if 0x08000000 <= pointer < 0x08800000:
            candidates.append(('rom', self.original, pointer - 0x08000000, {'kind': 'rom'}))
        for bank in self.banks + [self.common]:
            base = COMMON_RAM if bank['id'] == 'town-common' else BANK_RAM
            if base <= pointer < base + len(bank['data']):
                candidates.append((bank['id'], bank['data'], pointer - base,
                    {'kind': 'compressed-bank', 'bank': bank['id'], 'compressed_rom_offset': bank['rom_offset']}))
        for ident, data, start, source in candidates:
            try:
                tokens, end = tokenize(data, start, min(len(data), start + 4096))
            except ValueError:
                continue
            raw = data[start:end]
            if bytes(memory[pointer:pointer + len(raw)]) != raw:
                continue
            row = {'id': f'rom.{start:08x}' if ident == 'rom' else f'{ident}.{start:04x}',
                   'source': source | {'offset': start, 'end_exclusive': end},
                   'raw_hex': raw.hex(), 'source_sha256': digest(raw), 'tokens': tokens,
                   'japanese': readable(tokens), 'evidence': [{'frame': event['frame'],
                   'reader': event['address'], 'source': pointer, 'return': r[14],
                   'route': 'mansion-ordinary-input-research', 'window': r[0],
                   'window_hex': bytes(memory[r[0]:r[0]+24]).hex()}]}
            if event['address'] == 0x0801588C:
                row['evidence'][0].pop('window')
                row['evidence'][0].pop('window_hex')
                row['evidence'][0]['consumer'] = 'dungeon message queue'
            self.entries.append(row)
            if self.verbose:
                print(row['id'], row['japanese'], flush=True)
            return row
        raw = bytes(memory[pointer:pointer+512])
        try:
            tokens, end = tokenize(raw)
            text = readable(tokens)
        except ValueError:
            text, end = '', 128
        self.unknown.append({'pointer': pointer, 'frame': event['frame'], 'return': r[14],
                             'raw_hex': raw[:end].hex(), 'text': text})
        if self.verbose:
            print('unowned', hex(pointer), text, flush=True)
        return {'id': f'generated.{pointer:08x}', 'japanese': text}


def status(game):
    m = game.core.memory
    actor = m.u32[ACTORS]
    from tools.town_playtest import position as town_position
    return {'town_position':town_position(game), 'dungeon': m.u32[0x02003B6C], 'floor': m.u16[0x02005674],
            'position': position(game), 'hp': m.u16[actor+0x84], 'max_hp': m.u16[actor+0x86]}


def run(fixture, output, actions, stairs, goal=None):
    mgba.log.silence()
    original = load_base()
    with Session(original, output) as game:
        game.restore(Snapshot.load(fixture))
        observer = Discovery(game)
        walks = []
        error = None
        with Debugger(game, observer.callback, max_events=100000) as debug:
            for address in observer.ADDRESSES:
                debug.breakpoint(address)
            try:
                for i, action in enumerate(actions):
                    if isinstance(action, str):
                        game.press(action, wait=240)
                    else:
                        game.press(action[0], hold=action[1], wait=action[2])
                    game.capture(f'action-{i:03}')
                if goal:
                    walks.append(walk_to_stairs(game, tuple(goal)))
                for i in range(stairs):
                    print('walking', status(game), flush=True)
                    game.snapshot().save(output / f'floor-{status(game)["floor"]}-start')
                    walks.append(walk_to_stairs(game))
                    game.capture(f'stairs-{i}')
                    game.snapshot().save(output / f'stairs-{i}')
                    if i + 1 < stairs:
                        game.press('A', wait=600)
                        game.capture(f'arrival-{i}')
            except Exception as exc:
                error = str(exc) + (f': {exc.__cause__}' if exc.__cause__ else '')
                print('ERROR', error, flush=True)
        game.capture('end')
        game.snapshot().save(output / 'end')
        report = {'passed': error is None, 'error': error, 'source_rom_sha256': digest(original),
                  'fixture': str(fixture), 'inputs': game.inputs, 'walks': walks,
                  'entries': list({r['id']: r for r in observer.entries}.values()),
                  'reads': observer.entries, 'unknown': observer.unknown, 'status': status(game)}
        (output / 'trace.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
        print(report['status'], flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fixture', type=Path, default=ROOT/'build/english/books-validation/japanese/mansion-floor-one')
    parser.add_argument('--output', type=Path, default=ROOT/'build/mansion/research')
    parser.add_argument('--actions', default='[]')
    parser.add_argument('--stairs', type=int, default=0)
    parser.add_argument('--goal', nargs=2, type=int)
    args = parser.parse_args()
    run(args.fixture, args.output, json.loads(args.actions), args.stairs, args.goal)
