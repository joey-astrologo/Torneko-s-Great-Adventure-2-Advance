"""Observe nearby castle conversations from a naturally reached Japanese fixture."""

import argparse
import json
from pathlib import Path

import mgba.log

from tools.emulator import Debugger, Session, Snapshot
from tools.opening_text import BANK_RAM, banks
from tools.rom import ROOT, digest, load_base, require
from tools.text_codec import readable, tokenize
from tools.town_playtest import position

OUTPUT = ROOT / 'build/castle-conversations/research'
FIXTURE = ROOT / 'build/castle-arrival/research/castle'
ROUTES = ROOT / 'config/routes/castle-conversations.json'


def run(fixture=FIXTURE, output=OUTPUT):
    mgba.log.silence()
    original, bank = load_base(), banks()[0]
    routes = json.loads(ROUTES.read_text())
    results, entries = [], {}
    snapshot = Snapshot.load(fixture)
    with Session(original, output) as game:
        for route in routes['routes']:
            game.restore(snapshot)
            input_start = len(game.inputs) - 1
            require(list(position(game)) == routes['start_position'], 'Castle route start differs')
            reads, completed, depth = [], [], 0
            choices, choice_seen, chose_no = [], False, False
            active = None
            def callback(event):
                nonlocal active, depth, choice_seen
                r = event['registers']
                if event['address'] == 0x08015CE8:
                    choice_seen = True
                    return
                if event['address'] == 0x08015E28:
                    choices.append(r[0])
                    return
                if event['address'] == 0x080021B4:
                    if active is not None:
                        depth += 1
                        return
                    pointer = r[1]
                    if BANK_RAM <= pointer < BANK_RAM + len(bank['data']):
                        data, start = bank['data'], pointer - BANK_RAM
                        ident = f"{bank['id']}.{start:04x}"
                        source = {'kind': 'compressed-bank', 'bank': bank['id'],
                                  'compressed_rom_offset': bank['rom_offset']}
                    else:
                        require(0x08000000 <= pointer < 0x08000000 + len(original),
                                f'Unexpected castle source {pointer:08x}')
                        data, start = original, pointer - 0x08000000
                        ident, source = f'rom.{start:08x}', {'kind': 'rom'}
                    tokens, end = tokenize(data, start)
                    raw = data[start:end]
                    require(bytes(game.core.memory[pointer:pointer + len(raw)]) == raw, 'Native castle source differs')
                    active = {'id': ident, 'source': source | {'offset': start, 'end_exclusive': end},
                              'raw_hex': raw.hex(), 'source_sha256': digest(raw), 'tokens': tokens,
                              'japanese': readable(tokens), 'evidence': [{'route': routes['id'] + '/' + route['id'],
                              'frame': event['frame'], 'reader': event['address'], 'source': pointer,
                              'window': r[0], 'window_hex': bytes(game.core.memory[r[0]:r[0] + 24]).hex()}]}
                    reads.append(active)
                elif active is not None:
                    if depth:
                        depth -= 1
                    else:
                        completed.append(active['id'])
                        active = None
            with Debugger(game, callback, max_events=1000) as trace:
                trace.breakpoint(0x080021B4)
                trace.breakpoint(0x08002284)
                trace.breakpoint(0x08015CE8)
                trace.breakpoint(0x08015E28)
                for step in route['steps']:
                    game.press(step['key'], hold=step['hold'], wait=30)
                approach = position(game)
                game.capture(route['id'] + '-approach')
                game.press('A', wait=240)
                for page in range(32):
                    game.capture(route['id'] + f'-{page:02}')
                    before_reads = len(reads)
                    if route.get('choice') == 'no' and choice_seen and not chose_no:
                        game.press('RIGHT', wait=30)
                        chose_no = True
                        game.capture(route['id'] + '-choice-no')
                    game.press('A', wait=240)
                    if completed and active is None and len(reads) == before_reads:
                        break
                require(completed and active is None, 'Castle conversation did not complete: ' + route['id'])
                require(choices == ([int(route['choice'] == 'yes')] if 'choice' in route else []),
                        'Castle choice result differs')
                game.capture(route['id'] + '-closed')
            for row in reads:
                if row['id'] in entries:
                    entries[row['id']]['evidence'].extend(row['evidence'])
                else:
                    entries[row['id']] = row
            results.append({'route': route['id'], 'approach_position': approach, 'reads': completed,
                            'choices': choices, 'inputs': game.inputs[input_start:]})
    report = {'passed': True, 'source_rom_sha256': digest(original), 'fixture_state_sha256': digest(snapshot.state),
              'routes_sha256': digest(ROUTES.read_bytes()), 'routes': results, 'entries': list(entries.values()),
              'scope': 'Six ordinary-input routes to five NPCs, including both guard-choice outcomes, restoring one naturally reached Japanese castle checkpoint between routes. No RAM overrides; not all castle states or conversations.'}
    (output / 'trace.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print('Castle conversations:', len(results), 'routes,', len(entries), 'unique sources')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fixture', type=Path, default=FIXTURE)
    parser.add_argument('--output', type=Path, default=OUTPUT)
    args = parser.parse_args()
    run(args.fixture.resolve(), args.output.resolve())
