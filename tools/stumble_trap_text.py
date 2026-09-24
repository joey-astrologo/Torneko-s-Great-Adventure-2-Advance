"""Private stumbling-trap table and bounded item-loss acknowledgement."""
import json
import struct
from tools.compact_font import encode, load_font, measure
from tools.extract_shared_text import START, END, extract
from tools.inventory_action_text import CONTROL
from tools.rom import ROOT, digest, require

CATALOG = ROOT / 'translations/stumble-trap-review.json'
LITERALS = (0x27F48, 0x27F88, 0x27FB0, 0x283B4)


def add_stumble_trap(build):
    catalog = json.loads(CATALOG.read_text())
    require(catalog['base_rom_sha256'] == digest(build.original), 'Stumble base differs')
    require(len(catalog['entries']) == 4 and
            {r['table_offset'] for r in catalog['entries']} == {0x32C, 0x330, 0x328, 0x1D0},
            'Stumble source selection differs')
    sources = {r['table_offset']: r['source'] for r in extract()['entries']}
    table, rows, font = bytearray(build.original[START:END]), [], load_font()
    for row in catalog['entries']:
        text, source = row['english'], row['source']
        field = row['table_offset'] == 0x1D0
        require(source == sources[row['table_offset']] and row['status'] == 'reviewed' and row['review'],
                'Stumble source/review changed')
        require(text.count('{item}') == text.count('{fit}') == int(field) and
                not any(c in text.replace('{item}', '').replace('{fit}', '') for c in '{}%\n\r'),
                'Stumble fields/controls changed')
        widths = [measure(part.replace('{item}', ''), font) + part.count('{item}') * 192
                  for part in text.split('{fit}')]
        require(max(widths) <= 216, 'Stumble fallback width exceeds216px')
        payload = CONTROL.join(b'%s'.join(encode(f)[:-1] for f in p.split('{item}'))
                               for p in text.split('{fit}')) + b'\0'
        maximum = len(payload) + (61 if field else 0)
        require(maximum <= 256, 'Stumble formatter exceeds256-byte output')
        offset = build.allocate(row['id'], payload, 'stumble-trap-text')
        struct.pack_into('<I', table, row['table_offset'], offset + 0x08000000)
        rows.append(row | {'offset': offset, 'encoded_hex': payload.hex(),
                           'maximum_line_widths': widths, 'maximum_bytes': maximum})
    offset = build.allocate('stumble-trap-private-table', bytes(table), 'stumble-trap-text')
    for literal in LITERALS:
        build.patch(f'stumble-trap-table-{literal:x}', literal, struct.pack('<I', START + 0x08000000),
                    struct.pack('<I', offset + 0x08000000), 'stumble-trap-text')
    return {'entries': rows, 'table_offset': offset, 'catalog_sha256': digest(CATALOG.read_bytes()),
            'scope': catalog['scope']}
