"""Private labels and three closed-set town inventory messages."""
import json,struct,subprocess,tempfile
from pathlib import Path
from tools.rom import ROOT,digest,require
from tools.town_text import entries
from tools.text_codec import source_bytes,readable
from tools.compact_font import encode,measure
from tools.extract_action_labels import extract,START,END

CATALOG=ROOT/'translations/town-actions-review.json'

def add_town_actions(build):
    catalog=json.loads(CATALOG.read_text());sources={r['index']:r for r in entries()}
    require(catalog['base_rom_sha256']==digest(build.original),'Town action base differs')
    require(len(catalog['entries'])==3 and {r['index'] for r in catalog['entries']}=={59,108,109},'Town message ownership differs')
    require(len(catalog['labels'])==3 and {r['index'] for r in catalog['labels']}=={40,42,44},'Town label ownership differs')
    approved={r['id']:r['english'] for r in json.loads((ROOT/'translations/master.json').read_text())['entries']}
    table=bytearray(110*4);messages=[]
    for row in catalog['entries']:
        raw=source_bytes(sources[row['index']]['tokens'])
        require(row['id'] not in approved or row['english']==approved[row['id']],'Town wording differs from approved native source')
        require(row['status']=='reviewed' and row['id']==sources[row['index']]['id'] and
                row['source_hex']==raw.hex() and row['source_sha256']==digest(raw) and
                row['japanese']==readable(sources[row['index']]['tokens']),'Town source review differs')
        require(not any(c in row['english'] for c in '%{}\n\r') and measure(row['english'])<=216,'Town message width/control differs')
        payload=encode(row['english']);offset=build.allocate('town-items-'+str(row['index']),payload,'town-item-text')
        struct.pack_into('<I',table,row['index']*4,offset+0x08000000)
        messages.append(row|{'offset':offset,'encoded_hex':payload.hex(),'advance':measure(row['english'])})
    private=build.allocate('town-items-private-messages',bytes(table),'town-item-text')
    # The complete function reads r9 only at index59 or108/109. Its sparse private
    # table is never passed to another consumer. No original town/RAM table changes.
    action_table=bytearray(build.original[START:END]);action_sources=extract()['entries'];labels=[]
    for row in catalog['labels']:
        require(row['status']=='reviewed' and row['source']==action_sources[row['index']]['source'] and
                measure(row['english'])<=34,'Town action label source/budget differs')
        payload=encode(row['english']);offset=build.allocate(row['id'],payload,'town-item-text')
        struct.pack_into('<I',action_table,row['index']*4,offset+0x08000000)
        labels.append(row|{'offset':offset,'encoded_hex':payload.hex(),'advance':measure(row['english']),'budget':34})
    actions=build.allocate('town-items-private-actions',bytes(action_table),'town-item-text')
    for site in (0x1E560,0x1E62C):
        build.patch(f'town-items-action-consumer-{site:x}',site,struct.pack('<I',START+0x08000000),
                    struct.pack('<I',actions+0x08000000),'town-item-text')
    helper=(len(build.data)+3)&~3
    assembly=f'''.gba
.create "town-items.bin", 0x{helper+0x08000000:08x}
.thumb
    push {{r4-r7,lr}}
    mov r7, r9
    mov r6, r8
    push {{r6,r7}}
    ldr r0, =0x{private+0x08000000:08x}
    ldr r3, =0x0801E499
    bx r3
    .align 4
    .pool
.close
'''
    with tempfile.TemporaryDirectory(prefix='town-item-asm-') as directory:
        folder=Path(directory);(folder/'town-items.asm').write_text(assembly)
        subprocess.run([str(ROOT/'.tools/bin/armips'),'town-items.asm'],cwd=folder,check=True)
        payload=(folder/'town-items.bin').read_bytes()
    require(build.allocate('town-items-entry-helper',payload,'town-item-text')==helper,'Town helper alignment differs')
    build.patch('town-items-entry',0x1E490,bytes.fromhex('f0b54f464646c0b4'),
                bytes.fromhex('004b1847')+struct.pack('<I',helper+0x08000001),'town-item-text')
    return {'entries':messages,'labels':labels,'message_table_offset':private,'action_table_offset':actions,
            'helper_offset':helper,'assembly':assembly,'catalog_sha256':digest(CATALOG.read_bytes()),
            'scope':catalog['scope'],'output_capacity':256,'frame_bytes':268}
