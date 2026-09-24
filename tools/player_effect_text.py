"""Private, player-only effect consumers; no global shared-message replacement."""
import json
import re
import struct
from tools.rom import ROOT, digest, require
from tools.extract_shared_text import START, END, extract
from tools.compact_font import encode, measure
from tools.dialogue_layout import PLAYER_WIDTH

CATALOG = ROOT / 'translations/player-effects-review.json'
# Literal -> offsets used by the fully disassembled owning routine.
OWNERS = {0xB48C: (0x200,), 0xB4B0: (0x7A8,), 0xB4F8: (0x7DC,),
          0xB53C: (0x490,), 0xB588: (0x7A0,), 0xB5CC: (0x498,),
          0xB614: (0x918,), 0xB65C: (0x8F4,), 0xB6AC: (0xE0,),
          0xB6C4: (0x110,), 0xB6DC: (0x118,), 0xB728: (0x7AC,),
          0xB820: (0x3DC,)}

def add_effects(build):
    catalog = json.loads(CATALOG.read_text())
    require(catalog['base_rom_sha256'] == digest(build.original), 'Effect base differs')
    allowed = {offset for values in OWNERS.values() for offset in values}
    require(len(catalog['entries']) == len(allowed)
            and {r['table_offset'] for r in catalog['entries']} == allowed,
            'Unowned player-effect selection')
    sources = {r['table_offset']: r for r in extract()['entries']}
    table = bytearray(build.original[START:END]); entries = []
    for row in catalog['entries']:
        source = sources[row['table_offset']]['source']
        require(row['source'] == source and row['status'] == 'reviewed', 'Effect source/review differs')
        text = row['english']; plain = text.replace('{player}', '')
        require(not any(c in plain for c in '{}%\n\r'), 'Unknown effect format')
        width = measure(plain) + text.count('{player}') * PLAYER_WIDTH
        require(width <= 216, 'Effect cannot fit one line at maximum player width')
        payload = b'%s'.join(encode(p)[:-1] for p in text.split('{player}')) + b'\0'
        require(re.findall(b'%[sd]', bytes.fromhex(source['raw_hex'])) == re.findall(b'%[sd]', payload),
                'Effect arguments changed')
        maximum = len(payload) + text.count('{player}') * 12
        require(maximum <= 256, 'Effect exceeds native output buffer')
        offset = build.allocate(row['id'], payload, 'player-effects')
        struct.pack_into('<I', table, row['table_offset'], offset + 0x08000000)
        entries.append(row | {'offset': offset, 'encoded_hex': payload.hex(),
                              'maximum_width': width, 'maximum_bytes': maximum, 'capacity': 256})
    table_offset = build.allocate('player-effects-table', bytes(table), 'player-effects')
    for site in OWNERS:
        build.patch(f'player-effect-consumer-{site:x}', site,
                    struct.pack('<I', START + 0x08000000),
                    struct.pack('<I', table_offset + 0x08000000), 'player-effects')
    return {'entries': entries, 'table_offset': table_offset, 'consumer_literals': list(OWNERS),
            'catalog_sha256': digest(CATALOG.read_bytes()),
            'scope': 'Thirteen private player-only effect reads. Original shared table and all other consumers remain unchanged. Controlled native branch validation is separate from ordinary item/monster acquisition.'}
