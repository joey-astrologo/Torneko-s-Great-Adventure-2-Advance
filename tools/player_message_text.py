"""Translate a closed source-pointer set only in the native player-name formatter."""
import json,re,struct,subprocess,tempfile
from pathlib import Path
from tools.rom import ROOT,digest,require
from tools.extract_shared_text import extract
from tools.compact_font import encode,measure
from tools.dialogue_layout import PLAYER_WIDTH
from tools.inventory_action_text import CONTROL

CATALOG=ROOT/'translations/player-messages-review.json'
SLOTS={0x3C0,0x354,0x884,0x198,0x76C,0x474,0x2E0,0x364,0x2D8,0x308,0x7D4,0x7D8,
       0x2FC,0x2BC,0x190,0x4AC,0x108,0x10C,0x188,0x17C,0x180,0x8FC,0x178,0x990,
       0x194,0xE0,0x118,0x528,0x218,0x3B4,0x888,0x174,0x890}

def add_player_messages(build):
    catalog=json.loads(CATALOG.read_text());sources={r['table_offset']:r['source'] for r in extract()['entries']}
    require(catalog['base_rom_sha256']==digest(build.original),'Player formatter base differs')
    require(len(catalog['entries'])==len(SLOTS) and {r['table_offset'] for r in catalog['entries']}==SLOTS,
            'Player formatter source selection differs')
    rows=[];mapping=bytearray();original_pointers=set()
    for row in catalog['entries']:
        source=sources[row['table_offset']];text=row['english'];plain=text.replace('{player}','').replace('{fit}','')
        require(row['status']=='reviewed' and row['source']==source,'Player formatter source review differs')
        require(not any(c in plain for c in '{}%\n\r') and text.count('{player}')<=1 and text.count('{fit}')<=1,
                'Unsupported player formatter controls/arguments')
        fields=re.findall(b'%[sd]',bytes.fromhex(source['raw_hex']))
        require(fields==[b'%s']*text.count('{player}'),'Player formatter source arguments differ')
        widths=[measure(p.replace('{player}',''))+PLAYER_WIDTH*p.count('{player}') for p in text.split('{fit}')]
        require(max(widths)<=216,'Player formatter width exceeds216px')
        require('{fit}' not in text or sum(widths)>216,'Needless conditional break in a bounded one-line message')
        payload=bytearray()
        for part in re.split(r'(\{[^{}]+\})',text):
            payload.extend(b'%s' if part=='{player}' else CONTROL if part=='{fit}' else encode(part)[:-1])
        payload.append(0);payload=bytes(payload);maximum=len(payload)+12*text.count('{player}')
        require(maximum<=256,'Player formatter output exceeds256-byte buffer')
        for call in row['calls']:
            address=call['address']-0x08000000;raw=build.original[address:address+4]
            require(raw.hex()==call['original_hex'],'Player formatter call-site bytes differ')
            hi,lo=struct.unpack('<HH',raw);delta=((hi&0x7FF)<<12)|((lo&0x7FF)<<1)
            if delta&0x400000:delta-=0x800000
            require(hi&0xF800==0xF000 and lo&0xF800==0xF800 and address+4+delta==0x15848,
                    'Player formatter call-site target differs')
        offset=build.allocate(row['id'],payload,'player-message-wrapper');pointer=source['offset']+0x08000000
        require(pointer not in original_pointers,'Duplicate player wrapper source pointer');original_pointers.add(pointer)
        mapping.extend(struct.pack('<II',pointer,offset+0x08000000))
        rows.append(row|{'offset':offset,'encoded_hex':payload.hex(),'maximum_line_widths':widths,
                         'maximum_bytes':maximum,'capacity':256,'player_width':PLAYER_WIDTH,'player_content_bytes':14})
    table=build.allocate('player-message-pointer-map',bytes(mapping),'player-message-wrapper')
    helper=(len(build.data)+3)&~3
    assembly=f'''.gba
.create "player-messages.bin", 0x{helper+0x08000000:08x}
.thumb
; Preserve the original 12-byte save and 256-byte local frame.
    push {{r4,r5,lr}}
    sub sp, 0x100
    mov r4, r0
    mov r5, r1
    ldr r0, =0x{table+0x08000000:08x}
    mov r1, {len(rows)}
scan:
    ldr r2, [r0]
    cmp r4, r2
    beq found
    add r0, 8
    sub r1, 1
    bne scan
    b resume
found:
    ldr r4, [r0,4]
resume:
; Unmapped original, RAM and already-English pointers remain untouched.
    ldr r3, =0x08015851
    bx r3
    .align 4
    .pool
.close
'''
    with tempfile.TemporaryDirectory(prefix='player-messages-asm-') as directory:
        folder=Path(directory);(folder/'player-messages.asm').write_text(assembly)
        subprocess.run([str(ROOT/'.tools/bin/armips'),'player-messages.asm'],cwd=folder,check=True)
        payload=(folder/'player-messages.bin').read_bytes()
    require(build.allocate('player-message-entry-helper',payload,'player-message-wrapper')==helper,'Player helper alignment differs')
    build.patch('player-message-entry',0x15848,bytes.fromhex('30b5c0b0041c0d1c'),
                bytes.fromhex('004b1847')+struct.pack('<I',helper+0x08000001),'player-message-wrapper')
    return {'entries':rows,'mapping_offset':table,'helper_offset':helper,'assembly':assembly,
            'catalog_sha256':digest(CATALOG.read_bytes()),'scope':catalog['scope']}
