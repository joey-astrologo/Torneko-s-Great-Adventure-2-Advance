"""The item selector's direct-ROM heading in its original40px window."""
import json
import struct
from tools.rom import ROOT, digest, require
from tools.compact_font import encode, measure
from tools.extract_shared_text import extract, START

CATALOG = ROOT / 'translations/selection-prompts-review.json'


def add_selection_prompt(build):
    catalog = json.loads(CATALOG.read_text())
    require(catalog['base_rom_sha256'] == digest(build.original) and len(catalog['entries']) == 1, 'Selection prompt base/count differs')
    row = catalog['entries'][0]
    source = next(r['source'] for r in extract()['entries'] if r['table_offset'] == 0x14)
    require(row['status'] == 'reviewed' and row['source'] == source and row['table_offset'] == 0x14, 'Selection heading source differs')
    require(row['english'] == 'Which?' and measure(row['english']) <= 40, 'Selection heading exceeds original region')
    payload = encode(row['english'])
    offset = build.allocate(row['id'], payload, 'selection-prompt')
    table = build.allocate('selection-prompt-private-table', bytes(20) + struct.pack('<I', offset + 0x08000000), 'selection-prompt')
    build.patch('selection-prompt-table-literal', 0x1DDE4, struct.pack('<I', START + 0x08000000),
                struct.pack('<I', table + 0x08000000), 'selection-prompt')
    return {'entries': [row | {'offset': offset, 'encoded_hex': payload.hex(), 'layout': {'pages': [[row['english']]],
                             'line_widths': [[measure(row['english'])]], 'native_width': 40, 'native_rows': 1,
                             'direct_rom_stream': True}}], 'table_offset': table,
            'catalog_sha256': digest(CATALOG.read_bytes()),
            'scope': 'Only the heading loaded at0801DDBE..1DDC6 in item selector0801DD5C; its original40px/one-row geometry and buffers remain unchanged. Other shared-source consumers remain original.'}
