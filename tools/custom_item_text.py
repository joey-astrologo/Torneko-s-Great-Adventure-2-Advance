"""Private English category labels for the native custom item-name formatter."""

import json
import struct

from tools.compact_font import encode
from tools.extract_item_aliases import END, extract
from tools.extract_items import source
from tools.rom import ROOT, digest, require

CATALOG = ROOT / 'translations/custom-items-review.json'
CATEGORY_READERS = (0xF58C, 0xF59C, 0xF5B8)


def add_custom_items(build):
    catalog = json.loads(CATALOG.read_text())
    require(catalog['base_rom_sha256'] == digest(build.original), 'Custom item base differs')
    labels = extract()['category_labels']
    require({row['category'] for row in catalog['labels']} == set(range(14))
            and len(catalog['labels']) == 14, 'Custom category cohort differs')
    table = bytearray(build.original[END:END + 56])
    entries = []
    for row in catalog['labels']:
        require(row['source'] == labels[row['category']]['source'] and row['status'] == 'reviewed',
                'Custom category review/source differs')
        raw = encode(row['english'])
        offset = build.allocate(row['id'], raw, 'custom-items')
        struct.pack_into('<I', table, row['category'] * 4, offset + 0x08000000)
        entries.append(row | {'offset': offset, 'encoded_hex': raw.hex()})
    table_offset = build.allocate('custom-item-categories', bytes(table), 'custom-items')
    for site in CATEGORY_READERS:
        build.patch(f'custom-category-{site:x}', site, struct.pack('<I', END + 0x08000000),
                    struct.pack('<I', table_offset + 0x08000000), 'custom-items')
    require({row['kind'] for row in catalog['entries']} == {'plain', 'count'}
            and len(catalog['entries']) == 2, 'Custom format cohort differs')
    for row in catalog['entries']:
        require(row['status'] == 'reviewed', 'Unreviewed custom format')
        raw = b'\x03\x04%s' + encode(':')[:-1] + b'%s'
        if row['kind'] == 'count':
            raw += encode('[')[:-1] + b'%s' + encode(']')[:-1]
        raw += b'\x05\0'
        for site in row['readers']:
            pointer = struct.unpack_from('<I', build.original, site)[0]
            require(row['source'] == source(build.original, pointer), 'Custom format source differs')
        offset = build.allocate(row['id'], raw, 'custom-items')
        entries.append(row | {'offset': offset, 'encoded_hex': raw.hex()})
        for site in row['readers']:
            build.patch(f'custom-format-{site:x}', site,
                        struct.pack('<I', row['source']['offset'] + 0x08000000),
                        struct.pack('<I', offset + 0x08000000), 'custom-items')
    return {'entries': entries, 'table_offset': table_offset, 'scope': catalog['scope'],
            'catalog_sha256': digest(CATALOG.read_bytes())}
