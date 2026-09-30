"""Observe complete town-root, bank and storage screens through ordinary inputs."""
import json
from pathlib import Path

import mgba.log

from tools.audit_dungeon_screens import AuditedSession, save_json
from tools.bakery_playtest import service_ready
from tools.emulator import BIOS, Debugger, Session, version
from tools.holy_flame_playtest import items
from tools.rom import ROOT, default_rom, digest, require
from tools.screen_text_audit import ScreenTextAudit
from tools.verify_bank import BankChecks, balance, next_menu, open_bank
from tools.verify_storage import SAVE

OUT = ROOT/'build/coverage-audit/town'


def town_root(game, details, bank):
    for label in ('open', 'reopen'):
        first = len(game.audit.observer.reads)
        game.press('B', hold=8, wait=120)
        game.capture(label)
        reads = game.audit.observer.reads[first:]
        require(len(reads) == 1 and reads[0]['window_width'] == 40 and reads[0]['rows'] == 2,
                'Town root has unaccounted-for fields')
        game.press('B', hold=8, wait=120)
    details['fields'] = ['Items', 'Option']


def bank_roundtrip(game, details, bank):
    before = balance(game)
    require(before[0] > 0 and before[1] == 0, 'Expected earned wallet and empty bank')
    open_bank(game)
    game.capture('bank-menu')
    game.press('A', wait=120)
    game.capture('deposit-amount')
    game.press('A', wait=120)
    require(balance(game) == (0, before[0]), 'Ordinary deposit failed')
    game.capture('deposited')
    next_menu(game, bank)
    game.press('DOWN', wait=30)
    game.press('A', wait=120)
    game.capture('withdraw-amount')
    game.press('A', wait=120)
    require(balance(game) == before, 'Ordinary withdrawal failed')
    game.capture('withdrawn')
    next_menu(game, bank)
    game.press('B', wait=120)
    details.update(balance_before=before, balance_after=balance(game))


def storage_roundtrip(game, details, bank):
    before = items(game)
    require([i for _, i, _ in before] == [204, 51], 'Earned inventory differs')
    game.press('A', wait=120)
    game.capture('storage-menu')
    game.press('A', wait=120)
    game.capture('carried')
    game.press('R', wait=60)
    game.capture('marked')
    game.press('A', wait=120)
    require([i for _, i, _ in items(game)] == [51], 'Storage deposit failed')
    game.capture('deposited')
    game.press('A', wait=120)
    game.press('RIGHT', wait=30)
    game.press('A', wait=120)
    game.capture('stored')
    game.press('A', wait=120)
    require(sorted(i for _, i, _ in items(game)) == [51, 204], 'Storage withdrawal failed')
    game.capture('withdrawn')
    game.press('A', wait=120)
    game.press('DOWN', wait=30)
    game.press('A', wait=120)
    game.capture('empty')
    game.press('A', wait=120)
    details.update(inventory_before=before, inventory_after=items(game))


def run():
    mgba.log.silence()
    rom = (ROOT/'build/english/torneko-2-english.gba').read_bytes()
    build = json.loads((ROOT/'build/english/build.json').read_text())
    require(digest(rom) == build['output_sha256'], 'Town build identity differs')
    protected = {str(p): digest(p.read_bytes()) for p in
                 (default_rom(), default_rom().with_suffix('.sav'), SAVE)}
    outside = service_ready(rom, OUT/'bank-fixture')
    with Session(rom, OUT/'storage-fixture', initial_save=SAVE.read_bytes()) as game:
        game.frames(600)
        game.press('START', wait=180)
        game.press('A', wait=300)
        inside = game.snapshot()
        inside.save(OUT/'storage-fixture/ready')
        save_json(OUT/'storage-fixture/inputs.json', {'rom_sha256': digest(rom),
            'source_save_sha256': digest(SAVE.read_bytes()), 'inputs': game.inputs,
            'controlled_overrides': []})
    results = []
    for name, fixture, action in [('town-root-outside', outside, town_root),
                                  ('town-root-inside', inside, town_root),
                                  ('bank-roundtrip', outside, bank_roundtrip),
                                  ('storage-roundtrip', inside, storage_roundtrip)]:
        with AuditedSession(rom, OUT/name) as game:
            game.restore(fixture)
            game.audit = audit = ScreenTextAudit(game)
            game.images = []
            bank = BankChecks(game, build) if name == 'bank-roundtrip' else None
            details, error = {}, None
            def callback(event):
                if event['address'] in audit.ADDRESSES:
                    audit.callback(event)
                if bank and event['address'] in bank.ADDRESSES:
                    bank.callback(event)
            with Debugger(game, callback, max_events=300000) as debug:
                for address in set(audit.ADDRESSES+(bank.ADDRESSES if bank else ())):
                    debug.breakpoint(address)
                try:
                    action(game, details, bank)
                except Exception as exc:
                    error = str(exc)+((': '+str(exc.__cause__)) if exc.__cause__ else '')
            game.capture('end')
            require(game.snapshot().battery == fixture.battery, 'Town audit unexpectedly saved')
            report = {'case': name, 'rom_sha256': digest(rom), 'emulator': version(), 'bios': BIOS,
                'fixture_state_sha256': digest(fixture.state), 'fixture_battery_sha256': digest(fixture.battery),
                'source_save_sha256': digest(SAVE.read_bytes()), 'inputs': game.inputs,
                'controlled_overrides': [], 'route_error': error, 'images': game.images,
                **details, **audit.report()}
            report['passed'] = not error and not audit.unclassified and not audit.unreadable and not audit.layout_violations
            report['tools_sha256'] = {name: digest((ROOT/'tools'/name).read_bytes()) for name in
                ('audit_town_screens.py', 'audit_dungeon_screens.py', 'screen_text_audit.py', 'audit_menu_layouts.py', 'emulator.py')}
            save_json(OUT/name/'report.json', report)
            results.append(report)
            print(name, 'error:', error, 'unclassified:', sorted({hex(x['code']) for x in audit.unclassified}),
                  'reads:', len(audit.observer.reads), 'layout violations:', len(audit.layout_violations), flush=True)
    require(all(digest(Path(p).read_bytes()) == h for p,h in protected.items()), 'Original inputs changed')
    save_json(OUT/'report.json', {'rom_sha256': digest(rom), 'cases': results,
        'original_files_unchanged': True, 'scope': 'Ordinary B-button town roots, earned-money bank '
        'deposit/withdrawal, repaired-storage deposit/withdrawal/empty acknowledgement. '
        'No injected RAM/register/PC state. Other services/states and graphics renderers remain separate.'})
    require(all(r['passed'] for r in results), 'Town screen audit has unresolved findings')


if __name__ == '__main__':
    run()
