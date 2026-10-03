"""Private table for the computed wind-stage notice caller at 080051F0."""
import json
import struct

from tools.compact_font import encode, measure
from tools.dialogue_layout import PLAYER_WIDTH
from tools.extract_shared_text import START, END, extract
from tools.rom import ROOT, digest, require

CATALOG = ROOT/'translations/wind-review.json'


def add_wind(build):
    catalog = json.loads(CATALOG.read_text())
    require(catalog['base_rom_sha256'] == digest(build.original), 'Wind base differs')
    require(len(catalog['entries']) == 1, 'Wind cohort differs')
    row = catalog['entries'][0]
    source = next(r['source'] for r in extract()['entries'] if r['table_offset']==0x458)
    require(row['source'] == source and row['status']=='reviewed', 'Wind source/review differs')
    text = row['english']
    require(text.count('{player}')==1 and not any(c in text.replace('{player}','') for c in '{}%\n'),
            'Wind player field differs')
    raw = b'%s'.join(encode(part)[:-1] for part in text.split('{player}'))+b'\0'
    width = measure(text.replace('{player}',''))+PLAYER_WIDTH
    require(width<=216 and len(raw)+14-2<=256, 'Wind exceeds native wrapper bounds')
    offset = build.allocate(row['id'],raw,'wind')
    table = bytearray(build.original[START:END])
    struct.pack_into('<I',table,0x458,offset+0x08000000)
    table_offset = build.allocate('wind-private-table',bytes(table),'wind')
    build.patch('wind-computed-table',0x5220,struct.pack('<I',START+0x08000000),
                struct.pack('<I',table_offset+0x08000000),'wind')
    return dict(entries=[row|dict(offset=offset,encoded_hex=raw.hex(),maximum_width=width,
                                 maximum_bytes=len(raw)+12,capacity=256)],
                table_offset=table_offset,catalog_sha256=digest(CATALOG.read_bytes()),
                scope=catalog['scope'])
