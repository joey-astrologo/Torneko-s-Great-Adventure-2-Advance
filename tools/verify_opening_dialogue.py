"""Normal-input English opening checks: sources, glyphs, pages and both choices."""

import argparse
import json
from pathlib import Path

import mgba.log

from tools.build_english import build_rom
from tools.dialogue_checks import TextChecks
from tools.emulator import BIOS, Debugger, Session, Snapshot, version
from tools.event_text import opening_entries
from tools.lz77 import decompress
from tools.name_entry import HERO, STORED, indexed
from tools.name_entry_route import NameEntryRoute
from tools.name_entry_playtest import position
from tools.opening_text import BANK_RAM
from tools.rom import ROOT, default_rom, digest, load_base, require
from tools.verify_name_entry import open_editor
from tools.verify_compact_font import call_thumb

OUTPUT = ROOT / 'build/english/dialogue-validation'


def run_route(rom, build, branch, output):
    resources = {0x08000000 + row['rom_offset']: row for row in build['dialogue']['entries']
                 if row['batch'] == 'opening-dialogue'}
    choice_active = False
    commands, choices, captures = [], [], []
    bank_checks = 0
    bank_before = None
    bank_data, _ = decompress(rom, build['dialogue']['bank_rom_offset'])
    with Session(rom, output) as game:
        checks = TextChecks(game, resources)
        def callback(event):
            nonlocal choice_active, bank_checks, bank_before
            checks.callback(event)
            r, address = event['registers'], event['address']
            memory = game.core.memory
            if address == 0x0804D722:
                bank_before = (bytes(memory[BANK_RAM - 64:BANK_RAM]),
                               bytes(memory[BANK_RAM + len(bank_data):BANK_RAM + len(bank_data) + 64]),
                               r[4:12], r[13])
            elif address == 0x0804D726:
                require(bytes(memory[BANK_RAM:BANK_RAM + len(bank_data)]) == bank_data, 'Native rebuilt bank differs')
                require(bank_before == (bytes(memory[BANK_RAM - 64:BANK_RAM]),
                        bytes(memory[BANK_RAM + len(bank_data):BANK_RAM + len(bank_data) + 64]),
                        r[4:12], r[13]), 'Rebuilt bank loader changed guards or preserved registers')
                bank_checks += 1
            elif address == 0x08015A50:
                require(r[0] in resources, 'Untranslated story/help source on the opening route')
            elif address == 0x08051664:
                commands.append({'command': bytes(memory[r[0]:r[0] + 3]).decode('ascii'),
                                 'source': r[0], 'before_flags': memory.u8[0x0201020E]})
            elif address == 0x080516AE:
                commands[-1]['after_flags'] = memory.u8[0x0201020E]
            elif address == 0x08015CE8:
                choice_active = True
                game.snapshot().save(output / 'choice')
            elif address == 0x08015E28:
                choice_active = False
                choices.append(r[0])
        with Debugger(game, callback, max_events=150000) as trace:
            for address in (0x0804D722, 0x0804D726, 0x08015A50, 0x080021B4, 0x08001BC4, 0x08001C14, 0x08001C68, 0x080023A0,
                            0x08002284, 0x08051664, 0x080516AE, 0x08015CE8, 0x08015E28):
                trace.breakpoint(address)
            open_editor(game)
            editor = NameEntryRoute(game, build['name_entry']['keyboard_pages'])
            editor.clear()
            editor.enter('Torneko')
            editor.confirm()
            for i in range(160):
                if choice_active and not choices:
                    if branch == 'no':
                        game.press('RIGHT', wait=30)
                    game.capture('choice-' + branch)
                game.press('A', wait=240)
                picture = game.capture(f'page-{i:03}')
                captures.append({'file': f'page-{i:03}.png', 'frame': game.core.frame_counter,
                                 'rgb_sha256': digest(picture.tobytes())})
                if checks.completed('rom.0006b0e8'):
                    break
            require(checks.completed('rom.0006b0e8') and checks.active is None, 'Opening did not finish English help')
            game.press('A', wait=120)
            before = position(game)
            moved = False
            for direction in ('RIGHT', 'DOWN', 'LEFT', 'UP'):
                game.press(direction, wait=30)
                if position(game) != before:
                    moved = True
                    break
            require(moved, 'Normal movement after opening failed')
            game.capture('first-movement')
            game.snapshot().save(output / 'first-movement')
            require(bytes(game.core.memory[STORED:STORED + 16]) == indexed('Torneko'), 'Opening changed saved name')
        require(bank_checks == 1 and choices == [int(branch == 'yes')], 'Bank load or choice outcome differs')
        require([(c['command'], c['before_flags'], c['after_flags']) for c in commands] ==
                [('@B@', 0x14, 0x0C), ('@C@', 0x0C, 0x14)], 'English event side effects differ')
        required = {r['id'] for r in resources.values()} - {f"event-bank-0.{'1190' if branch == 'yes' else '1103'}"}
        require({r['id'] for r in checks.reads} == required, 'Opening source coverage differs')
        inputs = game.inputs
    report = {'passed': True, 'branch': branch, 'rom_sha256': digest(rom), 'inputs': inputs,
              'native_bank_checks': bank_checks, 'native_glyph_checks': checks.glyph_checks, 'reads': checks.reads,
              'commands': commands, 'choices': choices, 'captures': captures, 'normal_movement': True}
    (output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(branch, 'passed', checks.glyph_checks, 'glyphs', len(checks.reads), 'reads')
    return report


def run(output=OUTPUT):
    mgba.log.silence()
    original = load_base()
    save = default_rom().with_suffix('.sav')
    save_hash = digest(save.read_bytes())
    rom, build = build_rom()
    reports = [run_route(rom, build, branch, output / branch) for branch in ('yes', 'no')]
    tables = check_table_getters(rom, build, output)
    require(digest(load_base()) == digest(original) and digest(save.read_bytes()) == save_hash, 'Original files changed')
    report = {'passed': True, 'source_rom_sha256': digest(original), 'source_save_sha256': save_hash,
              'output_rom_sha256': digest(rom), 'emulator': version(), 'bios': BIOS,
              'original_files_unchanged': True, 'branches': reports,
              'unique_sources': sum(r['batch'] == 'opening-dialogue' for r in build['dialogue']['entries']),
              'controlled_table_getters': tables,
              'scope': 'Normal opening through both choices, first-floor help and movement. Later gameplay and graphics remain separate.'}
    (output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


def check_table_getters(rom, build, output):
    """Restore each controlled function call; these are not extra gameplay routes."""
    targets = {row['id']: 0x08000000 + row['rom_offset'] for row in build['dialogue']['entries']}
    reports = []
    cases = [('japanese', load_base(), None),
             ('english', rom, output / 'yes/choice')]
    for label, data, fixture in cases:
        with Session(data, output / ('table-getter-' + label)) as game:
            if fixture is not None:
                game.restore(Snapshot.load(fixture))
            else:
                # Generate the Japanese context from normal inputs on each run;
                # a clean output directory needs no historical checkpoint.
                with Debugger(game) as trace:
                    trace.breakpoint(0x08015CE8)
                    for step in json.loads((ROOT / 'config/routes/opening.json').read_text())['steps']:
                        if 'frames' in step:
                            game.frames(step['frames'])
                        elif 'press' in step:
                            game.press(step['press'], wait=step.get('wait', 120), hold=step.get('hold', 3))
                        if trace.events:
                            break
                    require(trace.events, 'Japanese choice context not reached')
            for row in opening_entries():
                expected = BANK_RAM + row['start']
                if label == 'english':
                    expected = targets.get(row['id'], expected)
                result = call_thumb(game, 0x08050270, row['group'], row['index'])
                require(result['r0'] == expected, 'Native group/index getter differs')
                reports.append({'rom': label, 'id': row['id'], 'group': row['group'], 'index': row['index'],
                                'expected': expected, 'result': result})
    return reports


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=OUTPUT)
    run(parser.parse_args().output.resolve())
