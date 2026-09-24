"""Private level-drain results with seven-character player-name bounds."""
import json
import struct
from tools.compact_font import encode, measure
from tools.dialogue_layout import PLAYER_WIDTH
from tools.extract_shared_text import START, END, extract
from tools.rom import ROOT, digest, require
CATALOG = ROOT / 'translations/level-drain-review.json'


def add_level_drain(build):
    catalog = json.loads(CATALOG.read_text())
    require(catalog['base_rom_sha256'] == digest(build.original), 'Level drain base differs')
    require(len(catalog['entries']) == 3 and {r['table_offset'] for r in catalog['entries']} ==
            {0xEC, 0x904, 0xC8}, 'Level drain sources differ')
    sources = {r['table_offset']: r['source'] for r in extract()['entries']}
    table, rows = bytearray(build.original[START:END]), []
    for row in catalog['entries']:
        text = row['english']
        player = row['table_offset'] != 0xC8
        require(row['source'] == sources[row['table_offset']] and row['status'] == 'reviewed'
                and row['review'], 'Level drain source/review differs')
        require(text.count('{player}') == int(player) and not any(c in text.replace('{player}', '')
                for c in '{}%\n\r'), 'Level drain format differs')
        width = measure(text.replace('{player}', '')) + PLAYER_WIDTH * player
        payload = b'%s'.join(encode(p)[:-1] for p in text.split('{player}')) + b'\0'
        maximum = len(payload) + 12 * player
        require(width <= 216 and maximum <= 256, 'Level drain output budget exceeded')
        offset = build.allocate(row['id'], payload, 'level-drain-text')
        struct.pack_into('<I', table, row['table_offset'], offset + 0x08000000)
        rows.append(row | {'offset': offset, 'encoded_hex': payload.hex(), 'maximum_bytes': maximum,
                           'maximum_line_widths': [width]})
    offset = build.allocate('level-drain-private-table', bytes(table), 'level-drain-text')
    for literal in (0x2BC8C, 0x2BCC0, 0x2BCE8):
        build.patch(f'level-drain-table-{literal:x}', literal, struct.pack('<I', START + 0x08000000),
                    struct.pack('<I', offset + 0x08000000), 'level-drain-text')
    return {'entries': rows, 'table_offset': offset, 'catalog_sha256': digest(CATALOG.read_bytes()),
            'scope': catalog['scope']}
