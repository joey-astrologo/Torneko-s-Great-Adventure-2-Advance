"""English custom names through native inventory and storage consumers."""

import argparse
import json
from pathlib import Path
import struct

import mgba.log

from tools.audit_menu_layouts import parent_image
from tools.compact_font import encode, measure
from tools.dialogue_checks import rendered_codes
from tools.emulator import Debugger, Session
from tools.name_entry import IDS
from tools.numeric_checks import NumericChecks
from tools.rom import ROOT, digest, load_base, require
from tools.screen_text_audit import ScreenTextAudit
from tools.verify_items import ItemChecks
from tools.verify_storage import SAVE

ITEMS = (116, 87, 48, 203, 169, 154)


def setup(game, ident, text, priced, count=99, extra_flags=0, storage=False):
    m = game.core.memory
    overrides = []

    def write(at, raw):
        overrides.append({'address': at, 'before': bytes(m[at:at+len(raw)]).hex(),
                          'after': raw.hex()})
        for i, byte in enumerate(raw):
            m.u8[at+i] = byte

    records = bytearray(120*20)
    struct.pack_into('<I', records, 0, 0x80000000 | (0x100000 if priced else 0) | extra_flags)
    records[4], records[5] = count, 1
    records[8] = bytes(m[0x020013D0:0x020014D0]).index(ident)
    write(0x0200DF28, records)
    db = 0x02003BAC + 20*ident
    write(db, struct.pack('<I', m.u32[db] & ~0x40000000))
    write(db+8, b'\1' + bytes(IDS[c] for c in text).ljust(8, b'\1') + b'\0\0')
    if storage:
        write(0x0200F008, bytes(12*250))
    return overrides


def inspect_rows(checks, audit, expected, label):
    rows = []
    for row in audit.observer.reads:
        raw = bytes.fromhex(row['raw_hex'])
        if expected not in raw or encode(label)[:-1] not in raw:
            continue
        colors = rendered_codes(raw, foreground=15, saved=15)
        require(len(colors) == len(row['glyph_positions']), 'Custom row glyph trace differs')
        ink, prices = [], []
        for (code, color), pos in zip(colors, row['glyph_positions']):
            glyph, _ = checks.glyph_record(code)
            edge = max((x+1 for line in glyph['rows'] for x, bit in enumerate(line)
                        if bit == '#'), default=0)
            require(pos['row'] == row['initial_row'], 'Custom item name wrapped')
            require(pos['x'] + glyph['advance'] <= row['window_width'], 'Custom item row exceeds window')
            # Names and prices both use green; inverse-price glyph identity,
            # including its native padding, identifies the price cells.
            if code == 0x8140 or 0x8740 <= code <= 0x8749:
                prices.append(pos['x'])
            elif edge:
                ink.append(pos['x']+edge)
        require(not prices or max(ink) <= min(prices), 'English custom name overlaps price')
        rows.append({'window_width': row['window_width'], 'initial_x': row['initial_x'],
                     'name_right': max(ink), 'price_left': min(prices) if prices else None,
                     'raw_hex': row['raw_hex'], 'single_line': True})
    require(rows, 'Complete English custom row was not observed')
    return rows


def run(source=ROOT/'build/english', only=None):
    mgba.log.silence()
    rom = (source/'torneko-2-english.gba').read_bytes()
    build = json.loads((source/'build.json').read_text())
    require(build['output_sha256'] == digest(rom), 'Custom test ROM differs')
    out = source/'custom-items-validation'
    from tools import verify_player_status_prototype as status
    previous = status.OUT
    try:
        status.OUT = out
        dungeon = status.ready(rom, build)
    finally:
        status.OUT = previous
    battery = SAVE.read_bytes()
    with Session(rom, out/'storage-cold', initial_save=battery) as game:
        game.frames(600)
        game.press('START', wait=180)
        game.press('A', wait=300)
        storage = game.snapshot()
    widest = max(IDS, key=measure)
    text = widest*8
    labels = {r['category']: r['english'] for r in build['custom_items']['entries'] if 'category' in r}
    base = load_base()
    cases = [(f'{context}-{ident}-{priced}', context, ident, priced, 99, 0, text)
             for context in ('inventory', 'storage') for ident in ITEMS for priced in (False, True)]
    cases += [(f'inventory-pot-count-{count}', 'inventory', 154, True, count, 0, text)
              for count in (0, 1, 20)]
    cases += [(f'inventory-ring-{tag}', 'inventory', 87, True, 99, flags, text)
              for tag, flags in (('equipped', 0x800000), ('cursed', 0x04800000))]
    cases += [('inventory-short', 'inventory', 116, False, 1, 0, 'A')]
    results = []
    for name, context, ident, priced, count, flags, entered in cases:
        if only and name != only:
            continue
        print('Custom item', name, flush=True)
        fixture = storage if context == 'storage' else dungeon
        with Session(rom, out/name) as game:
            game.restore(fixture)
            overrides = setup(game, ident, entered, priced, count, flags, context == 'storage')
            c, audit, numbers = ItemChecks(game, build), ScreenTextAudit(game), NumericChecks(game)
            before_name = bytes(game.core.memory[0x02003BAC+20*ident:0x02003BAC+20*ident+20])

            def callback(event):
                audit.callback(event)
                c.callback(event)
                numbers.callback(event)

            with Debugger(game, callback, max_events=250000) as debug:
                for address in set(c.ADDRESSES + audit.ADDRESSES + numbers.ADDRESSES):
                    debug.breakpoint(address)
                if context == 'inventory':
                    game.press('B', hold=8, wait=60)
                    game.press('A', wait=60)
                    game.capture('list')
                    parent = parent_image(game)
                    for opening in range(3):
                        game.press('A', wait=60)
                        game.capture(f'actions-{opening}')
                        game.press('B', wait=60)
                        require(parent_image(game) == parent, 'Custom item parent restoration differs')
                else:
                    # The native storage list has its own item-row reader; the
                    # 100px columns belong to its command menu, not its item names.
                    game.press('A', wait=120)
                    game.press('A', wait=120)
                    game.capture('carried')
                    game.press('R', wait=60)
                    game.capture('marked')
                    game.press('A', wait=120)
                    game.capture('deposited')
                    game.press('A', wait=120)
                    game.press('RIGHT', wait=60)
                    game.press('A', wait=120)
                    game.capture('stored')
                    game.press('A', wait=120)
                    game.capture('withdrawn')
                    require(game.core.memory.u32[0x0200DF28] & 0x80000000, 'Custom item withdrawal failed')
                require(not c.active and not c.stack, 'Incomplete custom item formatter/reader')
            label = labels[base[0x141B9C+ident*24+20]]
            rows = inspect_rows(c, audit, encode(entered)[:-1], label)
            screen = audit.report()
            (game.output/'screen.json').write_text(json.dumps(screen, ensure_ascii=False, indent=2)+'\n')
            require(not audit.unclassified and not audit.unreadable and not audit.layout_violations,
                    'Custom-name screen has untranslated text or layout failures; see screen.json')
            require(before_name == bytes(game.core.memory[0x02003BAC+20*ident:0x02003BAC+20*ident+20]),
                    'Custom name state changed')
            require(game.snapshot().battery == fixture.battery, 'Custom item probe changed battery')
            results.append({'case': name, 'context': context, 'item': ident, 'name': entered,
                            'overrides': overrides, 'inputs': game.inputs, 'rows': rows,
                            'formats': c.formats, 'glyph_checks': c.glyph_checks,
                            'numeric_checks': numbers.samples, 'battery_unchanged': True,
                            'fixture_state_sha256': digest(fixture.state),
                            'captures': {p.name: digest(p.read_bytes()) for p in game.output.glob('*.png')}})
            (out/'partial.json').write_text(json.dumps(results, ensure_ascii=False, indent=2)+'\n')
    require(digest(SAVE.read_bytes()) == digest(battery), 'Original storage save changed')
    report = {'passed': True, 'rom_sha256': digest(rom), 'cases': results,
              'widest_selectable_english_character': widest, 'character_advance': measure(widest),
              'source_rom_sha256': digest(base), 'storage_save_sha256': digest(battery),
              'scope': 'Controlled custom-name/item flags and quantities; ordinary inventory and storage inputs. '
                       'Six custom-name categories, widest eight-character English names, one-character name, '
                       'prices, ring markers, pot counts, repeated action opening and storage round trips. '
                       'Count99 is a synthetic formatting bound. Japanese-name width is outside layout acceptance.'}
    (out/('report.json' if not only else 'single-report.json')).write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
    print('Custom items:', len(results), 'passed')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=ROOT/'build/english')
    parser.add_argument('--only')
    args = parser.parse_args()
    run(args.source, args.only)
