"""Bind the computed shield damage selector while inheriting combat translations."""
import json
import struct

from tools.compact_font import encode, measure
from tools.extract_items import source
from tools.extract_shared_text import START, END
from tools.inventory_action_text import CONTROL
from tools.rom import ROOT, digest, require

CATALOG = ROOT/'translations/shield-reflection-review.json'


def add_shield_reflection(build):
    catalog = json.loads(CATALOG.read_text())
    require(catalog['base_rom_sha256'] == digest(build.original) and len(catalog['entries']) == 1,
            'Shield reflection review identity differs')
    row = catalog['entries'][0]
    require(row['source'] == source(build.original,0x0806393C) and row['status'] == 'reviewed' and
            row['table_offset'] == 0x224 and row['fields'] == ['actor','amount'],
            'Shield reflection source/fields differ')
    require(row['english'] == '{actor}{fit} takes {amount} damage from the shield.',
            'Shield reflection wording requires new bounds review')
    payload = b'%s'+CONTROL+encode(' takes ')[:-1]+b'%d'+encode(' damage from the shield.')
    widths = [186,measure(' takes 2147483647 damage from the shield.')]
    maximum = len(payload)+61+8
    require(max(widths) <= 216 and maximum <= 256,'Shield reflection bounds exceeded')
    # Check the incoming selector, local save, computed lookup and queue gate.
    for at,raw in ((0xCBC0,'8923'),(0xCD4C,'9693'),
                   (0xCEC4,'2249969da8004018016847aa07a83b1cf4f770f8'),
                   (0xCEEC,'969b002b03d007a8002108f0c9fc')):
        require(build.original[at:at+len(bytes.fromhex(raw))].hex() == raw,
                'Shield selector code ownership differs')
    offset = build.allocate(row['id'],payload,'shield-reflection')
    # This consumer also selects already-localized ordinary damage (0x67).
    table = bytearray(build.data[START:END])
    require(struct.unpack_from('<I',table,0x224)[0] == 0x0806393C,'Shield source slot differs')
    struct.pack_into('<I',table,0x224,offset+0x08000000)
    table_at = build.allocate('shield-damage-private-table',bytes(table),'shield-reflection')
    build.patch('shield-damage-reader',0xCF50,struct.pack('<I',START+0x08000000),
                struct.pack('<I',table_at+0x08000000),'shield-reflection')
    return dict(entries=[row | dict(offset=offset,encoded_hex=payload.hex(),maximum_bytes=maximum,
                maximum_line_widths=widths,capacity=256,amount_range=[0,0x7FFFFFFF])],
        table_offset=table_at,consumer_literal=0xCF50,inherited_from_compiled_shared_table=True,
        catalog_sha256=digest(CATALOG.read_bytes()),scope=catalog['scope'])
