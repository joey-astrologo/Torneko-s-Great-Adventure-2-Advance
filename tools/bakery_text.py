"""Seven reviewed bakery resources, with original native window geometry."""
import json, re, struct
from tools.rom import ROOT, load_base, digest, require
from tools.rom_build import RomBuild
from tools.build_compact_font import add_font
from tools.name_entry import add_name_entry
from tools.item_text import add_items
from tools.compact_font import encode, measure
from tools.dialogue_layout import compile_dialogue
from tools.town_text import resource, entries, RELOCATION
from tools.lz77 import pack_literals, decompress

CATALOG = ROOT / 'translations/bakery-review.json'

def compile_row(row, source):
    text = row['english']
    if row['index'] == 101:
        require(text == ['Bread', 'Giant bread', 'Magic bread', 'Leave'], 'Bakery choices changed')
        lines = [b'\x06\x0c' + encode(name)[:-1] + b'\x06\x80' + encode(str(price) + 'G')[:-1]
                 for name, price in zip(text[:3], (100, 300, 400))]
        lines.append(b'\x06\x0c' + encode(text[3])[:-1])
        widths = [128 + measure(str(price) + 'G') for price in (100, 300, 400)] + [12 + measure(text[3])]
        require(all(12 + measure(name) <= 120 for name in text[:3]) and max(widths) <= 168, 'Bakery columns overlap')
        return b'\r'.join(lines) + b'\0', {'pages': [text], 'line_widths': [widths], 'native_width': 176,
                                             'native_rows': 4, 'column_starts': [12, 128], 'direct_rom_stream': True}
    if row['index'] != 103:
        payload, layout = compile_dialogue(text, source['tokens'])
        return payload, layout | {'native_width': 224, 'direct_rom_stream': True}
    fields = {'{item}': (b'%s', 80, 30), '{price}': (b'\x03\x05%d\x05', 21, 3)}
    require(text.count('{item}') == text.count('{price}') == 1, 'Bakery substitutions differ')
    widths = []
    for line in text.split('\n'):
        plain = line
        width = 0
        for marker, (_, reserve, _) in fields.items():
            width += reserve * plain.count(marker)
            plain = plain.replace(marker, '')
        require(not any(c in plain for c in '{}%'), 'Unknown bakery format')
        widths.append(measure(plain) + width)
    require(len(widths) <= 2 and max(widths) <= 216, 'Bakery confirmation exceeds page')
    payload = b''.join(fields[part][0] if part in fields else encode(part)[:-1]
                       for part in re.split(r'(\{item\}|\{price\})', text)) + b'\0'
    maximum = len(payload) + 30 - 2 + 3 - 2
    require(maximum <= 256, 'Bakery format exceeds native stack buffer')
    return payload, {'pages': [text.split('\n')], 'line_widths': [widths], 'native_width': 224,
                     'maximum_formatted_bytes': maximum, 'capacity': 256, 'price_digits': 3}

def insert_bakery(build, decoded, bank):
    catalog = json.loads(CATALOG.read_text())
    require(catalog['base_rom_sha256'] == digest(build.original), 'Bakery source ROM differs')
    table = {r['index']: r for r in entries()}
    rows, slots = [], []
    require({r['index'] for r in catalog['entries']} == {100,101,102,103,104,106,107}, 'Unowned bakery slot selection')
    for row in catalog['entries']:
        require(row['status'] == 'reviewed', 'Unreviewed bakery text')
        source = table[row['index']]
        raw = bank['data'][source['start']:source['end_exclusive']]
        require(raw.hex() == row['source_hex'] and digest(raw) == row['source_sha256'], 'Bakery source changed')
        payload, layout = compile_row(row, source)
        require(re.findall(b'%[sd]', raw) == re.findall(b'%[sd]', payload), 'Bakery format order changed')
        offset = build.allocate(row['id'], payload, 'bakery-services')
        slot = source['slot']
        require(struct.unpack_from('<I', decoded, slot)[0] == source['linked_pointer'], 'Bakery slot already changed')
        struct.pack_into('<I', decoded, slot, (offset + 0x08000000 - RELOCATION) & 0xFFFFFFFF)
        slots.append(slot)
        rows.append(row | {'offset': offset, 'encoded_hex': payload.hex(), 'layout': layout, 'slot':slot})
    return rows, slots, digest(CATALOG.read_bytes())
