"""Freeze original Torneko 3 Latin font 0 for a standalone Torneko 2 build."""

import argparse
import json
from pathlib import Path
import struct

from tools.rom import ROOT, digest, load_base, require

SOURCE_SHA = '35bfff00dccd8de1a916b316298219c8c16a8adb0162ffe5056c481e0a8a4d02'
DEFAULT = ROOT.parent/'torneko-3-gba/Dragon Quest Characters - Torneko no Daibouken 3 Advance - Fushigi no Dungeon (Japan).gba'
OUTPUT = ROOT/'assets/fonts/torneko3-english.json'


def convert_glyph(record, bitmap):
    _, _, advance, _, colored, _ = struct.unpack('<IHhHBB', record)
    require(not colored and 1 <= advance <= 7 and len(bitmap) == 72, 'Unsupported source glyph')
    pixels = [[(bitmap[y*6+x//2] >> (4*(x%2))) & 15 for x in range(12)] for y in range(12)]
    require(all(v in (0,15) for row in pixels for v in row), 'Source glyph is not monochrome')
    require(not any(v for row in pixels for v in row[advance:]), 'Source glyph overhang would be lost')
    # Two blank top rows align the original nine-pixel capital body with T2's
    # existing baseline, without scaling, thinning, cropping ink or changing advance.
    return advance, ['.'*advance]*2 + [''.join('#' if v else '.' for v in row[:advance]) for row in pixels]


def run(path=DEFAULT):
    original = path.read_bytes()
    require(digest(original) == SOURCE_SHA, 'Expected original Japanese Torneko 3 ROM, not a translation patch')
    descriptors = {}
    for i in range(1345):
        offset = 0xC93B4C+i*12
        record = original[offset:offset+12]
        descriptors[struct.unpack_from('<H',record,4)[0]] = (offset,record)
    glyphs = {}
    source_bytes = bytearray()
    for code in range(32,127):
        mapped = struct.unpack_from('<H',original,0xCA2674+code*2)[0]
        offset,record = descriptors[mapped]
        bitmap_offset = struct.unpack_from('<I',record)[0]-0x08000000
        bitmap = original[bitmap_offset:bitmap_offset+72]
        advance,rows = convert_glyph(record,bitmap)
        source_bytes.extend(record+bitmap)
        glyphs[chr(code)] = {'advance':advance,'rows':rows,'origin':'torneko3-rom',
            'source_descriptor_offset':offset,'source_descriptor_hex':record.hex(),
            'source_bitmap_offset':bitmap_offset,'source_bitmap_hex':bitmap.hex()}
    font = {'schema':2,'id':'torneko3','name':'Torneko 3 original Latin font 0',
        'base_rom_sha256':digest(load_base()),'source_rom_sha256':SOURCE_SHA,
        'source_records_sha256':digest(source_bytes),'source_font':0,
        'adaptation':'Original advances and monochrome ink preserved; two blank rows added above the 12 source rows for T2 baseline alignment.',
        'glyphs':glyphs}
    OUTPUT.write_text(json.dumps(font,indent=2)+'\n')
    print(OUTPUT, font['source_records_sha256'])
    return font


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rom',type=Path,default=DEFAULT)
    run(parser.parse_args().rom)
