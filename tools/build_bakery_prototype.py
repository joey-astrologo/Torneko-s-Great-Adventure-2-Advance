"""Isolated native bakery text candidate; cumulative English build is untouched."""
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

OUT = ROOT / 'build/bakery-prototype'
CATALOG = ROOT / 'translations/bakery-prototype.json'

from tools.bakery_text import compile_row

def build_rom():
    build = RomBuild(load_base())
    font = add_font(build, compact_numbers=True)
    name = add_name_entry(build)
    items = add_items(build)
    bank = resource()
    decoded = bytearray(bank['data'])
    catalog = json.loads(CATALOG.read_text())
    require(catalog['base_rom_sha256'] == digest(build.original), 'Bakery source ROM differs')
    table = {r['index']: r for r in entries()}
    rows, slots = [], []
    for row in catalog['entries']:
        source = table[row['index']]
        raw = bank['data'][source['start']:source['end_exclusive']]
        require(raw.hex() == row['source_hex'] and digest(raw) == row['source_sha256'], 'Bakery source changed')
        payload, layout = compile_row(row, source)
        require(re.findall(b'%[sd]', raw) == re.findall(b'%[sd]', payload), 'Bakery format order changed')
        offset = build.allocate(row['id'], payload, 'bakery-prototype')
        slot = source['slot']
        require(struct.unpack_from('<I', decoded, slot)[0] == source['linked_pointer'], 'Bakery slot already changed')
        struct.pack_into('<I', decoded, slot, (offset + 0x08000000 - RELOCATION) & 0xFFFFFFFF)
        slots.append(slot)
        rows.append(row | {'offset': offset, 'encoded_hex': payload.hex(), 'layout': layout})
    restored = bytearray(decoded)
    for slot in slots:
        restored[slot:slot+4] = bank['data'][slot:slot+4]
    require(restored == bank['data'], 'Unowned town bytes changed')
    packed = pack_literals(decoded)
    require(decompress(packed) == (bytes(decoded), len(packed)), 'Town packing differs')
    offset = build.allocate('bakery-town-resource', packed, 'bakery-prototype')
    build.patch('bakery-town-pointer', bank['pointer_offset'], struct.pack('<I', 0x08000000 + bank['rom_offset']),
                struct.pack('<I', 0x08000000 + offset), 'bakery-prototype')
    rom, report = build.finish()
    return rom, report | {'font': font, 'name_entry': name, 'items': items, 'bakery': rows,
                          'catalog_sha256': digest(CATALOG.read_bytes()), 'town_slots': slots,
                          'scope': 'Isolated candidate, seven bakery slots; native unlock and cumulative acceptance pending.'}

def run():
    rom, report = build_rom()
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'game.gba').write_bytes(rom)
    (OUT / 'build.json').write_text(json.dumps(report, indent=2) + '\n')
    print(report['output_sha256'])

if __name__ == '__main__':
    run()
