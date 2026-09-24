"""Owned bear-trap notices and bounded conditional actor release message."""
import json
import struct

from tools.compact_font import encode, load_font, measure
from tools.extract_shared_text import START, END, extract
from tools.inventory_action_text import CONTROL
from tools.rom import ROOT, digest, require

CATALOG = ROOT / 'translations/bear-trap-review.json'


def add_bear_trap(build):
    catalog = json.loads(CATALOG.read_text())
    require(catalog['base_rom_sha256'] == digest(build.original), 'Bear trap base differs')
    require({r['table_offset'] for r in catalog['entries']} == {0x2DC, 0x2E8, 0x978}
            and len(catalog['entries']) == 3, 'Bear trap sources differ')
    sources = {r['table_offset']: r['source'] for r in extract()['entries']}
    table, rows, font = bytearray(build.original[START:END]), [], load_font()
    for row in catalog['entries']:
        text, source = row['english'], row['source']
        require(source == sources[row['table_offset']] and row['status'] == 'reviewed' and
                row['review'], 'Bear trap source/review changed')
        actor = row['table_offset'] == 0x978
        require(text.count('{actor}') == text.count('{fit}') == int(actor) and
                not any(c in text.replace('{actor}', '').replace('{fit}', '') for c in '{}%\n\r'),
                'Bear trap format/control differs')
        widths = [measure(p.replace('{actor}', ''), font) + p.count('{actor}') * 186
                  for p in text.split('{fit}')]
        require(max(widths) <= 216, 'Bear trap fallback width exceeded')
        payload = b''
        for i, part in enumerate(text.split('{fit}')):
            if i:
                payload += CONTROL
            fragments = part.split('{actor}')
            payload += b'%s'.join(encode(f)[:-1] for f in fragments)
        payload += b'\0'
        maximum = len(payload) + (61 if actor else 0)
        require(maximum <= 256, 'Bear trap output exceeds original 256-byte frame')
        offset = build.allocate(row['id'], payload, 'bear-trap-text')
        struct.pack_into('<I', table, row['table_offset'], offset + 0x08000000)
        rows.append(row | {'offset': offset, 'encoded_hex': payload.hex(),
                           'maximum_line_widths': widths, 'maximum_bytes': maximum,
                           'actor_content_bytes': 63 if actor else 0})
    offset = build.allocate('bear-trap-private-table', bytes(table), 'bear-trap-text')
    build.patch('bear-trap-table-literal', 0x275F4, struct.pack('<I', START + 0x08000000),
                struct.pack('<I', offset + 0x08000000), 'bear-trap-text')
    return {'entries': rows, 'table_offset': offset, 'catalog_sha256': digest(CATALOG.read_bytes()),
            'scope': catalog['scope']}
