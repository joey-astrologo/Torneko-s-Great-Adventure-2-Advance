"""Controlled native arrival selectors, floor formats and source/pixel comparison."""
import json
import struct

import mgba.log
from PIL import Image

from tools.emulator import Debugger, Session, Snapshot
from tools.extract_graphics_audition import arrivals, rectangle, save_json
from tools.rom import ROOT, load_base, digest, require

OUT = ROOT/'build/arrival-cards/native'


def pieces(ident, floor):
    if ident == 12 and floor > 10:
        return []
    out = [(8, 10, 0x13EEC0)] if ident == 12 else []
    digits = f'{floor:3d}'
    for i in range(1 if ident == 12 else 0, 3):
        if digits[i] != ' ':
            out.append((16+2*i, 10, 0x13EE00+8*int(digits[i])))
    if ident != 12:
        out.append((22, 10, 0x13EE50))
    return out


def compose(rom, atlas, ident, floor):
    im = Image.new('RGB', (240, 160))
    calls = pieces(ident, floor)
    if ident != 12 or floor <= 10:
        x, y, w, h = rectangle(rom, 0x13EE58+8*ident)
        calls.append(((30-w)//2, 4, 0x13EE58+8*ident))
    for dx, dy, at in calls:
        x, y, w, h = rectangle(rom, at)
        im.paste(atlas.crop((8*x, 8*y, 8*(x+w), 8*(y+h))), (8*dx, 8*dy))
    return im, calls


def run():
    mgba.log.silence()
    rom = load_base()
    manifest, atlas, _, _ = arrivals(rom)
    prefix = ROOT/'build/arrival-research/first-dungeon/departure'
    fixture = Snapshot.load(prefix)
    cases = [(i, 1) for i in range(13)]+[(11, f) for f in (10, 99, 999)]+[(12, 10), (12, 11)]
    results = []
    for ident, floor in cases:
        name = f'{ident:02}-floor-{floor:03}'
        out = OUT/name
        with Session(rom, out) as g:
            g.restore(fixture)
            m = g.core.memory
            entered, calls, ready, overrides = [], [], [], []

            def callback(e):
                a, r = e['address'], e['registers']
                if a == 0x08005C6C and not entered:
                    entered.append(e)
                    for at, raw in ((0x02003B6C, struct.pack('<I', ident)),
                                    (0x02005674, struct.pack('<H', floor))):
                        overrides.append({'address': at, 'before_hex': bytes(m[at:at+len(raw)]).hex(),
                                          'after_hex': raw.hex(), 'frame': e['frame']})
                        for j, v in enumerate(raw):
                            m.u8[at+j] = v
                elif a == 0x08005AC8 and entered:
                    calls.append((r[0], r[1], r[2]-0x08000000))
                elif a == 0x08005D0A and entered:
                    ready.append(e['frame'])

            with Debugger(g, callback, max_events=2000) as debug:
                for a in (0x08005C6C, 0x08005AC8, 0x08005D0A):
                    debug.breakpoint(a)
                g.press('A', hold=3, wait=0)
                for _ in range(600):
                    g.frames(1)
                    if ready and g.core.frame_counter >= ready[0]+3:
                        break
                require(len(entered) == len(ready) == 1, 'Arrival renderer not reached')
                actual = g.capture('card')
                expected, wanted = compose(rom, atlas, ident, floor)
                expected.save(out/'reconstructed.png')
                require(calls == wanted, 'Native arrival rectangle selection differs')
                # The controller's fade stops at brightness step1, rather than
                # displaying the unblended stored palette. Check every pixel
                # against a consistent measured palette conversion, keeping
                # that observation separate from a palette/fade model.
                conversion = {}
                for source, shown in zip(expected.get_flattened_data(), actual.get_flattened_data(), strict=True):
                    require(source not in conversion or conversion[source] == shown,
                            'Native arrival pixel topology differs: '+name)
                    conversion[source] = shown
                require(conversion.get((0, 0, 0)) == (0, 0, 0), 'Arrival backdrop differs')
                require(all((source == (0, 0, 0)) == (shown == (0, 0, 0))
                            for source, shown in conversion.items()), 'Arrival visible ink differs')
            require(g.snapshot().battery == fixture.battery, 'Arrival probe changed battery')
            results.append({'id': name, 'selector': ident, 'floor': floor, 'inputs': g.inputs,
                            'overrides': overrides, 'calls': calls, 'ready_frames': ready,
                            'png_sha256': digest((out/'card.png').read_bytes()),
                            'rgb_sha256': digest(actual.tobytes()), 'pixels_compared': 38400})
            results[-1]['observed_palette_conversion'] = [{'stored_rgb': a, 'native_rgb': b}
                                                          for a, b in conversion.items()]
        print('Arrival', name, 'matches native pixels', flush=True)
    save_json(OUT/'report.json', {'schema': 1, 'passed': True, 'source_rom_sha256': digest(rom),
                                'fixture_prefix': str(prefix.relative_to(ROOT)),
                                'fixture_state_sha256': digest(fixture.state),
                                'fixture_battery_sha256': digest(fixture.battery),
                                'cases': results, 'scope': 'Original arrival controller, controlled dungeon/floor fields at its native entry. All 13 location selectors plus 1/2/3-digit ordinary floors and well levels10/11. Exact source rectangles and all screen pixels under the recorded observed palette conversion; source RGB is brighter than the native step1 fade. Only ID11 floor1 follows the original fixture fields; no ordinary reachability claim for other selectors.'})


if __name__ == '__main__':
    run()
