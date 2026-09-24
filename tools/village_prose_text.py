"""Isolated village-name prose with distinct stack output and name storage."""
import json, struct, subprocess, tempfile
from pathlib import Path
from tools.rom import ROOT, digest, require
from tools.compact_font import encode, measure
from tools.dialogue_layout import compile_dialogue
from tools.text_codec import tokenize
from tools.opening_text import banks, BANK_RAM
from tools.event_text import table_entries
from tools.lz77 import pack_literals, decompress

CATALOG = ROOT/'translations/village-prose-review.json'
CAPACITY = 448
NAME_CAPACITY = 32

def compile_village(row):
    raw = bytes.fromhex(row['source_hex'])
    require(raw.count(b'%s') == row['english'].count('{village}') == 1, 'Village substitution differs')
    # Native producer can emit eight two-byte glyphs (112px), even though
    # the approved player editor currently caps ordinary names at seven.
    sentinel = 'W'*19
    require(sentinel not in row['english'], 'Village sentinel collides')
    payload, layout = compile_dialogue(row['english'].replace('{village}',sentinel),
                                      tokenize(raw.replace(b'%s',b''))[0])
    marker = encode(sentinel)[:-1]
    require(payload.count(marker) == 1, 'Village placeholder split during wrapping')
    payload = payload.replace(marker,b'%s')
    maximum = len(payload)+16-2
    require(maximum <= CAPACITY, 'Village prose exceeds stack capacity')
    widths = [[width-(measure(sentinel)-112)*line.count(sentinel)
               for line,width in zip(page,line_widths)]
              for page,line_widths in zip(layout['pages'],layout['line_widths'])]
    layout.update(pages=[[line.replace(sentinel,'{village}') for line in page] for page in layout['pages']],
                  line_widths=widths,encoded_bytes=len(payload),maximum_formatted_bytes=maximum,
                  capacity=CAPACITY,field_width=112,field_bytes=16)
    return payload,layout

def assemble(address):
    source=f'''.gba
.create "village.bin", 0x{address:08X}
.thumb
    push {{r4-r7,lr}}
    sub sp, 480
    mov r6, r0
    mov r7, r1
    mov r4, sp
    add r5, sp, 448
    mov r0, 0
    mov r1, 0
clear_name:
    strb r0, [r5,r1]
    add r1, 1
    cmp r1, 32
    blt clear_name
    mov r0, r5
    ldr r3, =0x08041FD5
    bl call_r3
name_ready:
    mov r0, r6
    mov r1, r7
    ldr r3, =0x08050271
    bl call_r3
    mov r1, r0
    mov r0, r4
    mov r2, r5
    ldr r3, =0x08000FB9
    bl call_r3
formatted:
    mov r0, r4
    ldr r3, =0x080503F9
    bl call_r3
    add sp, 480
    pop {{r4-r7}}
    pop {{r0}}
returned:
    bx r0
call_r3:
    bx r3
    .align 4
    .pool
    .word name_ready, formatted, returned
.close
'''
    with tempfile.TemporaryDirectory(prefix='village-prose-asm-') as folder:
        path=Path(folder);(path/'village.asm').write_text(source)
        subprocess.run([str(ROOT/'.tools/bin/armips'),'village.asm'],cwd=folder,check=True)
        payload=(path/'village.bin').read_bytes()
    return payload,source,struct.unpack('<III',payload[-12:])

def add_village_prose(build,bank_data=None,changed_by_bank=None):
    catalog=json.loads(CATALOG.read_text())
    require(catalog['base_rom_sha256']==digest(build.original),'Village prose base differs')
    selected={r['id']:r for r in catalog['entries']}
    require(set(selected)=={'event-bank-5.4a81','event-bank-5.a5c2','event-bank-6.7d09'},'Unowned village prose selection')
    rows,reports=[],[]
    for bank in banks()[5:7]:
        data=bytearray(bank['data']) if bank_data is None else bank_data[bank['id']];slots=[]
        for entry in table_entries(bank):
            if entry['id'] not in selected:continue
            row=selected[entry['id']];raw=bank['data'][entry['start']:entry['end_exclusive']]
            require(row['status']=='reviewed' and row['prose_review'] and raw.hex()==row['source_hex']
                    and digest(raw)==row['source_sha256'],'Village prose source/review differs')
            payload,layout=compile_village(row);offset=build.allocate(row['id'],payload,'village-prose-prototype')
            relative=(offset+0x08000000-(BANK_RAM+entry['strings_offset']+entry['group_offset']))&0xFFFFFFFF
            require(struct.unpack_from('<I',data,entry['slot'])[0]==entry['relative'],'Village slot already owned')
            struct.pack_into('<I',data,entry['slot'],relative);slots.append(entry['slot'])
            rows.append(row|{'offset':offset,'encoded_hex':payload.hex(),'layout':layout,
                             'bank':bank['id'],'group':entry['group'],'index':entry['index']})
        require(len(slots)==(2 if bank['index']==5 else 1),'Missing village prose slot')
        offset=None
        if bank_data is None:
            restored=bytearray(data)
            for slot in slots:restored[slot:slot+4]=bank['data'][slot:slot+4]
            require(restored==bank['data'],'Unowned village bank change')
            packed=pack_literals(data);require(decompress(packed)==(bytes(data),len(packed)),'Village bank packing differs')
            offset=build.allocate('village-'+bank['id'],packed,'village-prose-prototype')
            build.patch('village-'+bank['id']+'-pointer',bank['pointer_offset'],struct.pack('<I',bank['rom_offset']+0x08000000),
                        struct.pack('<I',offset+0x08000000),'village-prose-prototype')
        else:
            require(changed_by_bank is not None,'Shared village bank needs its slot ledger')
            changed_by_bank[bank['id']].extend(slots)
        reports.append({'id':bank['id'],'offset':offset,'changed_slots':slots,'new_ram_bytes':0})
    offset=(len(build.data)+3)&~3
    payload,source,points=assemble(offset+0x08000000)
    require(build.allocate('village-prose-helper',payload,'village-prose-prototype')==offset,'Village helper moved')
    build.patch('village-prose-entry',0x50BC4,bytes.fromhex('f0b5061c0f1c0021'),
                bytes.fromhex('004b1847')+struct.pack('<I',offset+0x08000001),'village-prose-prototype')
    return {'entries':rows,'banks':reports,'capacity':CAPACITY,'name_capacity':NAME_CAPACITY,
            'helper_offset':offset,'name_ready':points[0],'formatted':points[1],'returned':points[2],
            'helper_source':source,'review_sha256':digest(CATALOG.read_bytes())}
