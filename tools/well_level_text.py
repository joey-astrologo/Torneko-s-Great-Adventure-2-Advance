"""Isolated well-level acknowledgement with private labels and bounded storage."""
import json, struct, subprocess, tempfile
from pathlib import Path
from tools.rom import ROOT, digest, require
from tools.compact_font import encode, measure
from tools.dialogue_layout import compile_dialogue
from tools.text_codec import tokenize
from tools.opening_text import banks, BANK_RAM
from tools.event_text import table_entries
from tools.lz77 import pack_literals, decompress

CATALOG = ROOT/'translations/well-level-review.json'
CAPACITY = 256

def compile_acknowledgement(row, labels):
    raw = bytes.fromhex(row['source_hex'])
    require(raw.count(b'%s') == row['english'].count('{difficulty}') == 1,
            'Well acknowledgement substitution differs')
    sentinel = 'WWWWWWWW'
    require(sentinel not in row['english'], 'Well sentinel collides')
    maximum_width = max(measure(label['english']) for label in labels)
    maximum_bytes = max(len(encode(label['english']))-1 for label in labels)
    require(maximum_width <= measure(sentinel), 'Well label exceeds wrapping reserve')
    payload, layout = compile_dialogue(row['english'].replace('{difficulty}', sentinel),
                                      tokenize(raw.replace(b'%s', b''))[0])
    marker = encode(sentinel)[:-1]
    require(payload.count(marker) == 1, 'Well substitution split during wrapping')
    payload = payload.replace(marker, b'%s')
    maximum = len(payload) + maximum_bytes - 2
    require(maximum <= CAPACITY, 'Well acknowledgement exceeds stack capacity')
    widths = [[width-(measure(sentinel)-maximum_width)*line.count(sentinel)
               for line, width in zip(page, line_widths)]
              for page, line_widths in zip(layout['pages'], layout['line_widths'])]
    layout.update(pages=[[line.replace(sentinel, '{difficulty}') for line in page]
                         for page in layout['pages']], line_widths=widths,
                  encoded_bytes=len(payload), maximum_formatted_bytes=maximum,
                  capacity=CAPACITY, field_width=maximum_width, field_bytes=maximum_bytes)
    return payload, layout

def assemble(address, labels):
    source = f'''.gba
.create "well.bin", 0x{address:08X}
.thumb
    push {{r4,lr}}
    sub sp, 0x100
    mov r4, sp
    ldr r3, =0x08050271
    bl call_r3
    mov r1, r0
    ldr r0, =0x02005674
    mov r3, 0
    ldsh r0, [r0,r3]
    sub r0, 1
    lsl r0, r0, 2
    ldr r2, =0x{labels:08X}
    ldr r2, [r2,r0]
    mov r0, r4
    ldr r3, =0x08000FB9
    bl call_r3
formatted:
    mov r0, r4
    ldr r3, =0x080503F9
    bl call_r3
    ldr r2, =0x0201020C
    ldrb r0, [r2,2]
    mov r1, 4
    orr r0, r1
    strb r0, [r2,2]
    add sp, 0x100
    pop {{r4}}
    pop {{r0}}
returned:
    bx r0
call_r3:
    bx r3
    .align 4
    .pool
    .word formatted, returned
.close
'''
    with tempfile.TemporaryDirectory(prefix='well-level-asm-') as folder:
        path = Path(folder); (path/'well.asm').write_text(source)
        subprocess.run([str(ROOT/'.tools/bin/armips'), 'well.asm'], cwd=folder, check=True)
        payload = (path/'well.bin').read_bytes()
    formatted, returned = struct.unpack('<II', payload[-8:])
    return payload, source, formatted, returned

def add_well_level(build, bank_data=None, changed_by_bank=None):
    catalog = json.loads(CATALOG.read_text())
    require(catalog['base_rom_sha256'] == digest(build.original), 'Well base differs')
    require([r['value'] for r in catalog['labels']] == list(range(1, 11)), 'Well levels incomplete')
    labels = []
    for row in catalog['labels']:
        start = row['source_offset']; raw = bytes.fromhex(row['source_hex'])
        require(row['status'] == 'reviewed' and build.original[start:start+len(raw)] == raw
                and digest(raw) == row['source_sha256'], 'Well label source/review differs')
        require(struct.unpack_from('<I', build.original, 0x14D354+4*(row['value']-1))[0]
                == start+0x08000000, 'Well original level table differs')
        payload = encode(row['english'])
        offset = build.allocate(row['id'], payload, 'well-level-prototype')
        labels.append(row | {'offset': offset, 'encoded_hex': payload.hex()})
    table = build.allocate('well-level-private-table', b''.join(struct.pack('<I', r['offset']+0x08000000)
                                                             for r in labels), 'well-level-prototype')
    selected = {r['id']: r for r in catalog['entries']}
    require(set(selected) == {'event-bank-5.3c32', 'event-bank-6.2e6e'}, 'Unowned well prose selection')
    rows, reports = [], []
    for bank in banks()[5:7]:
        data = bytearray(bank['data']) if bank_data is None else bank_data[bank['id']]
        slots = []
        for entry in table_entries(bank):
            if entry['id'] not in selected: continue
            row = selected[entry['id']]; raw = bank['data'][entry['start']:entry['end_exclusive']]
            require(row['status'] == 'reviewed' and row['prose_review'] and raw.hex() == row['source_hex']
                    and digest(raw) == row['source_sha256'], 'Well prose source/review differs')
            payload, layout = compile_acknowledgement(row, labels)
            offset = build.allocate(row['id'], payload, 'well-level-prototype')
            relative = (offset+0x08000000-(BANK_RAM+entry['strings_offset']+entry['group_offset'])) & 0xFFFFFFFF
            require(struct.unpack_from('<I',data,entry['slot'])[0] == entry['relative'], 'Well slot already owned')
            struct.pack_into('<I', data, entry['slot'], relative); slots.append(entry['slot'])
            rows.append(row | {'offset': offset, 'encoded_hex': payload.hex(), 'layout': layout,
                               'bank': bank['id'], 'group': entry['group'], 'index': entry['index']})
        require(len(slots) == 1, 'Expected one well acknowledgement per bank')
        offset = None
        if bank_data is None:
            restored = bytearray(data)
            for slot in slots: restored[slot:slot+4] = bank['data'][slot:slot+4]
            require(restored == bank['data'], 'Unowned well bank change')
            packed = pack_literals(data); require(decompress(packed) == (bytes(data),len(packed)), 'Well bank packing differs')
            offset = build.allocate('well-'+bank['id'], packed, 'well-level-prototype')
            build.patch('well-'+bank['id']+'-pointer', bank['pointer_offset'],
                        struct.pack('<I', bank['rom_offset']+0x08000000),
                        struct.pack('<I', offset+0x08000000), 'well-level-prototype')
        else:
            require(changed_by_bank is not None, 'Shared well bank needs its slot ledger')
            changed_by_bank[bank['id']].extend(slots)
        reports.append({'id': bank['id'], 'offset': offset, 'changed_slots': slots, 'new_ram_bytes': 0})
    offset = (len(build.data)+3) & ~3
    payload, source, formatted, returned = assemble(offset+0x08000000, table+0x08000000)
    require(build.allocate('well-acknowledgement-helper', payload, 'well-level-prototype') == offset,
            'Well helper moved')
    build.patch('well-acknowledgement-entry', 0x50C14, bytes.fromhex('10b50d4cfff72afb'),
                bytes.fromhex('004b1847')+struct.pack('<I', offset+0x08000001), 'well-level-prototype')
    return {'entries': rows, 'labels': labels, 'banks': reports, 'capacity': CAPACITY,
            'helper_offset': offset, 'formatted': formatted, 'returned': returned,
            'helper_source': source, 'review_sha256': digest(CATALOG.read_bytes())}
