"""Verify English resume, first-dungeon tutorials and stair choices in native play."""

import argparse
import json
from pathlib import Path

import mgba.log

from tools.build_english import build_rom
from tools.dialogue_checks import TextChecks
from tools.emulator import BIOS, Debugger, Session, version
from tools.name_entry import STORED, indexed
from tools.name_entry_playtest import ACTORS, nearby_monsters, position, walk_to_stairs
from tools.rom import ROOT, default_rom, digest, load_base, require

OUTPUT = ROOT / 'build/english/first-dungeon-validation'
SAVE = ROOT / 'build/english/name-entry-validation/english-save/native-save.sav'


def run(save=SAVE, output=OUTPUT):
    mgba.log.silence()
    rom, build = build_rom()
    original_save = default_rom().with_suffix('.sav')
    original_hash = digest(original_save.read_bytes())
    battery = save.read_bytes()
    resources = {0x08000000 + row['rom_offset']: row for row in build['dialogue']['entries']
                 if row['batch'] == 'first-dungeon' or row['id'] == 'rom.0006309c'}
    with Session(rom, output, initial_save=battery) as game:
        checks = TextChecks(game, resources)
        with Debugger(game, checks.callback, max_events=40000) as trace:
            for address in checks.ADDRESSES:
                trace.breakpoint(address)
            game.frames(600)
            game.press('START', wait=180)
            game.capture('resume-menu')
            for i in range(16):
                game.press('A', wait=600)
                game.capture(f'resume-{i:02}')
                if checks.completed('rom.0006b080'):
                    break
            require(checks.completed('rom.0006b080'), 'Native English floor-two help not reached')
            game.press('A', wait=120)
            walk = walk_to_stairs(game)
            game.capture('stairs-menu')
            require(checks.completed('rom.0006b570'), 'Native English stair menu missing')
            stairs = game.snapshot()
            stair_position = position(game)
            game.press('DOWN', wait=30)
            game.capture('stay-selected')
            game.press('A', wait=120)
            require(position(game) == stair_position and not checks.completed('rom.0006b03c'),
                    'Stay unexpectedly moved to another floor')
            game.capture('stayed-on-floor-two')
            # A checked branch checkpoint, reached with normal inputs. Resume
            # it to test the other stair response without altering game state.
            game.restore(stairs)
            # Audited ordinary-input route variation: leave and re-enter the
            # floor-two stairs before selecting Descend.
            game.press('B',wait=120)
            step_origin=position(game)
            for direction,back in [('LEFT','RIGHT'),('DOWN','UP'),('UP','DOWN'),('RIGHT','LEFT')]:
                game.press(direction,wait=120)
                if position(game)!=step_origin:
                    game.press(back,wait=120)
                    require(position(game)==step_origin,'Stair round trip failed')
                    break
            else:raise ValueError('No ordinary stair round-trip step')
            game.press('A', wait=600)
            game.capture('floor-three-help')
            for _ in range(8):
                if checks.completed('rom.0006b03c'):
                    break
                game.press('A', wait=240)
            require(checks.completed('rom.0006b03c'), 'Descend did not reach floor-three English help')
            game.press('A', wait=120)
            actor = game.core.memory.u32[ACTORS]
            hp_before = game.core.memory.u16[actor + 0x84]
            rest = {'attempted': False}
            if not nearby_monsters(game, 3):
                game.press(('A', 'B'), hold=60, wait=60)
                hp_after = game.core.memory.u16[actor + 0x84]
                require(hp_after >= hp_before, 'Safe combined-button rest lost HP')
                rest = {'attempted': True, 'hp_before': hp_before, 'hp_after': hp_after,
                        'keys': ['A', 'B'], 'native_key_mask_checked': True}
                game.capture('after-rest')
            before = position(game)
            for key in ('RIGHT', 'DOWN', 'LEFT', 'UP'):
                game.press(key, wait=30)
                if position(game) != before:
                    break
            require(position(game) != before, 'No ordinary movement after floor-three help')
            game.capture('floor-three-movement')
            game.snapshot().save(output / 'floor-three')
            require(bytes(game.core.memory[STORED:STORED + 16]) == indexed('Torneko'), 'Dungeon changed seven-letter name')
            require({r['id'] for r in checks.reads} == {r['id'] for r in resources.values()}, 'Dungeon UI source coverage differs')
            require(checks.active is None, 'English reader did not finish')
        report = {'passed': True, 'output_rom_sha256': digest(rom), 'initial_save_sha256': digest(battery),
                  'source_rom_sha256': digest(load_base()), 'source_save_sha256': original_hash,
                  'emulator': version(), 'bios': BIOS, 'reads': checks.reads, 'native_glyph_checks': checks.glyph_checks,
                  'unique_sources': len(resources), 'inputs': game.inputs, 'walk': walk, 'rest': rest,
                  'stay_branch_preserved_floor': True, 'descend_reached_floor_three': True,
                  'scope': 'English initial-menu labels, Yes resume, floor-two/three tutorials and movement; Stay/Descend branch checkpoint. Save and suspend is checked separately by verify_name_entry. Erase action and No-resume inventory loss are not exercised.'}
    require(digest(original_save.read_bytes()) == original_hash, 'Original save changed')
    report['original_files_unchanged'] = True
    (output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print('First dungeon passed:', checks.glyph_checks, 'glyphs,', len(checks.reads), 'reads;', rest)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--save', type=Path, default=SAVE)
    parser.add_argument('--output', type=Path, default=OUTPUT)
    args = parser.parse_args()
    run(args.save.resolve(), args.output.resolve())
