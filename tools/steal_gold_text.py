"""Gold theft formats preserving native argument order and field capacities."""
import json
import re
import struct
from tools.compact_font import encode, measure
from tools.dialogue_layout import PLAYER_WIDTH
from tools.extract_shared_text import START, END, extract
from tools.inventory_action_text import CONTROL
from tools.rom import ROOT, digest, require
CATALOG = ROOT / 'translations/steal-gold-review.json'


def add_steal_gold(build):
    catalog = json.loads(CATALOG.read_text())
    require(catalog['base_rom_sha256'] == digest(build.original), 'Gold theft base differs')
    args = {0x2B0: ['actor', 'player', 'amount'], 0x2B4: ['number'], 0x710: ['actor', 'kind'], 0x714: []}
    require(len(catalog['entries']) == 4 and {r['table_offset'] for r in catalog['entries']} == set(args),
            'Gold theft sources differ')
    sources = {r['table_offset']: r['source'] for r in extract()['entries']}
    bounds = {'actor': (186, 63), 'player': (PLAYER_WIDTH, 14), 'amount': (measure('99999999G'), 10),
              'number': (measure('99999999'), 8), 'kind': (measure('gold'), len(encode('gold')) - 1)}
    table, rows = bytearray(build.original[START:END]), []
    for row in catalog['entries']:
        text, slot = row['english'], row['table_offset']
        require(row['source'] == sources[slot] and row['status'] == 'reviewed' and row['review'],
                'Gold theft source/review differs')
        require(re.findall(r'\{(?!fit\})([^}]+)\}', text) == args[slot] and
                text.count('{fit}') == int(slot in (0x2B0, 0x710)) and
                not any(c in re.sub(r'\{[^}]+\}', '', text) for c in '{}%\r\n'), 'Gold theft fields differ')
        widths = [measure(re.sub(r'\{[^}]+\}', '', p)) +
                  sum(p.count('{'+field+'}') * bounds[field][0] for field in args[slot])
                  for p in text.split('{fit}')]
        payload = b''.join(CONTROL if p == '{fit}' else b'%d' if p == '{number}' else b'%s'
                           if p.startswith('{') else encode(p)[:-1] for p in re.split(r'(\{[^}]+\})', text)) + b'\0'
        maximum = len(payload) + sum(bounds[field][1] - 2 for field in args[slot])
        capacity = 64 if slot == 0x2B4 else 256
        require(max(widths) <= 216 and maximum <= capacity, 'Gold theft output exceeds budgets')
        offset = build.allocate(row['id'], payload, 'steal-gold-text')
        struct.pack_into('<I', table, slot, offset + 0x08000000)
        rows.append(row | {'offset': offset, 'encoded_hex': payload.hex(), 'maximum_bytes': maximum,
                           'maximum_line_widths': widths, 'capacity': capacity})
    offset = build.allocate('steal-gold-private-table', bytes(table), 'steal-gold-text')
    for literal in (0x2BD38, 0x2BD84, 0x2BE58):
        build.patch(f'steal-gold-table-{literal:x}', literal, struct.pack('<I', START + 0x08000000),
                    struct.pack('<I', offset + 0x08000000), 'steal-gold-text')
    return {'entries': rows, 'table_offset': offset, 'catalog_sha256': digest(CATALOG.read_bytes()),
            'scope': catalog['scope']}
