"""Localize the direct Floor/status modal readers outside the message queue."""
import json
import struct

from tools.compact_font import encode, measure
from tools.rom import ROOT, digest, require

CATALOG = ROOT / 'translations/floor-notices-review.json'
START, SIZE = 0x140D68, 0x40C
SLOTS = {0x30, 0x34, 0xC8, 0x3C8, 0x3E4, 0x408}


def add_floor_notices(build, notices):
    catalog = json.loads(CATALOG.read_text())
    require(catalog['base_rom_sha256'] == digest(build.original) and
            {r['table_offset'] for r in catalog['entries']} == SLOTS,
            'Floor modal source/review cohort differs')
    table = bytearray(build.original[START:START + SIZE])
    rows = []
    for row in catalog['entries']:
        slot = row['table_offset']
        prior = next(r for r in notices['entries'] if slot in r['equivalent_slots'])
        raw, width = encode(row['english']), measure(row['english'])
        require(row['status'] == 'reviewed' and row['source'] == prior['source'] and
                struct.unpack_from('<I', table, slot)[0] == 0x08000000 + row['source']['offset'] and
                not any(c in row['english'] for c in '\r\n%{}') and width <= 168,
                'Floor modal source or one-line budget differs')
        if raw.hex() == prior['encoded_hex']:
            offset = prior['offset']
            require(build.data[offset:offset + len(raw)] == raw,
                    'Existing English notice bytes differ')
        else:
            offset = build.allocate(f'floor-notice.{slot:03x}', raw, 'floor-notices')
        struct.pack_into('<I', table, slot, 0x08000000 + offset)
        rows.append(row | {'offset': offset, 'encoded_hex': raw.hex(), 'width': width})
    offset = build.allocate('floor-notice-private-table', bytes(table), 'floor-notices')
    for literal in (0x16FB0, 0x17154, 0x17238):
        build.patch(f'floor-notice-table-{literal:x}', literal,
                    struct.pack('<I', 0x08140D68), struct.pack('<I', offset + 0x08000000),
                    'floor-notices')
    return {'entries': rows, 'table_offset': offset, 'budget': 168,
            'catalog_sha256': digest(CATALOG.read_bytes()), 'scope': catalog['scope']}
