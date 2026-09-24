"""Observe the first castle destination menu, cancellation and native return home."""

import argparse
import json
from pathlib import Path

import mgba.log

from tools.emulator import Debugger, Session, Snapshot
from tools.opening_text import BANK_RAM, banks
from tools.rom import ROOT, digest, load_base, require
from tools.text_codec import readable, tokenize
from tools.town_playtest import position

OUTPUT = ROOT / 'build/destination-menu/research'
FIXTURE = ROOT / 'build/castle-arrival/research/castle'


def run(fixture=FIXTURE, output=OUTPUT):
    mgba.log.silence()
    original, snapshot = load_base(), Snapshot.load(fixture)
    bank_map = {0x08000000 + b['rom_offset']: b for b in banks()}
    entries, results = {}, []
    with Session(original, output) as game:
        for route in ('cancel', 'home'):
            game.restore(snapshot)
            input_start = len(game.inputs) - 1
            reads, returns, loads, pointers = [], [], [], []
            active_bank = None
            def callback(event):
                nonlocal active_bank
                r, address = event['registers'], event['address']
                if event['kind'] == 'watchpoint':
                    pointers.append({'address': address, 'pc': r[15], 'frame': event['frame']})
                    return
                if address == 0x0804CC40:
                    returns.append(r[0])
                    return
                if address == 0x0804D722:
                    active_bank = bank_map[r[0]]
                    return
                if address == 0x0804D726:
                    require(bytes(game.core.memory[BANK_RAM:BANK_RAM + len(active_bank['data'])]) ==
                            active_bank['data'], 'Native home bank differs')
                    loads.append({'bank': active_bank['id'], 'frame': event['frame'], 'all_decoded_bytes_match': True})
                    return
                pointer = r[1]
                if 0x08000000 <= pointer < 0x08000000 + len(original):
                    data, start = original, pointer - 0x08000000
                    ident, source = f'rom.{start:08x}', {'kind': 'rom'}
                elif active_bank and BANK_RAM <= pointer < BANK_RAM + len(active_bank['data']):
                    data, start = active_bank['data'], pointer - BANK_RAM
                    ident = f"{active_bank['id']}.{start:04x}"
                    source = {'kind': 'compressed-bank', 'bank': active_bank['id'],
                              'compressed_rom_offset': active_bank['rom_offset']}
                else:
                    return  # Existing nested player-name RAM record, not a new source.
                tokens, end = tokenize(data, start)
                raw = data[start:end]
                require(bytes(game.core.memory[pointer:pointer + len(raw)]) == raw, 'Native destination source differs')
                observation = {'route': 'first-castle-destination/' + route, 'frame': event['frame'],
                               'reader': address, 'source': pointer, 'window': r[0],
                               'window_hex': bytes(game.core.memory[r[0]:r[0] + 24]).hex()}
                row = {'id': ident, 'source': source | {'offset': start, 'end_exclusive': end},
                       'raw_hex': raw.hex(), 'source_sha256': digest(raw), 'tokens': tokens,
                       'japanese': readable(tokens), 'evidence': [observation]}
                if ident in entries:
                    entries[ident]['evidence'].append(observation)
                else:
                    entries[ident] = row
                reads.append(ident)
            with Debugger(game, callback, max_events=1000) as trace:
                for address in (0x080021B4, 0x0804CC40, 0x0804D722, 0x0804D726):
                    trace.breakpoint(address)
                for address in (0x0814D718, 0x0814BEA0):
                    trace.watchpoint(address)
                game.press('DOWN', hold=140, wait=240)
                game.capture(route + '-menu')
                require(reads == ['rom.0006c524', 'rom.0006c14c'], 'Unexpected first destination menu')
                game.snapshot().save(output / (route + '-menu'))
                game.press('B' if route == 'cancel' else 'A', wait=600)
                game.capture(route + '-result')
                game.snapshot().save(output / (route + '-result'))
                if route == 'cancel':
                    before = position(game)
                    game.press('UP', hold=16, wait=60)
                    require(position(game)[1] < before[1], 'Cancel did not return town movement')
            results.append({'route': route, 'reads': reads, 'returns': returns, 'bank_loads': loads,
                            'pointer_reads': pointers, 'inputs': game.inputs[input_start:]})
    report = {'passed': True, 'source_rom_sha256': digest(original), 'fixture_state_sha256': digest(snapshot.state),
              'entries': list(entries.values()), 'routes': results,
              'scope': 'Normal first-castle exit, B cancellation with resumed movement, and Home selection with natural bank-one load and first home dialogue. The same naturally reached castle fixture is restored between routes.'}
    (output / 'trace.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print('Japanese destination routes:', [(r['route'], r['returns'], r['reads']) for r in results])
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fixture', type=Path, default=FIXTURE)
    parser.add_argument('--output', type=Path, default=OUTPUT)
    args = parser.parse_args()
    run(args.fixture.resolve(), args.output.resolve())
