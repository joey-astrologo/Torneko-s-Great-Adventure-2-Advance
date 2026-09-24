"""Private monster fullness, spell sealing and Kaclang formatter ownership."""
import json
import re
import struct
from tools.compact_font import encode, measure
from tools.dialogue_layout import PLAYER_WIDTH
from tools.extract_shared_text import START, END, extract
from tools.inventory_action_text import CONTROL
from tools.rom import ROOT, digest, require
CATALOG = ROOT / 'translations/monster-conditions-review.json'


def add_monster_conditions(build):
    catalog = json.loads(CATALOG.read_text())
    require(catalog['base_rom_sha256'] == digest(build.original), 'Monster condition base differs')
    args = {0x2C4: 'number', 0x418: 'player', 0x490: 'actor'}
    require(len(catalog['entries']) == 3 and {r['table_offset'] for r in catalog['entries']} == set(args),
            'Monster condition sources differ')
    sources = {r['table_offset']: r['source'] for r in extract()['entries']}
    bounds = {'actor': (186, 63), 'player': (PLAYER_WIDTH, 14), 'number': (measure('2147483647'), 10)}
    table, rows = bytearray(build.original[START:END]), []
    for row in catalog['entries']:
        text, slot = row['english'], row['table_offset']
        field = args[slot]
        require(row['source'] == sources[slot] and row['status'] == 'reviewed' and row['review'],
                'Monster condition source/review differs')
        require(re.findall(r'\{(?!fit\})([^}]+)\}', text) == [field] and
                text.count('{fit}') == int(slot == 0x490) and
                not any(c in re.sub(r'\{[^}]+\}', '', text) for c in '{}%\r\n'), 'Monster condition fields differ')
        widths = [measure(re.sub(r'\{[^}]+\}', '', p)) + p.count('{'+field+'}') * bounds[field][0]
                  for p in text.split('{fit}')]
        payload = b''.join(CONTROL if p == '{fit}' else b'%d' if p == '{number}' else b'%s'
                           if p.startswith('{') else encode(p)[:-1] for p in re.split(r'(\{[^}]+\})', text)) + b'\0'
        maximum = len(payload) + bounds[field][1] - 2
        require(max(widths) <= 216 and maximum <= 256, 'Monster condition output exceeds budgets')
        offset = build.allocate(row['id'], payload, 'monster-condition-text')
        struct.pack_into('<I', table, slot, offset + 0x08000000)
        rows.append(row | {'offset': offset, 'encoded_hex': payload.hex(), 'maximum_bytes': maximum,
                           'maximum_line_widths': widths})
    offset = build.allocate('monster-condition-private-table', bytes(table), 'monster-condition-text')
    for literal in (0x2C1EC, 0x2CE84, 0x2CEBC):
        build.patch(f'monster-condition-table-{literal:x}', literal, struct.pack('<I', START + 0x08000000),
                    struct.pack('<I', offset + 0x08000000), 'monster-condition-text')
    return {'entries': rows, 'table_offset': offset, 'catalog_sha256': digest(CATALOG.read_bytes()),
            'scope': catalog['scope']}
