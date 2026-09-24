"""Isolated medal formatter storage and reviewed total/reward messages."""
import json,re,struct,subprocess,tempfile
from pathlib import Path
from tools.rom import ROOT,digest,require
from tools.compact_font import encode,measure
from tools.dialogue_layout import compile_dialogue
from tools.text_codec import tokenize
from tools.opening_text import banks,BANK_RAM
from tools.event_text import table_entries
from tools.lz77 import pack_literals,decompress

CATALOG=ROOT/'translations/medal-review.json'
CAPACITY=480
FORMATTED={3,4,7,10,11,12,13}

def compile_medal(row,index):
    raw=bytes.fromhex(row['source_hex']);fields=re.findall(rb'%[-0-9]*l?d',raw)
    require(len(fields)==row['english'].count('{medals}') and len(fields)<=1,'Medal substitution differs')
    sentinel='WWWW';require(sentinel not in row['english'],'Medal sentinel collides')
    payload,layout=compile_dialogue(row['english'].replace('{medals}',sentinel),
                                  tokenize(re.sub(rb'%[-0-9]*l?d',b'',raw))[0])
    marker=encode(sentinel)[:-1];require(payload.count(marker)==len(fields),'Medal field split during wrapping')
    payload=payload.replace(marker,b'%d');maximum=len(payload)+len(fields)
    require(index not in FORMATTED or maximum<=CAPACITY,'Medal message exceeds owned stack capacity')
    widths=[[width-(measure(sentinel)-21)*line.count(sentinel) for line,width in zip(page,line_widths)]
            for page,line_widths in zip(layout['pages'],layout['line_widths'])]
    layout.update(pages=[[line.replace(sentinel,'{medals}') for line in page] for page in layout['pages']],
                  line_widths=widths,encoded_bytes=len(payload),maximum_formatted_bytes=maximum,
                  capacity=CAPACITY if index in FORMATTED else None,medal_range=[0,999])
    return payload,layout

def assemble(address):
    source=f'''.gba
.create "medal.bin", 0x{address:08X}
.thumb
entry:
    push {{r4-r7,lr}}
    mov r7, r10
    mov r6, r9
    mov r5, r8
    push {{r5-r7}}
    sub sp, 480
    ldr r3, =0x08051337
    bx r3
leave:
    add sp, 480
    pop {{r3-r5}}
    mov r8, r3
    mov r9, r4
    mov r10, r5
    pop {{r4-r7}}
    pop {{r0}}
returned:
    bx r0
    .align 4
    .pool
    .word leave, returned
.close
'''
    with tempfile.TemporaryDirectory(prefix='medal-asm-') as folder:
        path=Path(folder);(path/'medal.asm').write_text(source)
        subprocess.run([str(ROOT/'.tools/bin/armips'),'medal.asm'],cwd=folder,check=True)
        payload=(path/'medal.bin').read_bytes()
    return payload,source,struct.unpack('<II',payload[-8:])

def add_medals(build,bank_data=None,changed_by_bank=None):
    catalog=json.loads(CATALOG.read_text());require(catalog['base_rom_sha256']==digest(build.original),'Medal base differs')
    bank=banks()[6];data=bytearray(bank['data']) if bank_data is None else bank_data[bank['id']]
    sources={e['id']:e for e in table_entries(bank)}
    require({sources[r['id']]['index'] for r in catalog['entries']}==FORMATTED|{8,9},'Medal selection differs')
    rows,slots=[],[]
    for row in catalog['entries']:
        entry=sources[row['id']];raw=bank['data'][entry['start']:entry['end_exclusive']]
        require(entry['group']==14 and row['status']=='reviewed' and row['prose_review']
                and row['source_hex']==raw.hex() and digest(raw)==row['source_sha256'],'Medal source/review differs')
        payload,layout=compile_medal(row,entry['index']);offset=build.allocate(row['id'],payload,'medal-prototype')
        relative=(offset+0x08000000-(BANK_RAM+entry['strings_offset']+entry['group_offset']))&0xFFFFFFFF
        require(struct.unpack_from('<I',data,entry['slot'])[0]==entry['relative'],'Medal slot already owned')
        struct.pack_into('<I',data,entry['slot'],relative);slots.append(entry['slot'])
        rows.append(row|{'offset':offset,'encoded_hex':payload.hex(),'layout':layout,'index':entry['index']})
    bank_offset=None
    if bank_data is None:
        restored=bytearray(data)
        for slot in slots:restored[slot:slot+4]=bank['data'][slot:slot+4]
        require(restored==bank['data'],'Unowned medal bank modification')
        packed=pack_literals(data);require(decompress(packed)==(bytes(data),len(packed)),'Medal bank packing differs')
        bank_offset=build.allocate('medal-event-bank',packed,'medal-prototype')
        build.patch('medal-event-bank-pointer',bank['pointer_offset'],struct.pack('<I',bank['rom_offset']+0x08000000),
                    struct.pack('<I',bank_offset+0x08000000),'medal-prototype')
    else:
        require(changed_by_bank is not None,'Shared medal bank needs its slot ledger')
        changed_by_bank[bank['id']].extend(slots)
    offset=(len(build.data)+3)&~3;payload,source,points=assemble(offset+0x08000000)
    require(build.allocate('medal-frame-helper',payload,'medal-prototype')==offset,'Medal helper moved')
    for ident,site,before,target in [('entry',0x5132C,'f0b557464e464546',offset+0x08000000),
                                     ('leave',0x5157C,'38bc9846a146aa46',points[0])]:
        build.patch('medal-frame-'+ident,site,bytes.fromhex(before),bytes.fromhex('004b1847')+struct.pack('<I',target|1),'medal-prototype')
    for site,before,after in [(0x5133E,'0d4b','6b46'),(0x51444,'1b48','6846'),(0x5153E,'1549','6946')]:
        build.patch('medal-output-'+hex(site),site,bytes.fromhex(before),bytes.fromhex(after),'medal-prototype')
    return {'entries':rows,'bank_rom_offset':bank_offset,'changed_slots':slots,'capacity':CAPACITY,
            'helper_offset':offset,'returned':points[1],'helper_source':source,'review_sha256':digest(CATALOG.read_bytes())}
