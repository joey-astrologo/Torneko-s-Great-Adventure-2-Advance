"""Native English arrival cards: fresh entry, all selectors, uploads and return."""
import argparse
import html
import json
import struct
from pathlib import Path

import mgba.log
from PIL import Image, ImageChops

from tools.arrival_art import font_data, measure, inserted_atlas
from tools.emulator import BIOS, Debugger, Session, Snapshot, version
from tools.dialogue_checks import TextChecks
from tools.extract_graphics_audition import arrivals, save_json
from tools.name_entry_route import NameEntryRoute
from tools.name_entry_playtest import position
from tools.rom import ROOT, default_rom, digest, load_base, require
from tools.verify_name_entry import open_editor

OUT = ROOT/'build/arrival-cards/inserted'
CASES = [(i, 1) for i in range(13)]+[(8, f) for f in range(2, 11)]+[(8, f) for f in (99, 100, 999)]+[(11, f) for f in (10, 99, 999)]+[(12, 10), (12, 11)]


def departure(rom, build, output):
    prefix = output/'fixture/departure'
    provenance = output/'fixture/inputs.json'
    if prefix.with_suffix('.json').exists() and provenance.exists():
        saved = Snapshot.load(prefix)
        if saved.rom_sha256 == digest(rom):
            return saved
    last = next(r['rom_offset']+0x08000000 for r in build['dialogue']['entries'] if r['id'] == 'event-bank-0.12c6')
    with Session(rom, prefix.parent) as g:
        seen, early = [], []
        def callback(e):
            if e['address'] == 0x080021B4 and e['registers'][1] == last:
                seen.append(e)
            if e['address'] == 0x08005C6C:
                early.append(e)
        with Debugger(g, callback, max_events=2000) as d:
            d.breakpoint(0x080021B4);d.breakpoint(0x08005C6C)
            open_editor(g)
            editor = NameEntryRoute(g, build['name_entry']['keyboard_pages'])
            editor.clear();editor.enter('Torneko');editor.confirm()
            for _ in range(160):
                g.press('A', wait=240)
                if seen:
                    break
            require(len(seen) == 1 and not early, 'Fresh departure checkpoint differs')
        g.capture('departure')
        snap = g.snapshot();snap.save(prefix)
        save_json(provenance, {'rom_sha256': digest(rom), 'inputs': g.inputs,
                              'state_sha256': digest(snap.state), 'battery_sha256': digest(snap.battery),
                              'controlled_overrides': [], 'scope': 'Cold fresh save, ordinary editor/opening inputs, before the first arrival.'})
        return snap


def wanted_calls(art, ident, floor):
    if ident == 12 and floor > 10:
        return []
    table = art['descriptors_offset']
    calls = [(8, 10, table+192)] if ident == 12 else []
    field = f'{floor:3d}'
    for i in range(1 if ident == 12 else 0, 3):
        if field[i] != ' ':
            calls.append((16+i*2, 10, table+int(field[i])*8))
    if ident != 12:
        calls.append((22, 10, table+80))
    width = art['entries'][ident]['source_rect_tiles'][2]
    return calls+[((30-width)//2, 4, table+88+ident*8)]


def reference_pixels(art, ident, floor, font, original_floor):
    """Independent screen-space glyph placement, without decoding inserted tiles."""
    picture = Image.new('RGB', (240, 160))
    if ident == 12 and floor > 10:
        return picture
    def text(value, x, baseline):
        for ch in value:
            g = font['glyphs'][ch]
            for y, row in enumerate(g['rows']):
                for dx, bit in enumerate(row):
                    if bit == '3':
                        picture.putpixel((x+dx, baseline+g['top']+y), (255, 255, 255))
            x += g['advance']
    value = art['entries'][ident]['english']
    text(value, (240-measure(font, value))//2, 52)
    if ident == 12:
        text('Level', 64, 97)
    field = f'{floor:3d}'
    for i in range(1 if ident == 12 else 0, 3):
        if field[i] != ' ':
            picture.paste(original_floor[field[i]], (128+i*16, 80))
    if ident != 12:
        picture.paste(original_floor['F'], (176, 80))
    return picture


def check_vram(rom, art, calls, before, actual, counter):
    expected = bytearray(before)
    tile = 1
    for dx, dy, at in calls:
        x, y, w, h = struct.unpack_from('<4h', rom, at)
        require(0 <= x < 28 and x+w <= 28 and 0 <= y < 75 and y+h <= 75,
                'Selected English rectangle leaves atlas')
        for row in range(h):
            source = art['atlas_offset']+((y+row)*28+x)*32
            target = 0xC000+tile*32
            expected[target:target+w*32] = rom[source:source+w*32]
            for col in range(w):
                struct.pack_into('<H', expected, 0xB800+((dy+row)*32+dx+col)*2, 0xF000+tile+col)
            tile += w
    require(tile <= 512 and counter == tile, 'Native tile counter/capacity differs')
    require(bytes(expected) == actual, 'Native atlas upload, tile map or surrounding VRAM differs')
    return tile-1


def run(source, only=None):
    mgba.log.silence()
    rom = (source/'torneko-2-english.gba').read_bytes()
    build = json.loads((source/'build.json').read_text())
    require(digest(rom) == build['output_sha256'] and build['arrival_cards'], 'Arrival build differs')
    art = build['arrival_cards']
    source_save = default_rom().with_suffix('.sav');save_hash = digest(source_save.read_bytes())
    fixture = departure(rom, build, OUT)
    _, font = font_data()
    _, _, _, floors = arrivals(load_base())
    original_report = ROOT/'build/arrival-cards/native/report.json'
    original_checks = json.loads(original_report.read_text())
    require(original_checks['passed'] and original_checks['source_rom_sha256'] == digest(load_base()), 'Original palette reference differs')
    conversion = {}
    for case in original_checks['cases']:
        for row in case['observed_palette_conversion']:
            key, value = tuple(row['stored_rgb']), tuple(row['native_rgb'])
            require(key not in conversion or conversion[key] == value, 'Original fade observations disagree')
            conversion[key] = value
    inserted_atlas(rom, art).save(OUT/'english-atlas.png')
    results = []
    help_row = next(r for r in build['dialogue']['entries'] if r['id'] == 'rom.0006b0e8')
    help_at = help_row['rom_offset']+0x08000000
    for ident, floor in CASES:
        case_id = f'{ident:02}-floor-{floor:03}'
        if only and not case_id.startswith(only):
            continue
        output = OUT/case_id
        natural = (ident, floor) == (11, 1)
        with Session(rom, output) as g:
            g.restore(fixture);m = g.core.memory
            help_check = TextChecks(g, {help_at: help_row}) if natural else None
            entries, calls, ready, returned, overrides, copies, help_seen = [], [], [], [], [], [], []
            compositor = {}
            def write(at, data, reason):
                before = bytes(m[at:at+len(data)])
                if before != data:
                    overrides.append({'address': at, 'before_hex': before.hex(), 'after_hex': data.hex(), 'reason': reason, 'frame': g.core.frame_counter})
                    for i, v in enumerate(data):m.u8[at+i] = v
            def callback(e):
                a, r = e['address'], e['registers']
                if help_check and a in help_check.ADDRESSES:
                    help_check.callback(e)
                if a == 0x080021B4 and r[1] == help_at:
                    help_seen.append(e)
                if a == 0x08005C6C and not entries:
                    entries.append(e | {'guard_hex': bytes(m[r[13]:r[13]+32]).hex(),
                                        'selector': m.u32[0x02003B6C], 'floor': m.u16[0x02005674]})
                    require(r[14] & ~1 == 0x08004D66, 'Arrival caller changed')
                    require((entries[0]['selector'], entries[0]['floor']) == (11, 1), 'Fresh entry fields differ')
                    if not natural:
                        write(0x02003B6C, struct.pack('<I', ident), 'Controlled selector at original controller entry')
                        write(0x02005674, struct.pack('<H', floor), 'Controlled floor at original controller entry')
                if not entries or returned:
                    return
                if a == 0x08005B6C:
                    require(not compositor, 'Repeated compositor entry')
                    compositor.update(regs=r, vram=bytes(m[0x06000000:0x06018000]), guard=bytes(m[r[13]:r[13]+32]))
                elif a == 0x08005AC8:
                    calls.append((r[0], r[1], r[2]-0x08000000))
                elif a == 0x08005C52:
                    wanted = wanted_calls(art, ident, floor)
                    require(calls == wanted, 'Native descriptor selections differ')
                    tiles = check_vram(rom, art, wanted, compositor['vram'], bytes(m[0x06000000:0x06018000]), m.u16[0x020015A4])
                    copies.append({'tiles': tiles, 'vram_bytes_checked': 0x18000,
                                   'before_sha256': digest(compositor['vram']), 'after_sha256': digest(bytes(m[0x06000000:0x06018000]))})
                elif a == 0x08005CFA:
                    old = compositor['regs']
                    require(r[4:12] == old[4:12] and r[13] == old[13] and bytes(m[r[13]:r[13]+32]) == compositor['guard'], 'Compositor caller ABI/guard differs')
                elif a == 0x08005D0A:
                    ready.append(e)
                elif a == 0x08004D66:
                    old = entries[0]
                    require(r[4:12] == old['registers'][4:12] and r[13] == old['registers'][13] and bytes(m[r[13]:r[13]+32]).hex() == old['guard_hex'], 'Arrival controller ABI/guard differs')
                    returned.append(e)
                    if not natural:
                        write(0x02003B6C, struct.pack('<I', old['selector']), 'Restore native selector before caller resumes')
                        write(0x02005674, struct.pack('<H', old['floor']), 'Restore native floor before caller resumes')
            with Debugger(g, callback, max_events=10000) as d:
                addresses = {0x08005C6C, 0x08005B6C, 0x08005AC8, 0x08005C52, 0x08005CFA, 0x08005D0A, 0x08004D66, 0x080021B4}
                if help_check:addresses.update(help_check.ADDRESSES)
                for at in addresses:d.breakpoint(at)
                g.press('A', hold=3, wait=0)
                for _ in range(900):
                    g.frames(1)
                    if ready and g.core.frame_counter >= ready[0]['frame']+3:
                        break
                require(len(entries) == len(ready) == len(copies) == 1 and not returned, 'Visible arrival was not reached')
                actual = g.capture('card')
                expected = reference_pixels(art, ident, floor, font, floors)
                expected.save(output/'expected-stored-palette.png')
                expected.putdata([conversion[p] for p in expected.get_flattened_data()])
                expected.save(output/'expected-native.png')
                difference = ImageChops.difference(actual, expected)
                if difference.getbbox():difference.save(output/'difference.png')
                require(actual.tobytes() == expected.tobytes(), 'Native English card pixels differ: '+case_id)
                for _ in range(300):
                    g.frames(1)
                    if returned:break
                require(len(returned) == 1, 'Arrival did not complete its original fade/return')
                g.capture('after-return')
                movement = None
                if natural:
                    for _ in range(600):
                        if help_seen:break
                        g.frames(1)
                    require(help_seen, 'Native arrival did not continue into English tutorial')
                    g.frames(120);g.capture('tutorial')
                    for _ in range(8):
                        if help_check.completed(help_row['id']):break
                        g.press('A', wait=240)
                    require(help_check.completed(help_row['id']) and help_check.active is None, 'Post-arrival English tutorial pages did not finish')
                    g.press('A', wait=120)
                    before = position(g)
                    for direction in ('RIGHT', 'DOWN', 'LEFT', 'UP'):
                        g.press(direction, wait=30)
                        if position(g) != before:break
                    require(position(g) != before, 'No ordinary movement after inserted arrival')
                    movement = {'before': before, 'after': position(g), 'tutorial_glyph_checks': help_check.glyph_checks}
                    g.capture('movement')
            require(g.snapshot().battery == fixture.battery, 'Arrival validation changed battery')
            results.append({'id': case_id, 'selector': ident, 'floor': floor, 'natural_fields_and_inputs': natural,
                            'english': art['entries'][ident]['english'], 'inputs': g.inputs, 'overrides': overrides,
                            'calls': calls, 'entries': entries, 'ready': ready, 'returned': returned,
                            'vram_checks': copies, 'abi_and_stack_guard_preserved': True,
                            'pixels_compared': 38400, 'png_sha256': digest((output/'card.png').read_bytes()),
                            'rgb_sha256': digest(actual.tobytes()), 'battery_unchanged': True, 'movement': movement})
        save_json(OUT/'partial.json', results)
        print('English arrival', case_id, 'pixels, VRAM, fade and return passed', flush=True)
    require(digest(source_save.read_bytes()) == save_hash, 'Supplied save changed')
    report = {'schema': 1, 'passed': True, 'complete_matrix': only is None,
              'rom_sha256': digest(rom), 'source_rom_sha256': digest(load_base()), 'source_save_sha256': save_hash,
              'generator_sha256': digest(Path(__file__).read_bytes()), 'emulator': version(), 'bios': BIOS,
              'fixture_state_sha256': digest(fixture.state), 'fixture_battery_sha256': digest(fixture.battery),
              'fixture_inputs_sha256': digest((OUT/'fixture/inputs.json').read_bytes()),
              'original_palette_report_sha256': digest(original_report.read_bytes()),
              'palette_conversion': [{'stored_rgb': k, 'native_rgb': v} for k, v in conversion.items()],
              'cases': results, 'scope': 'Actual patched-ROM native controller and compositor, 30 cases: 13 names, every digit, ordinary 1/2/3-digit boundaries, widest-card maximum upload and Well suppression. Exact full-screen pixels at the established step1 fade, all 96KiB VRAM checked during composition, full fade/return and ABI/stack guards. Fresh ordinary opening/meadow/tutorial/movement for ID11/floor1; other selectors/floors are temporary controlled probes restored before caller resumes. No natural late-dungeon unlock/progression or full-game coverage claim.'}
    save_json(OUT/('report.json' if only is None else 'focused-report.json'), report)
    if only is None:gallery(report)
    return report


def gallery(report):
    cards = []
    for row in report['cases']:
        ident = row['id']
        status = 'Ordinary opening route' if row['natural_fields_and_inputs'] else 'Controlled selector/floor · native renderer'
        cards.append(f'<article><h2>{html.escape(row["english"])} · {row["floor"]}</h2><img src="{ident}/card.png" alt="Native English arrival"><p>{status}</p><p>38,400 pixels match · uploads/return pass</p></article>')
    (OUT/'index.html').write_text('''<!doctype html><html lang="en"><meta charset="utf-8"><title>Torneko 2 · inserted arrival cards</title>
<style>body{font:16px/1.5 system-ui;background:#111923;color:#e6eef4;max-width:1500px;margin:40px auto;padding:24px}a{color:#91decb}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:20px}article{padding:16px;background:#1b2734}h2{font-size:17px}img{width:100%;max-width:480px;image-rendering:pixelated}p{color:#b6c6d5}code{overflow-wrap:anywhere}</style>
<h1>Inserted English arrival cards · native mGBA</h1><p>All 13 location names, retained original floor digits/F, English Level, and the widened Ordeal Mansion.
These screenshots come from the patched ROM. Every case completed its original fade and return.</p><p>Only Mysterious Meadow 1F uses an ordinary fresh-game route. Other cards use recorded temporary selector/floor overrides at the native controller entry; natural late-game access remains untested.</p>
<p><a href="../../torneko-2-english.gba">Latest English ROM</a> · <a href="../../torneko-2-english.bps">BPS patch</a> · <a href="report.json">Native report</a> · <a href="../../../docs/ARRIVAL_INSERTION.md">Insertion and validation notes</a></p>
<p>Verified ROM SHA-256: <code>'''+report['rom_sha256']+'</code></p><div class="grid">'+''.join(cards)+'</div></html>')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=ROOT/'build/english')
    parser.add_argument('--only')
    args = parser.parse_args();run(args.source.resolve(), args.only)
