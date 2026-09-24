"""Owned strength/max-HP drain formats with separate actor and player bounds."""
import json
import re
import struct
from tools.compact_font import encode, measure
from tools.dialogue_layout import PLAYER_WIDTH
from tools.extract_shared_text import START, END, extract
from tools.inventory_action_text import CONTROL
from tools.rom import ROOT, digest, require

CATALOG = ROOT / 'translations/drain-review.json'


def add_drain(build):
    catalog = json.loads(CATALOG.read_text())
    require(catalog['base_rom_sha256'] == digest(build.original), 'Drain base differs')
    require(len(catalog['entries']) == 3 and {r['table_offset'] for r in catalog['entries']} ==
            {0x258, 0x94C, 0xA18}, 'Drain sources differ')
    sources = {r['table_offset']: r['source'] for r in extract()['entries']}
    table, rows = bytearray(build.original[START:END]), []
    for row in catalog['entries']:
        text = row['english']
        actor = row['table_offset'] != 0xA18
        fields = ['actor'] if actor else ['player', 'number']
        require(row['source'] == sources[row['table_offset']] and row['status'] == 'reviewed'
                and row['review'], 'Drain source/review differs')
        require(re.findall(r'\{(?!fit\})([^}]+)\}', text) == fields and text.count('{fit}') == 1
                and not any(c in re.sub(r'\{[^}]+\}', '', text) for c in '{}%\n\r'),
                'Drain format fields differ')
        widths = [measure(p.replace('{actor}', '').replace('{player}', '').replace('{number}', '32767'))
                  + p.count('{actor}') * 186 + p.count('{player}') * PLAYER_WIDTH
                  for p in text.split('{fit}')]
        require(max(widths) <= 216, 'Drain fallback width exceeded')
        payload = b''.join(CONTROL if p == '{fit}' else b'%s' if p in ('{actor}', '{player}')
                           else b'%d' if p == '{number}' else encode(p)[:-1]
                           for p in re.split(r'(\{[^}]+\})', text)) + b'\0'
        maximum = len(payload) + (61 if actor else 12 + 3)
        require(maximum <= 256, 'Drain output exceeds256-byte frame')
        offset = build.allocate(row['id'], payload, 'drain-text')
        struct.pack_into('<I', table, row['table_offset'], offset + 0x08000000)
        rows.append(row | {'offset': offset, 'encoded_hex': payload.hex(), 'maximum_bytes': maximum,
                           'maximum_line_widths': widths, 'actor_content_bytes': 63 if actor else 0})
    offset = build.allocate('drain-private-table', bytes(table), 'drain-text')
    for literal in (0x2BB44, 0x2BC40):
        build.patch(f'drain-table-{literal:x}', literal, struct.pack('<I', START + 0x08000000),
                    struct.pack('<I', offset + 0x08000000), 'drain-text')
    return {'entries': rows, 'table_offset': offset, 'catalog_sha256': digest(CATALOG.read_bytes()),
            'scope': catalog['scope']}
