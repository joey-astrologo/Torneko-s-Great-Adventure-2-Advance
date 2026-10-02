"""Own the computed timer-expiry reader without changing other shared-table users."""
import json
import re
import struct

from tools.compact_font import encode, measure
from tools.dialogue_layout import PLAYER_WIDTH
from tools.extract_shared_text import START, END, extract
from tools.inventory_action_text import CONTROL
from tools.rom import ROOT, digest, require

CATALOG = ROOT / 'translations/status-expiry-review.json'
SLOTS = {0x17C, 0x180, 0x184, 0x188, 0x3C0, 0x3E0, 0x8FC}
LITERAL = 0x9748


def add_status_expiry(build, players, monsters):
    catalog = json.loads(CATALOG.read_text())
    sources = {r['table_offset']: r['source'] for r in extract()['entries']}
    require(catalog['base_rom_sha256'] == digest(build.original) and
            len(catalog['entries']) == len(SLOTS) and
            {r['table_offset'] for r in catalog['entries']} == SLOTS,
            'Status-expiry source cohort differs')
    # Getter 09ACC(0) returns HERO, or a base monster name while transformed.
    field_width = max(PLAYER_WIDTH, *(measure(r['english']) for r in monsters['entries']))
    field_bytes = max(14, *(len(bytes.fromhex(r['encoded_hex'])) - 1 for r in monsters['entries']))
    expected = {
        0x90CC: '60fcffff',  # Native 0x3A0 local frame.
        0x96C4: '14af204da94604a88046251c414604318846043901c9800048440468002000f0f3f9021c381c211cf7f764fc381cd4990cf0caf80022d492013d002de6d1',
        0x9786: '54ac',  # Next scratch at SP+150; expiry output starts SP+50.
        0x9B0C: '583b0002',  # Normal name is HERO.
    }
    for address, raw in expected.items():
        require(build.original[address:address+len(bytes.fromhex(raw))].hex() == raw,
                'Status-expiry code/buffer ownership differs')
    table = bytearray(build.original[START:END])
    prior = {r['table_offset']: r for r in players['entries']}
    rows = []
    for row in catalog['entries']:
        slot, text = row['table_offset'], row['english']
        require(row['status'] == 'reviewed' and row['source'] == sources[slot] and
                struct.unpack_from('<I', table, slot)[0] == 0x08000000 + sources[slot]['offset'],
                'Status-expiry source review differs')
        require(text.count('{player}') == 1 and text.count('{fit}') <= 1 and
                not any(c in text.replace('{player}', '').replace('{fit}', '') for c in '{}%\r\n') and
                re.findall(b'%[sd]', bytes.fromhex(sources[slot]['raw_hex'])) == [b'%s'],
                'Status-expiry arguments/controls differ')
        widths = [measure(p.replace('{player}', '')) + field_width * p.count('{player}')
                  for p in text.split('{fit}')]
        require(max(widths) <= 216 and ('{fit}' not in text or sum(widths) > 216),
                'Status-expiry line budget/conditional break differs')
        payload = b''.join(b'%s' if p == '{player}' else CONTROL if p == '{fit}' else encode(p)[:-1]
                           for p in re.split(r'(\{[^{}]+\})', text)) + b'\0'
        maximum = len(payload) - 2 + field_bytes
        require(maximum <= 256, 'Status-expiry output exceeds native buffer')
        reused = slot in prior and prior[slot]['encoded_hex'] == payload.hex()
        offset = prior[slot]['offset'] if reused else build.allocate(row['id'], payload, 'status-expiry')
        require(build.data[offset:offset+len(payload)] == payload, 'Expiry payload differs')
        struct.pack_into('<I', table, slot, 0x08000000 + offset)
        rows.append(row | {'offset': offset, 'encoded_hex': payload.hex(), 'maximum_bytes': maximum,
                          'maximum_line_widths': widths, 'capacity': 256, 'field_width': field_width,
                          'field_content_bytes': field_bytes, 'reused_payload': reused,
                          'new_source': slot not in prior})
    offset = build.allocate('status-expiry-private-table', bytes(table), 'status-expiry')
    build.patch('status-expiry-table-literal', LITERAL, struct.pack('<I', START + 0x08000000),
                struct.pack('<I', offset + 0x08000000), 'status-expiry')
    return {'entries': rows, 'table_offset': offset, 'table_bytes': END - START,
            'new_source_count': sum(r['new_source'] for r in rows),
            'catalog_sha256': digest(CATALOG.read_bytes()), 'scope': catalog['scope']}
