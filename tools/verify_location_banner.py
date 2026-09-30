"""Check every dungeon-menu field and all 13 names through open/cancel/reopen."""
import argparse
import html
import json
from pathlib import Path

import mgba.log

from tools.audit_menu_layouts import Observer
from tools.dialogue_checks import TextChecks
from tools.emulator import BIOS, Debugger, Session, Snapshot, version
from tools.extract_graphics_audition import save_json
from tools.menu_checks import MenuChecks
from tools.name_entry_playtest import ACTORS, position
from tools.numeric_font import ALIASES
from tools.rom import ROOT, default_rom, digest, load_base, require
from tools.verify_service_ui import UiChecks

OUT = ROOT / 'build/location-banner'


def fresh_fixture(rom, folder):
    """Replay the recorded opening; no imported state or RAM edits."""
    route = ROOT / 'config/routes/readme.json'
    with Session(rom, folder) as game:
        for step in json.loads(route.read_text())['steps']:
            if 'frames' in step:
                game.frames(step['frames'])
            elif 'press' in step:
                game.press(step['press'], hold=step['hold'], wait=step['wait'])
            if game.core.frame_counter == 19773:
                break
        require(game.core.frame_counter == 19773 and game.core.memory.u32[0x02003B6C] == 11 and
                game.core.memory.u16[0x02005674] == 1, 'First-floor menu fixture differs')
        position(game)
        snap = game.snapshot()
        snap.save(folder / 'ready')
        save_json(folder / 'inputs.json', {'rom_sha256': digest(rom), 'inputs': game.inputs,
                  'route_sha256': digest(route.read_bytes()), 'controlled_overrides': []})
        return snap


def check_case(rom, build, fixture, selector, mode, folder):
    row = build['location_banner']['entries'][selector]
    resources = {e['offset'] + 0x08000000:
                 {'id': e['id'], 'encoded_hex': e['encoded_hex'], 'layout': {'pages': [[e['english']]]}}
                 for e in build['location_banner']['entries']}
    with Session(rom, folder) as game:
        game.restore(fixture)
        m = game.core.memory
        actor = m.u32[ACTORS]
        original_mode = m.u8[actor + 0x90]
        overrides = []
        if mode != original_mode:
            overrides.append({'address': actor + 0x90, 'before': original_mode, 'after': mode,
                              'reason': 'Controlled main-command mode; not a native class-unlock route'})
            m.u8[actor + 0x90] = mode
        observer, commands, status = Observer(game), MenuChecks(game, build['menus']), UiChecks(game, build['ui'])
        banner = TextChecks(game, resources)
        selection_reads = []
        glyph_codes = set()

        def callback(event):
            a, r = event['address'], event['registers']
            if a == 0x08019E16 and r[1] != selector:
                overrides.append({'frame': event['frame'], 'register': 'r1', 'before': r[1], 'after': selector,
                                  'reason': 'Controlled banner selector immediately after reading the native dungeon ID'})
                game.core.cpu.gprs[1] = selector
            if a == 0x08019E24:
                require(r[1] == row['offset'] + 0x08000000,
                        'Dungeon location banner bypassed the reviewed English pointer')
                selection_reads.append({'frame': event['frame'], 'pointer': r[1], 'window': r[0]})
            if a == 0x08001BC4:
                code = r[1]
                require(0xF020 <= code <= 0xF07E or code in ALIASES or code in (0x20, 0x8140),
                        f'Untranslated glyph {code:04x} in the complete dungeon-menu screen')
                glyph_codes.add(code)
            for checks in (observer, commands, status, banner):
                if a in checks.ADDRESSES:
                    checks.callback(event)

        captures = []
        first_banner = None
        with Debugger(game, callback, max_events=80000) as debug:
            for a in set(observer.ADDRESSES + commands.ADDRESSES + status.ADDRESSES +
                         banner.ADDRESSES + (0x08019E16, 0x08019E24)):
                debug.breakpoint(a)
            for phase in ('open', 'reopen', 'reopen-again'):
                start = len(observer.reads)
                game.press('B', hold=8, wait=240)
                picture = game.capture(phase)
                reads = observer.reads[start:]
                require(len(reads) == 5, 'Unaccounted-for dungeon-menu text field')
                fields = [(r['screen_x'], r['screen_y'], r['window_width'], r['rows']) for r in reads]
                require(fields[:3] == [(8, 104, 224, 3)] * 3 and
                        fields[3] == (8, 24, 40, 3 if mode == 0 else 4) and
                        fields[4] == (64, 32, 168, 1), 'Main menu geometry or field coverage changed')
                location = reads[4]
                require(location['source'] == row['offset'] + 0x08000000 and
                        location['raw_hex'] == row['encoded_hex'] and location['initial_x'] == 0 and
                        location['fixed_advance'] == location['spacing'] == 0, 'Banner content/layout differs')
                require(all(g['row'] == 0 for g in location['glyph_positions']), 'Location wrapped')
                # Main outer border ends at x52; banner outer border starts x60.
                require(location['screen_x'] - 4 - (reads[3]['screen_x'] + reads[3]['window_width'] + 4) == 8,
                        'Main/banner border gap changed')
                pixels = picture.crop((60, 28, 236, 52)).tobytes()
                if first_banner is None:
                    first_banner = pixels
                require(pixels == first_banner, 'Banner pixels changed after cancellation/reopening')
                captures.append({'phase': phase, 'frame': game.core.frame_counter,
                                 'png_sha256': digest((folder / (phase + '.png')).read_bytes()),
                                 'banner_rgb_sha256': digest(pixels), 'all_five_fields_checked': True})
                game.press('B', wait=120)
        require(not commands.active and not status.active and not status.pending and not banner.active,
                'Menu text verification incomplete')
        require(len(banner.reads) == len(selection_reads) == 3 and len(status.formats) == 9,
                'Menu family did not complete all three openings')
        require(game.snapshot().battery == fixture.battery and m.u32[0x02003B6C] == 11,
                'Menu checks changed save or dungeon identity')
        m.u8[actor + 0x90] = original_mode
        result = {'selector': selector, 'english': row['english'], 'mode': mode,
                  'natural': selector == 11 and mode == 0, 'overrides': overrides,
                  'inputs': game.inputs, 'captures': captures, 'selection_reads': selection_reads,
                  'all_native_glyph_codes': sorted(glyph_codes), 'banner_reads': banner.reads,
                  'banner_glyph_checks': banner.glyph_checks, 'status_formats': status.formats,
                  'command_formats': commands.formats, 'native_fields': observer.reads,
                  'width_px': row['banner_width'], 'budget_px': 168,
                  'battery_and_dungeon_identity_unchanged': True}
        save_json(folder / 'report.json', result)
        return result


def run(source, reject_old=False):
    mgba.log.silence()
    rom = (source / 'torneko-2-english.gba').read_bytes()
    build = json.loads((source / 'build.json').read_text())
    require(digest(rom) == build['output_sha256'], 'Build identity differs')
    protected = {str(p): digest(p.read_bytes()) for p in (default_rom(), default_rom().with_suffix('.sav'))}
    fixture = fresh_fixture(rom, OUT / 'fixture')
    cases = []
    for mode in range(3):
        for selector in range(13):
            cases.append(check_case(rom, build, fixture, selector, mode,
                                    OUT / 'native' / f'{selector:02}-mode-{mode}'))
    negative = None
    if reject_old:
        old = (OUT / 'pre-fix/torneko-2-english.gba').read_bytes()
        old_fixture = fresh_fixture(old, OUT / 'pre-fix-fixture')
        try:
            check_case(old, build, old_fixture, 11, 0, OUT / 'negative-control')
        except RuntimeError as error:
            reason = str(error.__cause__)
            require(reason == 'Dungeon location banner bypassed the reviewed English pointer',
                    'Negative control failed for an unrelated reason')
            negative = {'rom_sha256': digest(old), 'rejected': True, 'reason': reason}
        else:
            raise ValueError('The untranslated previous ROM passed the menu check')
    require(all(digest(Path(p).read_bytes()) == sha for p, sha in protected.items()), 'Original files changed')
    report = {'passed': True, 'rom_sha256': digest(rom), 'source_sha256': digest(load_base()),
              'generator_sha256': digest(Path(__file__).read_bytes()), 'emulator': version(), 'bios': BIOS,
              'fixture_state_sha256': digest(fixture.state), 'fixture_battery_sha256': digest(fixture.battery),
              'fixture_inputs_sha256': digest((OUT / 'fixture/inputs.json').read_bytes()),
              'cases': cases, 'negative_control': negative, 'original_files_unchanged': True,
              'scope': '39 cases: all 13 location labels in three main-command modes, each opened three times. '
                       'Every native glyph and all five text fields checked. Mysterious Meadow/normal mode is ordinary '
                       'fresh-game play; other selectors/class modes are controlled display probes. Not late-game route coverage.'}
    save_json(OUT / 'report.json', report)
    cards = ''.join(f'<figure><img src="native/{r["selector"]:02}-mode-0/open.png" alt="{html.escape(r["english"])}">'
                    f'<figcaption>{html.escape(r["english"])} · {r["width_px"]}/168px'
                    f' · {"ordinary route" if r["natural"] else "controlled banner selector"}</figcaption></figure>'
                    for r in cases if r['mode'] == 0)
    (OUT / 'index.html').write_text('<!doctype html><meta charset="utf-8"><title>Torneko 2 location banners</title>'
        '<style>body{background:#15212b;color:white;font:16px system-ui;margin:32px}figure{display:inline-block;margin:12px}'
        'img{width:480px;max-width:100%;image-rendering:pixelated}a{color:#9de6d0}</style>'
        '<h1>English dungeon-menu location banners</h1><p>Actual mGBA frames. All 13 names fit the original window. '
        'Commands, status fields and banner are checked together through cancellation and reopening.</p>'
        '<p><a href="report.json">39-case native report</a> · <a href="../torneko-2-english.gba">Latest ROM</a> · '
        '<a href="../torneko-2-english.bps">BPS patch</a></p>' + cards + f'<p>ROM SHA256: {digest(rom)}</p>')
    print('Dungeon menu: 39 cases, 117 openings; all five fields and every drawn glyph checked.')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=ROOT / 'build/english')
    parser.add_argument('--reject-old', action='store_true')
    args = parser.parse_args()
    run(args.source.resolve(), args.reject_old)
