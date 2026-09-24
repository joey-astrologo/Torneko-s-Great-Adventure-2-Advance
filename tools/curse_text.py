"""Owned monster curse notices and bounded actor announcement."""
import json
import struct

from tools.compact_font import encode, load_font, measure
from tools.extract_shared_text import START, END, extract
from tools.inventory_action_text import CONTROL
from tools.rom import ROOT, digest, require

CATALOG = ROOT / 'translations/curse-review.json'


def add_curse(build):
    catalog = json.loads(CATALOG.read_text())
    require(catalog['base_rom_sha256'] == digest(build.original), 'Curse base differs')
    require({r['table_offset'] for r in catalog['entries']} == {0x274, 0x270}
            and len(catalog['entries']) == 2, 'Curse sources differ')
    sources = {r['table_offset']: r['source'] for r in extract()['entries']}
    table, rows, font = bytearray(build.original[START:END]), [], load_font()
    for row in catalog['entries']:
        text, source = row['english'], row['source']
        require(source == sources[row['table_offset']] and row['status'] == 'reviewed' and
                row['review'], 'Curse source/review changed')
        actor = row['table_offset'] == 0x274
        require(text.count('{actor}') == text.count('{fit}') == int(actor) and
                not any(c in text.replace('{actor}', '').replace('{fit}', '') for c in '{}%\n\r'),
                'Curse format/control differs')
        widths = [measure(p.replace('{actor}', ''), font) + p.count('{actor}') * 186
                  for p in text.split('{fit}')]
        require(max(widths) <= 216, 'Curse fallback width exceeded')
        payload = b''
        for i, part in enumerate(text.split('{fit}')):
            if i:
                payload += CONTROL
            fragments = part.split('{actor}')
            payload += b'%s'.join(encode(f)[:-1] for f in fragments)
        payload += b'\0'
        maximum = len(payload) + (61 if actor else 0)
        require(maximum <= 256, 'Curse output exceeds original 256-byte frame')
        offset = build.allocate(row['id'], payload, 'curse-text')
        struct.pack_into('<I', table, row['table_offset'], offset + 0x08000000)
        rows.append(row | {'offset': offset, 'encoded_hex': payload.hex(),
                           'maximum_line_widths': widths, 'maximum_bytes': maximum,
                           'actor_content_bytes': 63 if actor else 0})
    offset = build.allocate('curse-private-table', bytes(table), 'curse-text')
    for literal in (0x2B968, 0x2BA1C):
        build.patch(f'curse-table-{literal:x}', literal, struct.pack('<I', START + 0x08000000),
                    struct.pack('<I', offset + 0x08000000), 'curse-text')
    return {'entries': rows, 'table_offset': offset, 'catalog_sha256': digest(CATALOG.read_bytes()),
            'scope': catalog['scope']}
