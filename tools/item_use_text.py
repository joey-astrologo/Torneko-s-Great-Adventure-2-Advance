"""Private item-use formats with measured joining at their single queue site."""
import json,re,struct,subprocess,tempfile
from pathlib import Path
from tools.rom import ROOT,digest,require
from tools.extract_item_use import START,END,extract
from tools.compact_font import encode,measure
from tools.dialogue_layout import PLAYER_WIDTH

CATALOG=ROOT/'translations/item-use-review.json'

def assemble(address):
    source=f'''.gba
.create "item-use.bin", 0x{address:08x}
.thumb
; Reproduce the private call site's r0=SP, r1=1 before saving its ABI.
    mov r0, sp
    mov r1, 1
    push {{r0-r7,lr}}
    mov r4, r0
    mov r6, r0
    mov r7, 0
scan:
    ldrb r0, [r6]
    add r6, 1
    cmp r0, 0
    beq join
    cmp r0, 13
    beq scan
    cmp r0, 3
    beq colour
    cmp r0, 5
    beq scan
    cmp r0, 0x80
    bls ascii
    cmp r0, 0xA0
    blo pair
    cmp r0, 0xDF
    bls queue
pair:
    lsl r0, r0, 8
    ldrb r1, [r6]
    add r6, 1
    orr r0, r1
    b glyph
ascii:
    cmp r0, 0x30
    blo queue
    cmp r0, 0x39
    bhi queue
    ldr r1, =0x821F
    add r0, r0, r1
glyph:
    ldr r3, =0x08001C71
    bl call_r3
    add r7, r7, r0
    cmp r7, 216
    bhi queue
    b scan
colour:
; Item names carry native colour+parameter and reset controls. Neither advances.
    add r6, 1
    b scan
join:
    mov r5, r4
    mov r6, r4
copy:
    ldrb r0, [r5]
    add r5, 1
    cmp r0, 13
    beq copy
    strb r0, [r6]
    add r6, 1
    cmp r0, 3
    bne copied
; Preserve the colour parameter even when its value is 13 (newline's opcode).
    ldrb r0, [r5]
    add r5, 1
    strb r0, [r6]
    add r6, 1
    b copy
copied:
    cmp r0, 0
    bne copy
queue:
    pop {{r0-r7}}
    pop {{r3}}
    ldr r3, =after_queue+1
    mov lr, r3
    ldr r3, =0x0801588D
    bx r3
after_queue:
; The halfword-aligned ten-byte entry also replaces the original MOV r0,1.
    mov r0, 1
    ldr r3, =0x08025865
    bx r3
call_r3:
    bx r3
    .align 4
    .pool
    .dw after_queue+1
.close
'''
    with tempfile.TemporaryDirectory(prefix='item-use-asm-') as directory:
        folder=Path(directory);(folder/'item-use.asm').write_text(source)
        subprocess.run([str(ROOT/'.tools/bin/armips'),'item-use.asm'],cwd=folder,check=True)
        return (folder/'item-use.bin').read_bytes(),source

def add_item_use(build):
    catalog=json.loads(CATALOG.read_text());extracted=extract()
    require(catalog['base_rom_sha256']==digest(build.original),'Item-use base differs')
    sources={r['source']['offset']:r['source'] for r in extracted['entries']}
    require(len(catalog['entries'])==len(sources)
            and {r['source']['offset'] for r in catalog['entries']}==set(sources),'Item-use review coverage differs')
    table=bytearray(build.original[START:END]);rows=[]
    for row in catalog['entries']:
        source=row['source'];text=row['english']
        require(source==sources[source['offset']] and row['status']=='reviewed','Item-use source/review differs')
        require(text.count('{player}')==text.count('{item}')==1
                and not any(c in text.replace('{player}','').replace('{item}','') for c in '{}%')
                and text.count('\n')==1 and text.split('\n')[0].endswith(' '),'Item-use field/break shape differs')
        parts=re.split(r'(\{player\}|\{item\})',text)
        payload=b''.join(b'%s' if p in ('{player}','{item}') else encode(p)[:-1] for p in parts)+b'\0'
        require(re.findall(b'%[sd]',bytes.fromhex(source['raw_hex']))==[b'%s',b'%s'],'Item-use original arguments differ')
        widths=[measure(line.replace('{player}','').replace('{item}',''))
                +line.count('{player}')*PLAYER_WIDTH+line.count('{item}')*162 for line in text.split('\n')]
        maximum=len(payload)+12+61
        require(max(widths)<=216 and maximum<=256,'Item-use fallback exceeds owned budget')
        offset=build.allocate(row['id'],payload,'item-use')
        categories=[]
        for slot in extracted['entries']:
            if slot['source']==source:
                struct.pack_into('<I',table,slot['category']*4,offset+0x08000000);categories.append(slot['category'])
        rows.append(row|{'offset':offset,'encoded_hex':payload.hex(),'categories':categories,
                         'maximum_formatted_bytes':maximum,'maximum_fallback_widths':widths})
    offset=build.allocate('item-use-table',bytes(table),'item-use')
    build.patch('item-use-table-consumer',0x258D0,struct.pack('<I',START+0x08000000),
                struct.pack('<I',offset+0x08000000),'item-use')
    helper=(len(build.data)+3)&~3;payload,assembly=assemble(helper+0x08000000)
    require(build.allocate('item-use-queue-helper',payload,'item-use')==helper,'Item-use helper moved')
    build.patch('item-use-queue-call',0x2585A,bytes.fromhex('68460121f0f715f80120'),
                bytes.fromhex('014b1847c046')+struct.pack('<I',helper+0x08000001),'item-use')
    return {'entries':rows,'table_offset':offset,'helper_offset':helper,'helper_source':assembly,
            'catalog_sha256':digest(CATALOG.read_bytes()),'extra_stack_bytes':36,
            'queue_return':struct.unpack_from('<I',payload,len(payload)-4)[0],
            'scope':'One player-only item-use consumer: existing 256-byte message and separate 64-byte formatted item. Authored two-line fallback joins only when actual glyph advances fit 216px. Known item/appearance row bounds are 162px; custom inscriptions and special definitions need separate consumer proof.'}
