"""Export T2's scrolling credits and arrival atlas with exact source provenance."""
import json
import struct

from PIL import Image

from tools.lz77 import decompress
from tools.rom import ROOT, load_base, digest, require

OUT = ROOT / 'build/graphics-audition'
ATLAS = 0x54E784
ATLAS_END = 0x555B04
RECTS = 0x13EE58
ARRIVALS = [
    ('屋敷のダンジョン', "Banker's Mansion"),
    ('墓場のダンジョン', 'Cemetery Dungeon'),
    ('お城のダンジョン', 'Castle Dungeon'),
    ('迷いの森', 'Lost Forest'),
    ('火吹き山', 'Mt. Fiery'),
    ('トロ遺跡', 'Toro Ruins'),
    ('不思議のダンジョン', 'Magic Dungeon'),
    ('もっと不思議のダンジョン', 'More Magic Dungeon'),
    ('試練の館', 'Ordeal Mansion'),
    ('剣のダンジョン', 'Sword Dungeon'),
    ('魔のダンジョン', 'Mage Dungeon'),
    ('ちょっと不思議の草原', 'Mysterious Meadow'),
    ('井戸', 'Well'),
]


def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n')


def palette(raw):
    return [tuple((((v >> shift) & 31) << 3) | (((v >> shift) & 31) >> 2) for shift in (0, 5, 10))
            for v, in struct.iter_unpack('<H', raw)]


def tiles_image(data, colours, width, height):
    require(width % 8 == height % 8 == 0 and len(data) == width*height//2,
            'Invalid 4bpp tile dimensions')
    im = Image.new('RGB', (width, height), colours[0])
    pixels = im.load()
    for y in range(height):
        for x in range(width):
            at = (y//8*(width//8)+x//8)*32 + (y % 8)*4 + (x % 8)//2
            pixels[x, y] = colours[(data[at] >> (4*(x % 2))) & 15]
    return im


def source_range(rom, start, end, purpose):
    require(0 <= start < end <= len(rom), 'Source range outside ROM')
    return {'start': start, 'end_exclusive': end, 'sha256': digest(rom[start:end]), 'purpose': purpose}


def credits(rom):
    config_path = ROOT / 'config/credits-audition.json'
    cfg = json.loads(config_path.read_text())
    require(cfg['source_rom_sha256'] == digest(rom), 'Credits transcript base differs')
    start = cfg['compressed_offset']
    data, end = decompress(rom, start)
    count = struct.unpack_from('<H', data, 32)[0]
    require(count == 7800 and len(data) == 79546, 'Credits dimensions changed')
    mask = data[34:34+count]
    require(set(mask) == {0, 1}, 'Unknown credits cell format')
    tiledata = data[34+count:]
    require(len(tiledata) == sum(mask)*32, 'Credit occupied-cell/tile count differs')
    colours = palette(data[:32])
    im = Image.new('RGB', (240, count//30*8), colours[0])
    index = 0
    for cell, occupied in enumerate(mask):
        if occupied:
            tile = tiles_image(tiledata[index*32:(index+1)*32], colours, 8, 8)
            im.paste(tile, (cell % 30*8, cell//30*8))
            index += 1
    bands, top = [], None
    for y in range(im.height+1):
        ink = y < im.height and im.crop((0, y, 240, y+1)).getbbox()
        if ink and top is None:
            top = y
        elif not ink and top is not None:
            bounds = im.crop((0, top, 240, y)).getbbox()
            bands.append([bounds[0], top, bounds[2], y])
            top = None
    require(len(bands) == len(cfg['lines']) == 67, 'Credit transcript/image line coverage differs')
    lines = []
    for i, (text, bounds) in enumerate(zip(cfg['lines'], bands, strict=True)):
        role = 'heading' if i in cfg['heading_indices'] else 'copyright' if i >= 61 else 'name'
        x = 12 if role == 'heading' else (20 if i == 61 else 44) if role == 'copyright' else 64
        lines.append({'id': f'credit-line-{i:02}', 'text': text, 'role': role,
                      'x': x, 'y': bounds[1], 'bounds': bounds, 'width_budget': 240-x})
    sections = []
    for j, first in enumerate(cfg['section_indices']):
        stop = (cfg['section_indices']+[len(lines)])[j+1]
        sections.append({'id': f'credit-section-{j:02}', 'label': lines[first]['text'],
                         'first_line': first, 'end_line_exclusive': stop,
                         'top': lines[first]['y']-8,
                         'bottom': lines[stop-1]['bounds'][3]+8})
    report = {'schema': 1, 'source_rom_sha256': digest(rom), 'output_rom': None,
              'source': source_range(rom, start, end, 'BIOS type-10 GBA credit bitmap'),
              'decoded_sha256': digest(data), 'decoded_bytes': len(data),
              'decoded_layout': {'palette': [0, 32], 'cell_count': [32, 34],
                                 'occupancy': [34, 34+count], 'tiles': [34+count, len(data)]},
              'dimensions': list(im.size), 'occupied_tiles': index, 'palette': colours,
              'reader': 0x080554FC, 'source_literal': 0x555DC,
              'lines': lines, 'sections': sections, 'config_sha256': digest(config_path.read_bytes()),
              'scope': 'Complete decoded GBA credit roll. All 67 visible lines are English; exact source spellings retained. Raster reconstruction, not natural ending access. Older ASCII credits at 0x6DF04 are a different resource.'}
    return report, im


def rectangle(rom, at):
    rect = struct.unpack_from('<4h', rom, at)
    x, y, w, h = rect
    require(0 <= x < 28 and 0 <= y < 33 and 0 < w <= 28-x and 0 < h <= 33-y,
            'Arrival rectangle outside its atlas')
    return list(rect)


def arrivals(rom):
    colours = palette(rom[ATLAS-32:ATLAS])
    atlas = tiles_image(rom[ATLAS:ATLAS_END], colours, 224, 264)
    names_path = ROOT/'translations/save-preview-review.json'
    names = {r['id']: r for r in json.loads(names_path.read_text())['entries']}
    entries, images = [], {}
    for i, (jp, en) in enumerate(ARRIVALS):
        at = RECTS+8*i
        reference = names[f'save-preview.{0x5d0+4*i:x}']
        require(reference['english'] == en and reference['status'] == 'reviewed',
                'Arrival candidate differs from the reviewed destination name')
        x, y, w, h = rectangle(rom, at)
        crop = atlas.crop((8*x, 8*y, 8*(x+w), 8*(y+h)))
        dest = [8*((30-w)//2), 32, 8*w, 8*h]
        image = Image.new('RGB', (240, 160), colours[0])
        image.paste(crop, dest[:2])
        ident = f'arrival-{i:02}'
        images[ident] = image
        entries.append({'id': ident, 'selector': i, 'japanese': jp, 'english': en,
                        'wording_status': 'existing reviewed destination name; artwork not selected',
                        'name_catalog_id': reference['id'],
                        'descriptor_offset': at, 'descriptor_hex': rom[at:at+8].hex(),
                        'source_rect_tiles': [x, y, w, h], 'text_region': dest,
                        'source_rows': [source_range(rom, ATLAS+((y+n)*28+x)*32,
                                                    ATLAS+((y+n)*28+x+w)*32, 'arrival atlas row')
                                        for n in range(h)],
                        'floor_kind': 'level' if i == 12 else 'ordinary',
                        'native_reachability': 'ordinary first entry observed' if i == 11 else 'controlled selector; ordinary route not established'})
    glyphs = {}
    for name, at in [(str(i), 0x13EE00+8*i) for i in range(10)]+[('F', 0x13EE50), ('level', 0x13EEC0)]:
        x, y, w, h = rectangle(rom, at)
        glyphs[name] = atlas.crop((8*x, 8*y, 8*(x+w), 8*(y+h)))
    manifest = {'schema': 1, 'source_rom_sha256': digest(rom), 'output_rom': None,
                'resources': [source_range(rom, ATLAS-32, ATLAS, 'stored palette'),
                              source_range(rom, ATLAS, ATLAS_END, '4bpp arrival atlas'),
                              source_range(rom, 0x13EE00, 0x13EEC8, 'digits, F, 13 location rectangles and level prefix')],
                'entries': entries, 'palette': colours, 'name_catalog_sha256': digest(names_path.read_bytes()),
                'reader': 0x08005B6C,
                'scope': '13 nonempty location rectangles (IDs 0–12), ten digits, F and the separate level prefix. ID12 suppresses its complete card above floor10. Separate town cards are not established; first castle/home transitions had no separate card.'}
    return manifest, atlas, images, glyphs


def run():
    rom = load_base()
    manifest, roll = credits(rom)
    folder = ROOT/'build/credits'
    folder.mkdir(parents=True, exist_ok=True)
    roll.save(folder/'original-roll.png')
    for s in manifest['sections']:
        roll.crop((0, s['top'], 240, s['bottom'])).save(folder/(s['id']+'.png'))
    save_json(folder/'manifest.json', manifest)
    manifest, atlas, images, glyphs = arrivals(rom)
    folder = ROOT/'build/arrival-cards'
    folder.mkdir(parents=True, exist_ok=True)
    atlas.save(folder/'original-atlas.png')
    for ident, image in images.items():
        image.save(folder/(ident+'.png'))
    for key, image in glyphs.items():
        image.save(folder/('glyph-'+key+'.png'))
    save_json(folder/'manifest.json', manifest)
    print('Exported 67 credit lines / 15 sections and 13 arrival names / 12 floor components')


if __name__ == '__main__':
    run()
