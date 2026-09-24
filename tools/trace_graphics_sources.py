"""Identify title/background assets and the first dungeon's native arrival card."""

import json
import struct

import mgba.log
from PIL import Image

from tools.emulator import Debugger, Session, Snapshot
from tools.opening_text import BANK_RAM
from tools.rom import ROOT, default_rom, digest, load_base, require

OUTPUT = ROOT / 'build/graphics-research'
ARRIVAL = ROOT / 'build/arrival-research/first-dungeon'
BACKGROUND_TABLE = 0x13EC14
ATLAS = 0x54E784


def tiled_image(data, palette, width, height, bpp):
    require(bpp in (4, 8) and width % 8 == height % 8 == 0, 'Unsupported tile shape')
    require(len(data) == width * height * bpp // 8, 'Tile extent differs')
    colors = []
    for at in range(0, len(palette), 2):
        value = int.from_bytes(palette[at:at + 2], 'little')
        channels = [(value >> shift) & 31 for shift in (0, 5, 10)]
        colors.append(tuple((c << 3) | (c >> 2) for c in channels))
    image = Image.new('RGB', (width, height))
    pixels = image.load()
    for y in range(height):
        for x in range(width):
            tile = y // 8 * (width // 8) + x // 8
            pixel = (y % 8) * 8 + x % 8
            code = data[tile * 64 + pixel] if bpp == 8 else (data[tile * 32 + pixel // 2] >> (pixel % 2 * 4)) & 15
            pixels[x, y] = colors[code]
    return image


class GraphicsTrace:
    ADDRESSES = (0x08004240, 0x080042D6, 0x080042DA, 0x080042F0,
                 0x08004370, 0x08000F8C, 0x08000FA0, 0x08005AC8, 0x08005C6C)

    def __init__(self, game, original):
        self.game, self.original = game, original
        self.backgrounds, self.copies, self.rectangles, self.cards = [], [], [], []
        self.background, self.copy, self.palette = None, None, None

    def callback(self, event):
        r, a, m = event['registers'], event['address'], self.game.core.memory
        if a == 0x08004240:
            self.background = {'requested_index': r[0], 'frame': event['frame'], 'preserved': (r[4:12], r[13])}
        elif a == 0x080042D6:
            require(self.background is not None and 0 < r[2] <= 256, 'Unexpected background palette')
            self.palette = r[0], r[2] * 2
            self.background.update(palette_source=r[1], palette_count=r[2], palette_buffer=r[0],
                                   calibration_mode=m.u16[0x03000A0E],
                                   original_palette_sha256=digest(bytes(m[r[1]:r[1] + r[2] * 2])))
        elif a == 0x080042DA:
            start, size = self.palette
            self.background['converted_palette_sha256'] = digest(bytes(m[start:start + size]))
        elif a == 0x080042F0:
            offset = r[6] - 0x08000000
            require((offset - BACKGROUND_TABLE) % 20 == 0, 'Background record alignment differs')
            source = struct.unpack_from('<I', self.original, offset)[0]
            require(r[0] == 0x06000000 and r[1] == source + 512 and r[2] == 38400, 'Background transfer differs')
            self.background.update(index=(offset - BACKGROUND_TABLE) // 20, record_offset=offset,
                                   record_hex=self.original[offset:offset + 20].hex(),
                                   resource_offset=source - 0x08000000,
                                   resource_end_exclusive=source - 0x08000000 + 512 + 38400)
        elif a == 0x08004370:
            require(self.background.pop('preserved') == (r[4:12], r[13]), 'Background loader changed preserved registers/SP')
            self.background['callee_saved_and_sp_preserved'] = True
            self.backgrounds.append(self.background)
            self.background = None
        elif a == 0x08000F8C:
            require(self.copy is None, 'Nested leaf copy')
            if 0x08000000 <= r[1] < 0x08000000 + len(self.original) and 0x05000000 <= r[0] < 0x06018000:
                require(r[1] + r[2] <= 0x08000000 + len(self.original) and 0 < r[2] <= 0x18000, 'Graphics copy exceeds source')
                self.copy = {'frame': event['frame'], 'source': r[1], 'destination': r[0],
                             'bytes': r[2], 'caller_return': r[14]}
        elif a == 0x08000FA0 and self.copy is not None:
            row = self.copy
            source = self.original[row['source'] - 0x08000000:row['source'] - 0x08000000 + row['bytes']]
            require(bytes(m[row['destination']:row['destination'] + row['bytes']]) == source, 'Native graphics copy differs')
            row.update(all_copied_bytes_match=True, sha256=digest(source))
            self.copies.append(row)
            self.copy = None
        elif a == 0x08005C6C:
            self.cards.append({'frame': event['frame'], 'dungeon_id': m.u32[0x02003B6C],
                               'floor': m.u16[0x02005674], 'reader': a})
        elif a == 0x08005AC8:
            raw = bytes(m[r[2]:r[2] + 8])
            x, y, width, height = struct.unpack('<4h', raw)
            require(0 <= x < 28 and 0 <= y and 0 < width <= 28 - x and height > 0, 'Arrival rectangle differs')
            self.rectangles.append({'frame': event['frame'], 'descriptor': r[2], 'descriptor_hex': raw.hex(),
                                    'source_tiles': [x, y, width, height], 'destination_tiles': r[:2],
                                    'source_rows': [{'offset': ATLAS + ((y + line) * 28 + x) * 32,
                                                     'bytes': width * 32} for line in range(height)]})


def title_backgrounds(original):
    output = OUTPUT / 'title'
    captures = []
    with Session(original, output) as game:
        observer = GraphicsTrace(game, original)
        with Debugger(game, observer.callback, max_events=10000) as trace:
            for a in observer.ADDRESSES:
                trace.breakpoint(a)
            for label, key, frames in [('title', None, 600), ('menu', 'START', 180), ('name', 'A', 180)]:
                game.press(key, wait=frames) if key else game.frames(frames)
                picture = game.capture(label)
                row = observer.backgrounds[-1]
                offset = row['resource_offset']
                tiles = original[offset + 512:offset + 512 + 38400]
                memory = game.core.memory
                require(bytes(memory[0x06000000:0x06009600]) == tiles, 'Captured BG0 differs from selected resource')
                # Native map is synthesized as 30 active columns in a 32-wide
                # screen block. Its two unused columns are not resource data.
                for y in range(20):
                    require([memory.u16[0x0600B000 + y * 64 + x * 2] for x in range(30)] == list(range(y * 30, y * 30 + 30)),
                            'Native title/background tile map differs')
                palette = bytes(memory[0x05000000:0x05000200])
                background = tiled_image(tiles, palette, 240, 160, 8)
                background.save(output / (label + '-background.png'))
                if label == 'title':
                    require(background.tobytes() == picture.tobytes(), 'Title reconstruction differs from complete native frame')
                captures.append({'id': label, 'frame': game.core.frame_counter, 'record_index': row['index'],
                                 'resource_offset': offset, 'tile_sha256': digest(tiles),
                                 'native_palette_sha256': digest(palette), 'background_rgb_sha256': digest(background.tobytes()),
                                 'screen_rgb_sha256': digest(picture.tobytes()), 'dispcnt': memory.u16[0x04000000],
                                 'bg0cnt': memory.u16[0x04000008], 'complete_frame_matches_bg0': label == 'title'})
                (output / (label + '.palette')).write_bytes(palette)
                (output / (label + '.tiles')).write_bytes(tiles)
        require(captures[1]['resource_offset'] == captures[2]['resource_offset'] != captures[0]['resource_offset'],
                'Observed title/menu/name resource relation differs')
        require(captures[1]['tile_sha256'] == captures[2]['tile_sha256'], 'Menu/name background pixels differ')
        family = []
        require(original[0x5FD98:0x5FD9D] == bytes((13, 18, 19, 20, 21)), 'Random background selector changed')
        for index in original[0x5FD98:0x5FD9D]:
            offset = BACKGROUND_TABLE + index * 20
            source = struct.unpack_from('<I', original, offset)[0] - 0x08000000
            family.append({'index': index, 'record_offset': offset, 'record_hex': original[offset:offset + 20].hex(),
                           'resource_offset': source, 'resource_end_exclusive': source + 38912,
                           'resource_sha256': digest(original[source:source + 38912]),
                           'naturally_observed_here': index == captures[1]['record_index']})
        report = {'passed': True, 'source_rom_sha256': digest(original), 'background_loads': observer.backgrounds,
                  'native_copies': observer.copies, 'captures': captures, 'menu_background_candidates': family,
                  'inputs': game.inputs, 'scope': 'Native startup/title, first menu and name editor. Title is reconstructed pixel-for-pixel; this menu/name pair shares one background resource. Five selector candidates are enumerated; the other four are not naturally observed in this run. Palette calibration/fades and all later logo occurrences need separate treatment before artwork insertion.'}
    (output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


def first_dungeon(original):
    with Session(original, ARRIVAL) as game:
        start = Snapshot.load(ROOT / 'build/opening-text/fixtures/opening-1')
        game.restore(start)
        last_seen = False
        def last_line(event):
            nonlocal last_seen
            if event['registers'][1] == BANK_RAM + 0x12C6:
                last_seen = True
        with Debugger(game, last_line, max_events=1000) as trace:
            trace.breakpoint(0x080021B4)
            for _ in range(100):
                game.press('A', wait=240)
                if last_seen:
                    break
        require(last_seen, 'Opening departure not reached')
        game.capture('departure')
        departure = game.snapshot()
        departure.save(ARRIVAL / 'departure')
        observer, frames = GraphicsTrace(game, original), []
        with Debugger(game, observer.callback, max_events=20000) as trace:
            for a in observer.ADDRESSES:
                trace.breakpoint(a)
            game.press('A', wait=0)
            for n in range(4, 604):
                game.frames(1)
                picture = game.capture(f'frame-{n:03}')
                frames.append({'file': f'frame-{n:03}.png', 'frame': game.core.frame_counter,
                               'rgb_sha256': digest(picture.tobytes())})
                if n == 353:
                    palette = bytes(game.core.memory[0x050001E0:0x05000200])
                    game.capture('card')
                    (ARRIVAL / 'card.palette').write_bytes(palette)
                    label = tiled_image(original[0x552684:0x553104], palette, 224, 24, 4)
                    label.save(ARRIVAL / 'label-native-palette.png')
                    tiled_image(original[ATLAS:0x555B04], palette, 224, 264, 4).save(ARRIVAL / 'atlas-native-palette.png')
        require(len(observer.cards) == 1 and observer.cards[0]['dungeon_id'] == 11 and observer.cards[0]['floor'] == 1,
                'First arrival selector differs')
        label = next(row for row in observer.rectangles if row['descriptor'] == 0x0813EE58 + 11 * 8)
        require(label['source_tiles'] == [0, 18, 28, 3], 'First dungeon label rectangle differs')
        for row in label['source_rows']:
            require(any(c['source'] == 0x08000000 + row['offset'] and c['bytes'] == row['bytes']
                        and c['all_copied_bytes_match'] for c in observer.copies), 'Arrival label row lacks native copy proof')
        inputs = list(game.inputs)
        # A second native replay checks every captured transition frame. This
        # does not change RNG, state, bank selection or player input timing.
        game.restore(departure)
        game.press('A', wait=0)
        for row in frames:
            game.frames(1)
            require(digest(game.screen.to_pil().convert('RGB').tobytes()) == row['rgb_sha256'], 'Arrival replay frame differs')
        report = {'passed': True, 'source_rom_sha256': digest(original), 'fixture_state_sha256': digest(start.state),
                  'departure_state_sha256': digest(departure.state), 'inputs': inputs, 'frames': frames,
                  'arrival_calls': observer.cards, 'rectangles': observer.rectangles, 'native_copies': observer.copies,
                  'background_loads': observer.backgrounds, 'native_replay_identical_frames': len(frames),
                  'scope': 'Natural first departure, meadow walk-in, dungeon-11/floor-1 arrival card, and tutorial. All 600 consecutive transition frames replay identically. The arrival card is a separate 4bpp tile atlas, not the ordinary story font. No graphics changed; later dungeon/card selectors remain separate.'}
    (ARRIVAL / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


def run():
    mgba.log.silence()
    original = load_base()
    save = default_rom().with_suffix('.sav')
    save_hash = digest(save.read_bytes())
    title, arrival = title_backgrounds(original), first_dungeon(original)
    require(digest(load_base()) == digest(original) and digest(save.read_bytes()) == save_hash, 'Original files changed')
    report = {'passed': True, 'source_rom_sha256': digest(original), 'source_save_sha256': save_hash,
              'original_files_unchanged': True, 'title_report_sha256': digest((OUTPUT / 'title/report.json').read_bytes()),
              'arrival_report_sha256': digest((ARRIVAL / 'report.json').read_bytes()),
              'title_complete_frame_reconstructed': True, 'same_menu_name_background': True,
              'title_and_menu_use_different_resources': True, 'first_dungeon_card_confirmed': True,
              'arrival_replay_identical_frames': arrival['native_replay_identical_frames'],
              'menu_background_selector_candidates': len(title['menu_background_candidates']), 'graphics_patched': False}
    (OUTPUT / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))
    return report


if __name__ == '__main__':
    run()
