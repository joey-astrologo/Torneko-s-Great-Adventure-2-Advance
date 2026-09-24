"""Isolate three player-only status messages at their audited native consumers."""
import json, re, struct
from tools.rom import ROOT, digest, require
from tools.extract_shared_text import START, END, extract
from tools.compact_font import encode, measure
from tools.dialogue_layout import PLAYER_WIDTH

CATALOG = ROOT / 'translations/player-status-review.json'

def add_player_status(build):
    catalog = json.loads(CATALOG.read_text())
    require(catalog['base_rom_sha256'] == digest(build.original), 'Player-status base differs')
    require({r['table_offset'] for r in catalog['entries']} == {0xE4,0xE8,0x4A0}, 'Unowned player-status selection')
    sources = {r['table_offset']: r for r in extract()['entries']}
    table = bytearray(build.original[START:END]); rows=[]
    for row in catalog['entries']:
        source = sources[row['table_offset']]['source']
        require(row['source'] == source and row['status'] == 'reviewed', 'Player-status source/review differs')
        text = row['english']
        plain = text.replace('{player}', '')
        require(not any(c in plain for c in '{}%\n'), 'Unknown player-status format')
        width = measure(plain) + text.count('{player}') * PLAYER_WIDTH
        require(width <= 216, 'Player status cannot safely fit one line')
        payload = b'%s'.join(encode(part)[:-1] for part in text.split('{player}')) + b'\0'
        require(re.findall(b'%[sd]', bytes.fromhex(source['raw_hex'])) == re.findall(b'%[sd]', payload), 'Status arguments changed')
        maximum = len(payload) + text.count('{player}') * (14-2)
        require(maximum <= 256, 'Player status exceeds native buffer')
        offset = build.allocate(row['id'], payload, 'player-status')
        struct.pack_into('<I', table, row['table_offset'], offset+0x08000000)
        rows.append(row | {'offset': offset, 'encoded_hex': payload.hex(), 'maximum_width': width,
                           'maximum_bytes': maximum, 'capacity': 256})
    table_offset = build.allocate('player-status-table', bytes(table), 'player-status')
    # Each literal is private to one fully disassembled player-only routine.
    # Other shared-table consumers retain the original Japanese pointers.
    for site in (0xB760, 0xB7D8, 0xB7A8):
        build.patch(f'player-status-consumer-{site:x}', site, struct.pack('<I', START+0x08000000),
                    struct.pack('<I', table_offset+0x08000000), 'player-status')
    return {'entries': rows, 'table_offset': table_offset, 'consumer_literals': [0xB760,0xB7D8,0xB7A8],
            'catalog_sha256': digest(CATALOG.read_bytes()), 'scope': 'Player-only hallucination and blindness routines. Other consumers of these shared Japanese sources remain unchanged.'}
