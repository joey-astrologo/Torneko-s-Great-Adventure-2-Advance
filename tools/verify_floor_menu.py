"""Audit all drawn text while opening Floor, Trap and Stairs with normal buttons."""
import argparse
import html
import json
import struct
from pathlib import Path

import mgba.log

from tools.audit_dungeon_screens import save_json
from tools.emulator import Debugger, Session, version
from tools.holy_flame_playtest import items, use
from tools.name_entry_playtest import ACTORS, MAP, position, walk_to_stairs
from tools.rom import ROOT, default_rom, digest, require
from tools.screen_text_audit import ScreenTextAudit
from tools.verify_location_banner import fresh_fixture

CASES = [('empty-merchant', 'empty', 0, None), ('empty-warrior', 'empty', 1, None),
         ('empty-mage', 'empty', 2, None), ('floor-item', 'item', 0, None),
         ('stairs', 'stairs', 0, None), ('trap', 'trap', 0, None),
         ('floor-transformed', 'empty', 0, 0xBF), ('floor-frightened', 'empty', 0, 0x9C),
         ('trap-transformed', 'trap', 0, 0xBF), ('trap-frightened', 'trap', 0, 0x9C),
         ('trap-dancing', 'trap', 0, 0x9A), ('stairs-frightened', 'stairs', 0, 0x9C),
         ('stairs-dancing', 'stairs', 0, 0x9A), ('empty-inventory', 'inventory', 0, None)]


def modal_background(game):
    """BG3 tiles under the modal, excluding independently animated OAM sprites."""
    m = game.core.memory
    control = m.u16[0x0400000E]
    base = 0x06000000 + ((control >> 8) & 31) * 0x800
    chars = 0x06000000 + ((control >> 2) & 3) * 0x4000
    words = [m.u16[base + y*64 + x*2] for y in range(8, 12) for x in range(7, 30)]
    return digest(b''.join(struct.pack('<H', w) + bytes(m[chars+(w&1023)*32:chars+(w&1023)*32+32])
                           for w in words))


def run(source, output, allow_findings=False):
    mgba.log.silence()
    rom = (source / 'torneko-2-english.gba').read_bytes()
    build = json.loads((source / 'build.json').read_text())
    require(digest(rom) == build['output_sha256'], 'Floor-menu ROM/ledger mismatch')
    protected = {str(p): digest(p.read_bytes()) for p in
                 (default_rom(), default_rom().with_suffix('.sav'))}
    fixture = fresh_fixture(rom, output / 'fresh-fixture')
    # An ordinary walk gives the Stairs cases a real first-floor staircase.
    with Session(rom, output / 'stairs-fixture') as g:
        g.restore(fixture)
        steps = walk_to_stairs(g)
        g.press('B', wait=120)  # Cancel the prompt opened automatically upon reaching the stairs.
        stairs = g.snapshot()
        stairs.save(g.output / 'ready')
        save_json(g.output / 'inputs.json', {'rom_sha256': digest(rom),
                  'inputs': g.inputs, 'steps': steps, 'controlled_overrides': []})
    from tools.service_fixtures import dungeon
    item_fixture = dungeon(rom, build)
    item_fixture.save(output / 'item-fixture/ready')
    save_json(output / 'item-fixture/inputs.json', json.loads(
        (ROOT / 'build/services/current-dungeon/inputs.json').read_text()))
    results = []
    for name, kind, mode, condition in CASES:
        snap = item_fixture if kind == 'item' else stairs if kind == 'stairs' else fixture
        with Session(rom, output / name) as g:
            g.restore(snap)
            m = g.core.memory
            actor = m.u32[ACTORS]
            changes, captures, modals, returns = [], [], [], []
            audit = ScreenTextAudit(g)
            error = None

            def write(address, data, reason):
                changes.append({'address': address, 'before': bytes(m[address:address+len(data)]).hex(),
                                'after': data.hex(), 'reason': reason})
                for i, value in enumerate(data):
                    m.u8[address+i] = value

            def capture(label):
                pic = g.capture(label)
                captures.append({'path': label + '.png', 'frame': g.core.frame_counter,
                                 'sha256': digest((g.output / (label + '.png')).read_bytes())})
                return pic

            def callback(event):
                audit.callback(event)
                r = event['registers']
                if event['address'] == 0x08017068:
                    modals.append({'registers': r, 'guard': bytes(m[r[13]:r[13]+32]).hex(),
                                   'source': r[0], 'frame': event['frame']})
                if event['address'] == 0x080170C4:
                    original = modals[-1]
                    require(r[4:12] == original['registers'][4:12] and
                            r[13] == original['registers'][13] and r[0] == original['registers'][14] and
                            bytes(m[r[13]:r[13]+32]).hex() == original['guard'],
                            'Floor modal failed caller/stack preservation')
                    returns.append({'frame': event['frame'], 'caller_abi_preserved': True})

            if mode:
                write(actor+0x90, bytes([mode]), 'Controlled command mode; class unlocking is not exercised')
            x, y = position(g)
            tile = MAP + (x*32+y)*28
            if kind == 'trap':
                require(m.u16[tile+10] == 0xFFFF and not m.u32[tile+16], 'Expected empty fixture tile')
                write(tile+10, struct.pack('<H', 0), 'Controlled visible trap selector; never activate the trap')
            if condition:
                write(actor+condition, b'\x01', 'Controlled refusal condition; leave native menu dispatch intact')
            before_inventory = None
            with Debugger(g, callback, max_events=150000) as debug:
                for address in set(audit.ADDRESSES) | {0x08017068, 0x080170C4}:
                    debug.breakpoint(address)
                try:
                    if kind == 'item':
                        use(g, 204, 7)  # A naturally carried Big bread, ordinary Drop.
                        require(m.u32[tile+16], 'Native Drop did not leave an item underfoot')
                    if kind == 'inventory':
                        use(g, 204, 11)  # Eat the opening bread through its normal menu.
                        require(not items(g), 'Ordinary Eat did not empty the opening inventory')
                    before_inventory = bytes(m[0x0200DF28:0x0200E888])
                    before_tile = bytes(m[tile:tile+28])
                    baseline = None
                    modal_case = kind in ('empty', 'inventory') or condition is not None
                    for cycle in range(3):
                        audit.phase = f'open-{cycle}'
                        start = len(audit.observer.reads)
                        g.press('B', hold=8, wait=120)
                        for _ in range(0 if kind == 'inventory' else 2 if mode else 1):
                            g.press('DOWN', wait=30)
                        parent = capture(f'parent-{cycle}')
                        parent_background = modal_background(g)
                        g.press('A', wait=120)
                        pic = capture(f'panel-{cycle}')
                        reads = audit.report()['reads'][start:]
                        text = '\n'.join(r['text'] for r in reads)
                        if modal_case:
                            expected = {None: 'There is nothing underfoot.',
                                        0xBF: "Can't do that while transformed.",
                                        0x9C: "You're too frightened to do that.",
                                        0x9A: "You can't do that while dancing."}[condition]
                            if kind == 'inventory':
                                expected = 'You have no items.'
                            if not allow_findings:
                                require(expected in text, 'Floor modal text differs: ' + text)
                            field = reads[-1]
                            require((field['screen_x'], field['screen_y'], field['window_width'], field['rows']) ==
                                    (64, 72, 168, 1), 'Floor modal geometry changed')
                            pixels = pic.crop((60, 68, 236, 92)).tobytes()
                            if baseline is None:
                                baseline = pixels
                            require(pixels == baseline, 'Floor panel changed across reopening')
                        else:
                            expected = {'item': 'Big bread', 'trap': 'Step', 'stairs': 'Descend'}[kind]
                            require(expected in text, 'Floor branch not reached: ' + text)
                        audit.phase = f'dismiss-{cycle}'
                        g.press('B', wait=120)
                        closed = capture(f'dismissed-{cycle}')
                        if modal_case:
                            require(modal_background(g) == parent_background and
                                    all(closed.crop(box).tobytes() == parent.crop(box).tobytes()
                                        for box in ((60, 28, 236, 52), (4, 100, 236, 156))),
                                    'Floor modal did not restore the parent panels')
                        g.press('B', wait=120)  # Return from the restored root menu to gameplay.
                    require(bytes(m[0x0200DF28:0x0200E888]) == before_inventory and
                            bytes(m[tile:tile+28]) == before_tile and g.snapshot().battery == snap.battery,
                            'Cancelled Floor inspection changed inventory/tile/battery')
                    require(len(modals) == len(returns) == (3 if modal_case else 0),
                            'Floor modal opening/return count differs')
                except Exception as exc:
                    error = str(exc)
            capture('end')
            report = {'case': name, 'rom_sha256': digest(rom), 'route_error': error,
                      'fixture_state_sha256': digest(snap.state), 'fixture_battery_sha256': digest(snap.battery),
                      'controlled_overrides': changes, 'inputs': g.inputs, 'captures': captures,
                      'modal_entries': modals, 'modal_returns': returns, **audit.report()}
            report['passed'] = not error and not audit.unclassified and not audit.unreadable and not audit.layout_violations
            save_json(g.output / 'report.json', report)
            results.append(report)
            print(name, 'PASS' if report['passed'] else 'FAIL', error,
                  'Japanese/unknown glyphs:', len(audit.unclassified), flush=True)
    require(all(digest(Path(p).read_bytes()) == sha for p, sha in protected.items()), 'Source files changed')
    receipt = {'passed': all(r['passed'] for r in results), 'rom_sha256': digest(rom),
               'emulator': version(), 'source_hashes': protected, 'source_files_unchanged': True,
               'tools_sha256': {name: digest((ROOT/'tools'/name).read_bytes()) for name in
                                ('verify_floor_menu.py', 'screen_text_audit.py', 'floor_notice_text.py')},
               'cases': results}
    save_json(output / 'report.json', receipt)
    body = ['<!doctype html><meta charset="utf-8"><title>Floor menu audit</title>',
            '<style>body{font:16px system-ui;max-width:1050px;margin:auto;background:#eee}img{width:480px;image-rendering:pixelated}figure{display:inline-block;margin:8px}</style>',
            '<h1>Floor menu audit</h1><p>ROM ' + digest(rom) + '</p>']
    for r in results:
        body.append('<h2>' + html.escape(r['case']) + (' PASS' if r['passed'] else ' FAIL') + '</h2>')
        body.append('<p>' + ('Controlled setup; ordinary menu buttons.' if r['controlled_overrides'] else 'Ordinary gameplay inputs.') + '</p>')
        for label in ('parent-0', 'panel-0', 'dismissed-0', 'panel-2'):
            path = r['case'] + '/' + label + '.png'
            if (output/path).exists():
                body.append(f'<figure><img src="{path}"><figcaption>{label}</figcaption></figure>')
    (output/'index.html').write_text('\n'.join(body))
    require(allow_findings or receipt['passed'], 'Floor-menu audit has unresolved findings')
    return receipt


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=ROOT/'build/english')
    parser.add_argument('--output', type=Path, default=ROOT/'build/floor-menu/native')
    parser.add_argument('--allow-findings', action='store_true')
    args = parser.parse_args()
    run(args.source, args.output, args.allow_findings)
