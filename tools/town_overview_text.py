"""Private descriptors for the original computed town overview label reader."""
import json
import struct

from tools.compact_font import encode, measure
from tools.extract_items import source
from tools.rom import ROOT, digest, require

CATALOG = ROOT/'translations/town-overview-review.json'
START, END = 0x14D4CC, 0x14D52C
INDICES = {1,2,3,4,6,7,9,10,11}


def add_town_overview(build):
    catalog = json.loads(CATALOG.read_text())
    table = bytearray(build.original[START:END])
    require(catalog['base_rom_sha256']==digest(build.original)
            and catalog['table_sha256']==digest(table), 'Town overview source differs')
    require({r['index'] for r in catalog['entries']}==INDICES, 'Town overview cohort differs')
    entries=[]
    for row in catalog['entries']:
        i=row['index'];before=bytes(table[8*i:8*i+4]);text=row['english']
        pointer=struct.unpack_from('<I',table,8*i+4)[0]
        require(row['source']==source(build.original,pointer) and row['status']=='reviewed',
                'Town overview source/review differs')
        require(not any(c in text for c in '{}%@\r\n') and before[2:]==b'\x09\x01'
                and before[0] in (1,20) and before[1] in (1,17), 'Town overview controls/window differ')
        width=measure(text);tiles=max(9,(width+15)//8)
        # Retain eight-pixel screen margins; only these standalone labels widen.
        after=bytes([before[0] if before[0]==1 else 29-tiles,before[1],tiles,1])
        raw=b'\x14'+encode(text)
        at=build.allocate(row['id'],raw,'town-overview')
        table[8*i:8*i+4]=after;struct.pack_into('<I',table,8*i+4,at+0x08000000)
        entries.append(row|dict(offset=at,encoded_hex=raw.hex(),text_width=width,
                               original_window=list(before),window=list(after)))
    for i in (0,5,8):require(table[8*i:8*i+8]==b'\0'*8,'Town overview null record differs')
    at=build.allocate('town-overview-private-descriptors',bytes(table),'town-overview')
    build.patch('town-overview-reader',0x51FB0,struct.pack('<I',START+0x08000000),
                struct.pack('<I',at+0x08000000),'town-overview')
    return dict(entries=entries,table_offset=at,catalog_sha256=digest(CATALOG.read_bytes()),
                scope=catalog['scope'])
