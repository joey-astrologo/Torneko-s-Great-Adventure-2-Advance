"""Decode every full-screen background record and check its native uploads.

This covers the 22-record table owned by 08004240, including its optional
foreground layer. Town tile maps, sprites and other scene loaders are separate.
Controlled calls establish loader behavior, not ordinary scene reachability.
"""
import argparse
import html
import json
from pathlib import Path
import struct

import mgba.log
from PIL import Image, ImageDraw

from tools.emulator import Debugger, Session, ffi
from tools.rom import ROOT, default_rom, digest, load_base, require
from tools.title_art import SOURCES, TABLE
from tools.trace_graphics_sources import GraphicsTrace, tiled_image

BASE = 0x08000000
COUNT = 22


def records(rom):
    require(rom[TABLE+COUNT*20:TABLE+COUNT*20+8] == b'AGB-TORU',
            'Reinspect background descriptor boundary')
    rows = []
    for index in range(COUNT):
        at = TABLE+index*20
        source, mapping, tiles, size, colors, gamma = struct.unpack_from('<IIIHHi', rom, at)
        require(BASE <= source <= BASE+len(rom)-38912 and colors in (240, 256),
                'Background resource or palette outside verified shape')
        require(bool(mapping) == bool(tiles) == bool(size), 'Partial foreground descriptor')
        source -= BASE
        row = dict(index=index, record_range=[at, at+20], record_hex=rom[at:at+20].hex(),
                   resource_range=[source, source+38912], resource_sha256=digest(rom[source:source+38912]),
                   palette_colors=colors, gamma=gamma)
        if mapping:
            mapping -= BASE
            tiles -= BASE
            require(0 <= mapping <= len(rom)-600 and 0 <= tiles <= len(rom)-size
                    and size % 64 == 0 and max(rom[mapping:mapping+600])*64+64 <= size,
                    'Foreground map addresses an unowned tile')
            row['foreground'] = dict(map_range=[mapping, mapping+600], tile_range=[tiles, tiles+size],
                map_sha256=digest(rom[mapping:mapping+600]), tile_sha256=digest(rom[tiles:tiles+size]))
        rows.append(row)
    return rows


def decode(rom, row, palette=None):
    at = row['resource_range'][0]
    palette = palette or rom[at:at+512]
    background = tiled_image(rom[at+512:at+38912], palette, 240, 160, 8)
    foreground = None
    if row.get('foreground'):
        f = row['foreground']
        lo, hi = f['map_range']
        tiles = f['tile_range'][0]
        selected = b''.join(rom[tiles+v*64:tiles+(v+1)*64] for v in rom[lo:hi])
        foreground = tiled_image(selected, palette, 240, 160, 8)
    return background, foreground


def native(rom, rows, output):
    cases, covered = [], set()
    with Session(rom, output) as g:
        g.frames(600)
        snapshot = g.snapshot()
        for request in list(range(COUNT)) + [13]*32:
            if request == 13 and covered == set(range(COUNT)):
                break
            print('Native background request', request, 'case', len(cases), flush=True)
            # Vary only the elapsed native frames for repeated random requests.
            g.restore(snapshot)
            delay = max(0, len(cases)-COUNT+1)
            if delay:
                g.frames(delay)
            cpu, m = g.core.cpu, g.core.memory
            before = [int(v) & 0xffffffff for v in cpu.gprs]
            sentinels = [0x23450000+i for i in range(4, 12)]
            for i, value in enumerate(sentinels, 4):
                cpu.gprs[i] = value
            cpu.gprs[0], cpu.gprs[14] = request, 0x08000355
            for name, value in ((b'cpsr', int(cpu.cpsr.packed) | 0x20), (b'pc', 0x08004240)):
                require(g.core._core.writeRegister(g.core._core, name, ffi.new('uint32_t*', value)),
                        'Background probe register write failed')
            observer = GraphicsTrace(g, rom)
            with Debugger(g, observer.callback) as trace:
                for address in GraphicsTrace.ADDRESSES[:5]:
                    trace.breakpoint(address)
                trace.run_until(lambda _: bool(observer.backgrounds), max_steps=1000000)
                result = trace.events[-1]['registers']
            require(result[4:12] == sentinels and result[13] == before[13], 'Background loader ABI differs')
            selected = observer.backgrounds[-1]['index']
            require(selected == request if request != 13 else selected in (13,18,19,20,21),
                    'Background selector differs')
            row = rows[selected]
            at = row['resource_range'][0]
            require(bytes(m[0x06000000:0x06009600]) == rom[at+512:at+38912], 'Background tiles differ')
            for y in range(20):
                require([m.u16[0x0600B000+y*64+x*2] for x in range(30)] == list(range(y*30,y*30+30)),
                        'Background map differs')
            if row.get('foreground'):
                f = row['foreground']
                lo, hi = f['tile_range']
                dest = struct.unpack_from('<I', rom, 0x4390)[0]
                require(bytes(m[dest:dest+hi-lo]) == rom[lo:hi], 'Foreground tiles differ')
                dest = struct.unpack_from('<I', rom, 0x4394)[0]
                lo = f['map_range'][0]
                for y in range(20):
                    require([m.u16[dest+y*64+x*2] for x in range(30)] == list(rom[lo+y*30:lo+(y+1)*30]),
                            'Foreground map differs')
            palette = bytes(m[0x02001064:0x02001264])
            for layer, picture in zip(('background', 'foreground'), decode(rom, row, palette)):
                if picture:
                    picture.save(output/f'{selected:02}-{layer}.png')
            require(g.snapshot().battery == snapshot.battery, 'Graphics loader changed battery')
            covered.add(selected)
            cases.append(dict(request=request, delay_frames=delay, selected=selected,
                controlled_registers=dict(r0=request, lr=0x08000355, pc=0x08004240,
                                          r4_r11=sentinels, original_registers=before),
                callee_saved_and_sp_preserved=True, tile_and_map_uploads_match=True,
                battery_unchanged=True, native_loader=observer.backgrounds[-1],
                calibrated_palette_sha256=digest(palette)))
        require(covered == set(range(COUNT)), 'Not all native background records selected')
        g.restore(snapshot)
        require(g.snapshot().battery == snapshot.battery, 'Snapshot restoration changed battery')
        return dict(cases=cases, inputs=g.inputs, snapshot_state_sha256=digest(snapshot.state),
                    snapshot_battery_sha256=digest(snapshot.battery), covered_records=sorted(covered))


def run(source, output):
    mgba.log.silence()
    original = load_base()
    save = default_rom().with_suffix('.sav')
    save_sha = digest(save.read_bytes())
    rom = (source/'torneko-2-english.gba').read_bytes()
    build = json.loads((source/'build.json').read_text())
    require(digest(rom) == build['output_sha256'], 'Background audit ROM/ledger mismatch')
    old, current = records(original), records(rom)
    output.mkdir(parents=True, exist_ok=True)
    for a, b in zip(old, current):
        require(a == b if a['index'] not in SOURCES else a['record_hex'][8:] == b['record_hex'][8:],
                'Unrelated background descriptor or source changed')
    for name, data, rows in (('original', original, old), ('compiled', rom, current)):
        folder = output/name
        folder.mkdir(exist_ok=True)
        sheet = Image.new('RGB', (960, 1104), '#ddd')
        draw = ImageDraw.Draw(sheet)
        for row in rows:
            index = row['index']
            for layer, picture in zip(('background', 'foreground'), decode(data, row)):
                if picture:
                    picture.save(folder/f'{index:02}-{layer}.png')
                    if layer == 'background':
                        x, y = index % 4*240, index//4*184
                        sheet.paste(picture, (x,y+24))
                        draw.text((x+4,y+5), f'Record {index}', fill='black')
        sheet.save(folder/'backgrounds.png')
    native_report = native(rom, current, output/'native')
    require(digest(load_base()) == digest(original) and digest(save.read_bytes()) == save_sha,
            'Original ROM/save changed')
    report = dict(passed=True, source_rom_sha256=digest(original), rom_sha256=digest(rom),
        source_save_sha256=save_sha, source_files_unchanged=True,
        tool_sha256=digest(Path(__file__).read_bytes()), address_space='ROM file offsets; exclusive ranges',
        table_range=[TABLE, TABLE+COUNT*20], records=current, original_records=old,
        unique_backgrounds=len({r['resource_sha256'] for r in old}),
        foreground_records=sum('foreground' in r for r in old),
        native=native_report, scope=__doc__,
        visual_review='Separate human/model inspection; upload equality does not automatically classify lettering.')
    (output/'report.json').write_text(json.dumps(report, indent=2)+'\n')
    cards=[]
    for row in current:
        index=row['index']
        cards.append(f'<h2>Record {index}</h2>'+''.join(
            f'<figure><figcaption>{html.escape(label)}</figcaption><img src="{path}"></figure>'
            for label,path in [('Original base',f'original/{index:02}-background.png'),
                               ('Current native palette',f'native/{index:02}-background.png')]+
                              ([('Foreground',f'native/{index:02}-foreground.png')] if row.get('foreground') else [])))
    (output/'index.html').write_text('<!doctype html><meta charset="utf-8"><title>Scene backgrounds</title>'
        '<style>body{font:16px system-ui;background:#18222b;color:white}figure{display:inline-block;margin:12px}'
        'img{width:480px;image-rendering:pixelated}a{color:#9df}</style><h1>Full-screen background audit</h1>'
        '<p>22 controlled native loader selections. Decoded layers, not full scene captures. '
        'Town tile maps and sprites are separate.</p><a href="report.json">Evidence</a>'+''.join(cards))
    print('Background audit: 22 native records, 19 unique bases, 9 foreground records passed')
    return report


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=ROOT/'build/english')
    parser.add_argument('--output', type=Path, default=ROOT/'build/graphics-discovery/backgrounds')
    args=parser.parse_args()
    run(args.source, args.output)
