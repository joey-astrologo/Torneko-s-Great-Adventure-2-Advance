"""Connect the dungeon menu banner to the already reviewed location strings."""
import struct

from tools.compact_font import encode, measure
from tools.rom import require

OWNER = 'dungeon-location-banner'
LITERAL = 0x19E44
BUDGET = 168


def add_location_banner(build, results):
    rows = sorted((r for r in results['ui_entries'] if 0x5D0 <= r['table_offset'] <= 0x600),
                  key=lambda r: r['table_offset'])
    require([r['table_offset'] for r in rows] == list(range(0x5D0, 0x604, 4)),
            'Dungeon banner location set incomplete')
    table = results['shared_table']
    allocation = next(a for a in build.allocations if a['id'] == 'result-shared-table')
    require(allocation['owner'] == 'results' and allocation['start'] == table and
            allocation['end_exclusive'] >= table + 0x604, 'Location table lacks ownership')
    entries = []
    for selector, row in enumerate(rows):
        payload = bytes.fromhex(row['encoded_hex'])
        require(row['status'] == 'reviewed' and payload == encode(row['english']) and
                not any(c in row['english'] for c in '\r\n%{}') and
                measure(row['english']) <= BUDGET, 'Location banner exceeds its one-line budget')
        require(struct.unpack_from('<I', build.original, 0x140D68 + row['table_offset'])[0] ==
                0x08000000 + row['source']['offset'], 'Original location selector differs')
        require(struct.unpack_from('<I', build.data, table + row['table_offset'])[0] ==
                0x08000000 + row['offset'], 'Translated location pointer differs')
        require(build.data[row['offset']:row['offset'] + len(payload)] == payload,
                'Translated location bytes differ')
        entries.append(row | {'selector': selector, 'banner_budget': BUDGET,
                              'banner_width': measure(row['english'])})
    build.patch('dungeon-location-banner-table', LITERAL,
                struct.pack('<I', 0x08140D68), struct.pack('<I', 0x08000000 + table), OWNER)
    return {'entries': entries, 'shared_table': table, 'literal': LITERAL, 'budget': BUDGET,
            'scope': 'One owned reader-literal redirect. Reuses all 13 reviewed result/history location strings; '
                     'no new text allocations, window geometry, RAM/save fields or selector changes.'}
