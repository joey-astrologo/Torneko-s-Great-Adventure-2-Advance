"""Trace the original GBA scrolling-credit bitmap in a disposable native session."""
import json
import mgba.log
from PIL import Image

from tools.emulator import Session, Debugger, ffi
from tools.extract_graphics_audition import credits
from tools.lz77 import decompress
from tools.rom import ROOT, load_base, digest, require

OUT = ROOT / 'build/credits/research'


def run():
    mgba.log.silence()
    rom = load_base()
    decoded, end = decompress(rom, 0x585304)
    manifest, expected_roll = credits(rom)
    prefix = OUT / 'title'
    events, overrides, captures, copies = [], [], [], []
    entered, done, native_decode = [], [], []
    with Session(rom, OUT) as game:
        game.frames(600)
        fixture = game.snapshot()
        fixture.save(prefix)
        m = game.core.memory

        def write(at, data, why):
            before = bytes(m[at:at+len(data)])
            if before == data:
                return
            overrides.append({'frame': game.core.frame_counter, 'address': at,
                              'before_hex': before.hex(), 'after_hex': data.hex(), 'reason': why})
            for i, v in enumerate(data):
                m.u8[at+i] = v

        def jump(event, target, reason):
            overrides.append({'frame': event['frame'], 'pc_before': event['address'],
                              'pc_after': target, 'reason': reason})
            require(game.core._core.writeRegister(game.core._core, b'pc',
                    ffi.new('uint32_t*', target)), 'Credits redirect failed')

        def callback(e):
            a, r = e['address'], e['registers']
            if a == 0x08007814 and not events:
                events.append(e)
                jump(e, 0x08054DA4, 'Controlled entry into the complete ending setup frame from the title frame wait.')
            elif a == 0x08054DF4 and events:
                jump(e, 0x08054EA2, 'Skip the save operation and five story scenes; execute original pre-credits setup.')
            elif a == 0x080554FC:
                entered.append(e | {'guard': bytes(m[r[13]:r[13]+32]).hex()})
            elif a == 0x08055546:
                require(bytes(m[0x020129A8:0x020129A8+len(decoded)]) == decoded,
                        'Native credits BIOS decode differs')
                native_decode.append(e)
                (OUT / 'decoded.bin').write_bytes(decoded)
                write(0x0600B800, b'\0\xf0'*1024, 'Controlled blank credit tile map before the first row upload.')
                write(0x0600C000, bytes(32), 'Controlled transparent tile zero.')
            elif a == 0x08059184 and entered and not done:
                game.core.cpu.gprs[0] = 1
                jump(e, 0x08007814, 'Isolate credit rendering from uninitialized surrounding scene jobs; retain native VBlank wait.')
            elif a == 0x080555A8:
                # Original halfword copier just returned. r7 is the tile slot;
                # the source pointer is retained on this frame's stack.
                source = m.u32[r[13]]
                dest = 0x0600C000 + 32*r[7]
                require(bytes(m[source:source+32]) == bytes(m[dest:dest+32]),
                        'Native credits tile upload differs')
                require(bytes(m[source:source+32]) == decoded[source-0x020129A8:source-0x020129A8+32],
                        'Native credit source buffer changed during playback')
                copies.append({'source': source, 'destination': dest, 'frame': e['frame']})
            elif a == 0x080556A8:
                old = entered[0]
                require(r[4:12] == old['registers'][4:12] and r[13] == old['registers'][13]
                        and bytes(m[r[13]:r[13]+32]).hex() == old['guard'],
                        'Credits renderer ABI/guard differs')
                done.append(e)
            if a == 0x08007814 and native_decode and not done:
                for at in (0x03000A0C, 0x03000C30, 0x04000000):
                    write(at, b'\0\x08', 'Controlled BG3-only display; surrounding scene windows/objects excluded.')
                write(0x04000050, bytes(6), 'Controlled unblended credit layer.')
                write(0x05000000, bytes(2), 'Controlled black backdrop for transparent credit pixels.')

        with Debugger(game, callback, max_events=20000) as debug:
            for a in (0x08007814, 0x08054DF4, 0x080554FC, 0x08055546,
                      0x080555A8, 0x080556A8, 0x08059184):
                debug.breakpoint(a)
            for tick in range(4500):
                if done:
                    break
                game.frames(1)
                if entered and native_decode and (tick % 32 == 0):
                    name = f'frame-{tick:04d}'
                    im = game.capture(name)
                    captures.append({'file': name+'.png', 'frame': game.core.frame_counter,
                                     'rgb_sha256': digest(im.tobytes()),
                                     'dispcnt': m.u16[0x04000000], 'bg3cnt': m.u16[0x0400000E],
                                     'bg3vofs': m.u16[0x0400001E],
                                     'bldcnt': m.u16[0x04000050], 'bldalpha': m.u16[0x04000052],
                                     'bldy': m.u16[0x04000054],
                                     'palette_hex': bytes(m[0x050001E0:0x05000200]).hex()})
            require(len(entered) == len(native_decode) == len(done) == 1,
                    'Controlled credits playback did not finish')
        require(game.snapshot().battery == fixture.battery, 'Credits probe changed battery')
        # Match native frames to the decoded roll without inferring position
        # from write-only GBA scroll registers. Require every visible line to
        # be fully covered by at least one exact 240x160 frame comparison.
        rows = [expected_roll.crop((0, y, 240, y+1)).tobytes() for y in range(expected_roll.height)]
        matched, excluded = [], []
        for capture in captures:
            im = Image.open(OUT/capture['file']).convert('RGB')
            box = im.getbbox()
            positions = []
            if box:
                top = box[1]
                row = im.crop((0, top, 240, top+1)).tobytes()
                positions = [y-top for y, value in enumerate(rows) if value == row
                             and expected_roll.crop((0, y-top, 240, y-top+160)).tobytes() == im.tobytes()]
            if positions:
                matched.append({'file': capture['file'], 'source_top': positions[0], 'pixels_compared': 38400})
            else:
                excluded.append(capture['file'])
        covered = [line['id'] for line in manifest['lines'] if any(
            row['source_top'] <= line['bounds'][1] and row['source_top']+160 >= line['bounds'][3]
            for row in matched)]
        require(len(covered) == 67, 'Native credit frame comparisons do not cover all visible lines')
        expected_tiles = set(range(0x020129A8+7834, 0x020129A8+len(decoded), 32))
        require({c['source'] for c in copies} == expected_tiles, 'Native credit tile-source coverage differs')
        report = {'schema': 1, 'passed': True, 'source_rom_sha256': digest(rom),
                  'compressed_range': [0x585304, end], 'decoded_sha256': digest(decoded),
                  'decoded_bytes': len(decoded), 'fixture_prefix': str(prefix.relative_to(ROOT)),
                  'fixture_state_sha256': digest(fixture.state),
                  'fixture_battery_sha256': digest(fixture.battery), 'inputs': game.inputs,
                  'overrides': overrides, 'entry': entered, 'return': done,
                  'native_decode': native_decode, 'tile_copies': copies, 'captures': captures,
                  'exact_frame_matches': matched, 'fully_covered_lines': covered,
                  'excluded_blank_leadin_or_fade_frames': excluded,
                  'battery_unchanged': True,
                  'scope': 'Controlled ending entry from title, skipping save and five story scenes. Original credit renderer and BIOS decode; scene-update calls replaced by original VBlank waits, with explicit BG3/map/backdrop/blend overrides to isolate the text layer. All 2241 unique source tiles and all67 lines covered by exact full-frame comparisons; renderer ABI and battery unchanged. Initial lead-in/blank/fade frames, natural ending access, unmodified surrounding display behavior and final ending artwork are excluded. Write-only I/O reads are diagnostic bus observations, not reliable scroll/blend values.'}
        report['generator_sha256'] = digest((ROOT/'tools/research_credits.py').read_bytes())
        (OUT / 'report.json').write_text(json.dumps(report, indent=2)+'\n')
    print('Original credits:', len(copies), 'tile uploads;', len(captures), 'native captures')


if __name__ == '__main__':
    run()
