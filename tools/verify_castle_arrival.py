"""Reach the King's English audience and probe bounded native name substitutions."""

import argparse
import json
from pathlib import Path

import mgba.log

from tools.build_english import build_rom
from tools.dialogue_checks import TextChecks, player_layout_cases
from tools.emulator import Debugger, Session, Snapshot
from tools.name_entry import HERO
from tools.name_entry_playtest import walk_to_stairs
from tools.rom import ROOT, default_rom, digest, load_base, require
from tools.town_playtest import MOVE, position

OUTPUT = ROOT / 'build/english/castle-validation'
FIXTURE = ROOT / 'build/english/first-dungeon-validation/floor-three'


def run(fixture=FIXTURE, output=OUTPUT):
    mgba.log.silence()
    rom, build = build_rom()
    source_save = default_rom().with_suffix('.sav')
    save_hash = digest(source_save.read_bytes())
    rows = {0x08000000 + r['rom_offset']: r for r in build['dialogue']['entries'] if r['batch'] == 'castle-arrival'}
    ident = 'event-bank-0.26c0'
    with Session(rom, output / 'natural') as game:
        game.restore(Snapshot.load(fixture))
        checks = TextChecks(game, rows)
        movement = []
        def callback(event):
            if event['address'] == MOVE:
                movement.append({'frame': event['frame'], 'direction': event['registers'][0],
                                 'step_index': event['registers'][1]})
                return
            if event['address'] == 0x08015A50:
                if event['registers'][0] in rows:
                    game.snapshot().save(output / 'king-reader')
                return
            checks.callback(event)
        with Debugger(game, callback, max_events=30000) as trace:
            for address in checks.ADDRESSES:
                trace.breakpoint(address)
            trace.breakpoint(MOVE)
            trace.breakpoint(0x08015A50)
            walk = walk_to_stairs(game)
            game.capture('floor-three-stairs')
            game.press('A', wait=600)
            for i in range(64):
                game.capture(f'audience-{i:02}')
                if checks.completed(ident):
                    break
                game.press('A', wait=240)
            require(checks.completed(ident), 'English first audience not reached')
            game.press('A', wait=180)
            game.snapshot().save(output / 'audience-complete')
            before = position(game)
            movement.clear()
            game.press('DOWN', hold=16, wait=120)
            after = position(game)
            require(after[0] == before[0] and after[1] > before[1] and movement and
                    all(row['direction'] == 4 for row in movement), 'Native town movement did not resume')
            game.capture('after-audience')
            game.snapshot().save(output / 'after-audience')
        natural = {'passed': True, 'inputs': game.inputs, 'walk': walk, 'reads': checks.reads,
                   'native_glyph_checks': checks.glyph_checks,
                   'movement_after_audience': {'before': before, 'after': after, 'calls': movement}}
    # These cases change only the existing name record in a disposable reader
    # snapshot. They are controlled layout probes, not newly created save files.
    cases = player_layout_cases()
    controlled = []
    with Session(rom, output / 'controlled') as game:
        snapshot = Snapshot.load(output / 'king-reader')
        for label, name in cases:
            game.restore(snapshot)
            input_start = len(game.inputs) - 1
            before = bytes(game.core.memory[HERO - 16:HERO])
            after = bytes(game.core.memory[HERO + 16:HERO + 32])
            for i, value in enumerate(name.ljust(16, b'\0')):
                game.core.memory.u8[HERO + i] = value
            checks = TextChecks(game, rows)
            try:
                with Debugger(game, checks.callback, max_events=15000) as trace:
                    for address in checks.ADDRESSES:
                        trace.breakpoint(address)
                    game.frames(180)
                    game.capture(label + '-first-page')
                    for _ in range(64):
                        if checks.completed(ident):
                            break
                        game.press('A', wait=180)
                    require(checks.completed(ident), 'Controlled name audience did not finish')
                require(bytes(game.core.memory[HERO - 16:HERO]) == before and
                        bytes(game.core.memory[HERO + 16:HERO + 32]) == after, 'Name substitution changed adjacent fields')
                controlled.append({'label': label, 'name_hex': name.hex(), 'passed': True,
                                   'inputs': game.inputs[input_start:],
                                   'native_glyph_checks': checks.glyph_checks, 'reads': checks.reads,
                                   'name_record_only_override': True, 'adjacent_fields_preserved': True})
            finally:
                game.restore(snapshot)
    require(digest(source_save.read_bytes()) == save_hash, 'Original save changed')
    report = {'passed': True, 'output_rom_sha256': digest(rom), 'source_rom_sha256': digest(load_base()),
              'source_save_sha256': save_hash, 'original_files_unchanged': True,
              'natural': natural, 'controlled_names': controlled,
              'scope': 'Normal continuation of verified English floor-three fixture to the first audience and resumed movement; three separate controlled name/width probes. Further castle conversations remain untranslated.'}
    (output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print('Castle audience passed:', natural['native_glyph_checks'], 'natural glyphs,', len(controlled), 'name cases')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fixture', type=Path, default=FIXTURE)
    parser.add_argument('--output', type=Path, default=OUTPUT)
    args = parser.parse_args()
    run(args.fixture.resolve(), args.output.resolve())
