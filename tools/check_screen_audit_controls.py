"""Prove the unfiltered audit rejects retained bad banner and gold builds."""
import mgba.log

from tools.audit_dungeon_screens import run, save_json
from tools.emulator import Debugger, Session
from tools.rom import ROOT, digest, require
from tools.screen_text_audit import ScreenTextAudit
from tools.verify_location_banner import fresh_fixture


def main():
    mgba.log.silence()
    root = ROOT/'build/coverage-audit'
    cases = run(['natural-gold-arrows-combat'], root/'pre-fix', root/'negative-control')
    require(len(cases) == 1 and not cases[0]['passed'] and
            cases[0]['route_error'] == 'Gold pickup lacks the English word space' and
            not cases[0]['unclassified_glyphs'], 'Old gold build failed for an unrelated reason')
    output = root/'untranslated-banner-control'
    rom = (ROOT/'build/location-banner/pre-fix/torneko-2-english.gba').read_bytes()
    fixture = fresh_fixture(rom, output/'fixture')
    with Session(rom, output) as game:
        game.restore(fixture)
        audit = ScreenTextAudit(game)
        with Debugger(game, audit.callback, max_events=30000) as debug:
            for address in audit.ADDRESSES:
                debug.breakpoint(address)
            game.press('B', hold=8, wait=120)
            game.capture('menu')
        require(len(audit.observer.reads) == 5 and
                any(g['code'] == 0x82BF for g in audit.unclassified),
                'Unfiltered audit failed to reject Japanese in the unregistered banner')
        save_json(output/'report.json', {'rom_sha256': digest(rom), 'rejected': True,
            'inputs': game.inputs, 'controlled_overrides': [],
            'fixture_sha256': digest(fixture.state),
            'reason': 'Unclassified Japanese glyphs in an unregistered location reader',
            'generator_sha256': digest((ROOT/'tools/screen_text_audit.py').read_bytes()),
            'image_sha256': digest((output/'menu.png').read_bytes()), **audit.report()})
    print('Historical controls rejected: missing gold separator and untranslated banner.')


if __name__ == '__main__':
    main()
