"""Replay the first castle NPC routes with English text and both guard choices."""

import argparse
import json
from pathlib import Path

import mgba.log

from tools.build_english import build_rom
from tools.dialogue_checks import TextChecks
from tools.emulator import Debugger, Session, Snapshot
from tools.rom import ROOT, default_rom, digest, load_base, require
from tools.trace_castle_conversations import ROUTES
from tools.town_playtest import position

OUTPUT = ROOT / 'build/english/castle-conversations-validation'
FIXTURE = ROOT / 'build/english/castle-validation/audience-complete'
EXPECTED = {
    'king-repeat': ['event-bank-0.2914'],
    'left-adviser': ['event-bank-0.29bf'],
    'right-courtier': ['event-bank-0.2948'],
    'left-guard': ['event-bank-0.2a54'],
    'right-guard-yes': ['event-bank-0.2c86', 'rom.0006309c', 'event-bank-0.2cbc'],
    'right-guard-no': ['event-bank-0.2c86', 'rom.0006309c', 'event-bank-0.2d20'],
}


def run(fixture=FIXTURE, output=OUTPUT):
    mgba.log.silence()
    rom, build = build_rom()
    source_save = default_rom().with_suffix('.sav')
    save_hash = digest(source_save.read_bytes())
    rows = {0x08000000 + row['rom_offset']: row for row in build['dialogue']['entries']
            if row['batch'] == 'castle-conversations' or row['id'] == 'rom.0006309c'}
    routes = json.loads(ROUTES.read_text())
    snapshot = Snapshot.load(fixture)
    results = []
    with Session(rom, output) as game:
        for route in routes['routes']:
            game.restore(snapshot)
            input_start = len(game.inputs) - 1
            require(list(position(game)) == routes['start_position'], 'English castle route start differs')
            checks, choices = TextChecks(game, rows), []
            choice_seen = chose_no = False
            def callback(event):
                nonlocal choice_seen
                r = event['registers']
                if event['address'] == 0x08015A50:
                    require(r[0] in rows, 'Untranslated story reached in castle route')
                    return
                if event['address'] == 0x08015CE8:
                    choice_seen = True
                    return
                if event['address'] == 0x08015E28:
                    choices.append(r[0])
                    return
                checks.callback(event)
            with Debugger(game, callback, max_events=10000) as trace:
                for address in checks.ADDRESSES + (0x08015A50, 0x08015CE8, 0x08015E28):
                    trace.breakpoint(address)
                for step in route['steps']:
                    game.press(step['key'], hold=step['hold'], wait=30)
                game.press('A', wait=240)
                for page in range(32):
                    game.capture(route['id'] + f'-{page:02}')
                    before_reads = len(checks.reads)
                    if route.get('choice') == 'no' and choice_seen and not chose_no:
                        game.press('RIGHT', wait=30)
                        chose_no = True
                        game.capture(route['id'] + '-choice-no')
                    game.press('A', wait=240)
                    if checks.reads and checks.active is None and len(checks.reads) == before_reads:
                        break
                require(checks.active is None and [row['id'] for row in checks.reads] == EXPECTED[route['id']],
                        'English NPC source sequence differs from Japanese route: ' + route['id'])
                require(choices == ([int(route['choice'] == 'yes')] if 'choice' in route else []),
                        'English castle choice result differs')
                before = position(game)
                game.press('DOWN', hold=16, wait=90)
                after = position(game)
                require(after[0] == before[0] and after[1] > before[1], 'NPC dialogue did not return town movement')
                game.capture(route['id'] + '-movement')
            results.append({'route': route['id'], 'passed': True, 'choices': choices, 'reads': checks.reads,
                            'native_glyph_checks': checks.glyph_checks, 'movement': {'before': before, 'after': after},
                            'inputs': game.inputs[input_start:]})
    require(digest(source_save.read_bytes()) == save_hash, 'Original save changed')
    report = {'passed': True, 'output_rom_sha256': digest(rom), 'source_rom_sha256': digest(load_base()),
              'source_save_sha256': save_hash, 'original_files_unchanged': True,
              'fixture_state_sha256': digest(snapshot.state), 'routes_sha256': digest(ROUTES.read_bytes()),
              'routes': results, 'native_glyph_checks': sum(row['native_glyph_checks'] for row in results),
              'scope': 'Six normal-input routes from one naturally reached English audience-completion checkpoint; five NPCs, both guard choices, resumed town movement. Later castle states are outside this acceptance.'}
    (output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print('English castle conversations:', len(results), 'routes,', report['native_glyph_checks'], 'native glyphs')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fixture', type=Path, default=FIXTURE)
    parser.add_argument('--output', type=Path, default=OUTPUT)
    args = parser.parse_args()
    run(args.fixture.resolve(), args.output.resolve())
