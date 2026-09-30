"""Approved Shiren arrival bitmaps in an owned appended atlas and descriptor copy."""
import json
import struct

from PIL import Image

from tools.extract_graphics_audition import ATLAS, ATLAS_END, arrivals, palette, tiles_image
from tools.rom import ROOT, digest, require

OWNER = 'arrival-card-artwork'
DESCRIPTORS = 0x13EE00
DESCRIPTORS_END = 0x13EEC8
FONT = ROOT/'assets/fonts/shiren-arrival.json'
CONFIG = ROOT/'config/arrival-art.json'
POINTERS = {0x5B68: ATLAS, 0x5BFC: 0x13EEC0, 0x5C00: 0x13EC80,
            0x5C5C: 0x13EC80, 0x5C60: 0x13EE50, 0x5C64: 0x13EE58}


def font_data():
    cfg = json.loads(CONFIG.read_text())
    require(digest(FONT.read_bytes()) == cfg['font_sha256'], 'Approved arrival font changed')
    font = json.loads(FONT.read_text())['font']
    require(font['id'] == cfg['face'] and font['cap_height'] == cfg['height'] == 17,
            'Only the approved native-size source font is inserted')
    require(cfg['tracking'] == 0 and cfg['floor_style'] == 'original', 'Unapproved arrival rendering settings')
    return cfg, font


def measure(font, text):
    require(set(text) <= set(font['glyphs']), 'Arrival text needs unsupported glyphs: '+text)
    return sum(font['glyphs'][ch]['advance'] for ch in text)


def lettering(font, text, width, x, baseline):
    """Native-scale binary glyphs; reject every out-of-region ink pixel."""
    im = Image.new('L', (width, 24))
    for ch in text:
        g = font['glyphs'][ch]
        for yy, row in enumerate(g['rows']):
            for xx, value in enumerate(row):
                require(value in '03', 'Approved source lettering is binary')
                if value == '3':
                    px, py = x+xx, baseline+g['top']+yy
                    require(0 <= px < width and 0 <= py < 24, 'Arrival artwork clips: '+text)
                    im.putpixel((px, py), 1)
        x += g['advance']
    return im


def pack(image):
    require(image.width % 8 == image.height % 8 == 0, 'Atlas must use full tiles')
    out = bytearray()
    for ty in range(0, image.height, 8):
        for tx in range(0, image.width, 8):
            for y in range(8):
                for x in range(0, 8, 2):
                    lo, hi = image.getpixel((tx+x, ty+y)), image.getpixel((tx+x+1, ty+y))
                    require(0 <= lo <= 15 and 0 <= hi <= 15, 'Palette index outside 4bpp')
                    out.append(lo | hi << 4)
    return bytes(out)


def artwork(original):
    cfg, font = font_data()
    manifest, _, _, _ = arrivals(original)
    desc = bytearray(original[DESCRIPTORS:DESCRIPTORS_END])
    # Retain all original atlas bytes in this private copy, including digits/F.
    # New rows live after them. No source gap or padding is reused as free space.
    extension = Image.new('L', (224, 14*24))
    rows = []
    for e in manifest['entries']:
        ident, text = e['selector'], e['english']
        require(cfg['names'][str(ident)] == text, 'Approved arrival wording changed')
        advance = measure(font, text)
        width = cfg['width_tiles'].get(str(ident), e['source_rect_tiles'][2])
        destination_x = ((30-width)//2)*8
        x = (240-advance)//2-destination_x
        graphic = lettering(font, text, width*8, x, 20)
        extension.paste(graphic, (0, ident*24))
        rect = [0, 33+ident*3, width, 3]
        struct.pack_into('<4h', desc, 88+ident*8, *rect)
        require(destination_x >= 0 and destination_x+width*8 <= 240 and width <= 28,
                'Arrival descriptor exceeds native map or atlas row')
        rows.append({'id': e['id'], 'selector': ident, 'english': text,
                     'advance_px': advance, 'original_width_px': e['text_region'][2],
                     'text_region': [destination_x, 32, width*8, 24], 'source_rect_tiles': rect,
                     'ink_bounds_local': list(graphic.getbbox()), 'glyph_origin_counts':
                     {kind: sum(font['glyphs'][c]['origin'] == kind for c in text)
                      for kind in sorted({font['glyphs'][c]['origin'] for c in text})}})
    level = lettering(font, 'Level', 64, 0, 17)
    extension.paste(level, (0, 13*24))
    struct.pack_into('<4h', desc, 192, 0, 72, 8, 3)
    data = original[ATLAS:ATLAS_END]+pack(extension)
    require(len(data) == 28*75*32 and desc[:88] == original[DESCRIPTORS:DESCRIPTORS+88],
            'Original floor components changed')
    require(original[ATLAS:ATLAS+32] == bytes(32), 'Original blank tile differs')
    require(palette(original[ATLAS-32:ATLAS])[1] == (255, 255, 255), 'White palette entry differs')
    return data, bytes(desc), rows


def add_arrival_art(build):
    data, descriptors, rows = artwork(build.original)
    atlas = build.allocate('arrival-english-atlas', data, OWNER)
    table = build.allocate('arrival-english-descriptors', descriptors, OWNER)
    for at, old in POINTERS.items():
        new = atlas if old == ATLAS else table+(old-DESCRIPTORS)
        build.patch(f'arrival-pointer-{at:05x}', at, struct.pack('<I', 0x08000000+old),
                    struct.pack('<I', 0x08000000+new), OWNER)
    return {'font_sha256': digest(FONT.read_bytes()), 'config_sha256': digest(CONFIG.read_bytes()),
            'generator_sha256': digest((ROOT/'tools/arrival_art.py').read_bytes()),
            'atlas_offset': atlas, 'atlas_bytes': len(data), 'atlas_dimensions': [224, 600],
            'descriptors_offset': table, 'descriptor_bytes': len(descriptors), 'entries': rows,
            'level_prefix': {'english': 'Level', 'source_rect_tiles': [0, 72, 8, 3],
                             'text_region': [64, 80, 64, 24], 'advance_px': 44},
            'english_graphic_count': 14, 'original_digits_f_palette_and_credits_preserved': True,
            'scope': '13 approved single-line Shiren location names and Level, native scale/spacing; Ordeal Mansion widened to 17 tiles. Private appended atlas/descriptors, six owned literal redirects. No instruction, RAM/save allocation, floor-number, palette, fade or credits changes.'}


def inserted_atlas(rom, report):
    at = report['atlas_offset']
    return tiles_image(rom[at:at+report['atlas_bytes']], palette(rom[ATLAS-32:ATLAS]), 224, 600)
