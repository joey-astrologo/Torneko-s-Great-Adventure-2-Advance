"""Full English inscription input with original target/history eligibility."""
import json,struct,subprocess,tempfile
from pathlib import Path
from tools.rom import ROOT,digest,require
from tools.compact_font import encode
from tools.extract_items import source

def far(site,address,reg=3):
    padding=b'\xc0\x46' if site&2 else b''
    return struct.pack('<HH',0x4800|(reg<<8)|(1 if site&2 else 0),0x4700|(reg<<3))+padding+struct.pack('<I',address|1)

def helper_source(address):
    return f'''.gba
.create "input.bin", 0x{address:08X}
.thumb
.area 128, 0xFF
; Original owner SP has36 bytes: glyphs[31], spare byte, limit[4].
    push {{r3,lr}}
    mov r0, r7
    ldr r3, =0x08004AF9
    bl init_call
    lsl r0, r0, 24
    lsr r0, r0, 24
    mov r1, 15
    cmp r0, 124
    beq init_limit
    cmp r0, 151
    beq init_limit
    mov r1, 8
init_limit:
    str r1, [sp,40]
    pop {{r3}}
    pop {{r0}}
    mov lr, r0
; Reproduce the four displaced instructions at182E8.
    ldr r2, =0x0200CD08
    mov r0, 255
    strb r0, [r2,0]
    mov r1, 0
    ldr r3, =0x080182F1
    bx r3
init_call:
    bx r3
    .align 4
    .pool
.endarea
.area 128, 0xFF
; Widen only the two inscription inputs; ordinary custom names keep geometry.
    push {{r4}}
    ldr r0, [sp,36]
    cmp r0, 15
    beq wide
    mov r0, 7
    mov r2, 15
    b geometry_done
wide:
    mov r0, 1
    mov r2, 28
geometry_done:
    mov r1, 1
    mov r3, 1
    ldr r4, =0x0801834D
    mov lr, r4
    pop {{r4}}
    bx lr
    .align 4
    .pool
.endarea
.area 128, 0xFF
; Finish the native indexed-glyph conversion at8 or15 slots, then NUL.
    add r3, 1
    ldr r0, [sp,32]
    cmp r3, r0
    bge display_done
    ldr r0, =0x0801838B
    bx r0
display_done:
    lsl r0, r0, 1
    mov r1, sp
    add r1, r1, r0
    mov r0, 0
    strb r0, [r1,0]
    mov r1, sp
    ldr r0, =0x080183B1
    bx r0
    .align 4
    .pool
.endarea
.area 128, 0xFF
; Shared B-delete keeps original8-slot behavior except limit15 inscriptions.
; EDIT[0..16) is already the shared editor's owned16-byte working record.
    mov r2, r3
    mov r0, r8
    cmp r0, 15
    beq delete_start
    mov r0, 8
delete_start:
    mov r4, r2
    mov r3, 1
delete_loop:
    cmp r1, r0
    bge delete_end
    strb r3, [r2,r1]
    add r1, 1
    b delete_loop
delete_end:
    mov r3, 0
    add r0, r0, r2
    strb r3, [r0,0]
    mov r1, r8
    cmp r1, 15
    beq delete_return
    strb r3, [r0,1]
delete_return:
    ldr r0, =0x0801A345
    bx r0
    .align 4
    .pool
.endarea
.area 128, 0xFF
; The original candidate iterator and result IDs remain unchanged.
    ldr r0, [r4,0]
    mov r1, sp
    bl compare
    ldr r3, =0x080354AD
    bx r3
    .align 4
    .pool
.endarea
.area 128, 0xFF
    ldr r0, [r4,0]
    mov r1, sp
    bl compare
    ldr r3, =0x0803EF9D
    bx r3
    .align 4
    .pool
.endarea
.area 128, 0xFF
; Exact Japanese comparison; fold case only inside an F0 English glyph.
compare:
    push {{r4,r5,lr}}
compare_loop:
    ldrb r2, [r0,0]
    ldrb r3, [r1,0]
    cmp r2, r3
    bne unequal
    cmp r2, 0
    beq equal
    ldrb r4, [r0,1]
    ldrb r5, [r1,1]
    cmp r2, 240
    bne compare_second
    cmp r4, 65
    blo fold_second
    cmp r4, 90
    bhi fold_second
    add r4, 32
fold_second:
    cmp r5, 65
    blo compare_second
    cmp r5, 90
    bhi compare_second
    add r5, 32
compare_second:
    cmp r4, r5
    bne unequal
    add r0, 2
    add r1, 2
    b compare_loop
equal:
    mov r0, 0
    b compare_return
unequal:
    mov r0, 1
compare_return:
    pop {{r4,r5}}
    pop {{r1}}
    bx r1
    .align 4
    .pool
.endarea
.close
'''

CATALOG=ROOT/'translations/writing-input-review.json'

def add_input(build):
    original=build.original;owner='writing-input';entries=[];tables=[]
    catalog=json.loads(CATALOG.read_text())
    require(catalog['base_rom_sha256']==digest(original),'Writing input review base differs')
    items=json.loads((ROOT/'translations/items-review.json').read_text())['entries']
    items={r['id']:r for r in items}
    effects={r['item_id']:r['english'] for r in json.loads((ROOT/'translations/scroll-item-review.json').read_text())['effects']}
    spells={r['id']:r['name'] for r in json.loads((ROOT/'translations/spells-review.json').read_text())['entries']}
    for family,literal in [('scroll',0x354B8),('spell',0x3EFA8)]:
        base=struct.unpack_from('<I',original,literal)[0]-0x08000000;old=[];i=0
        while True:
            raw=original[base+8*i:base+8*i+8];ptr,num=struct.unpack_from('<Ih',raw)
            if num==0:break
            old.append({'source':source(original,ptr),'target':num,'record_hex':raw.hex()});i+=1
        require(len(old)==(54 if family=='scroll' else 100),'Original inscription lookup size differs')
        reviewed_table=next(t for t in catalog['tables'] if t['family']==family)
        end=base+8*(len(old)+1)
        require(reviewed_table['source_offset']==base and reviewed_table['end_exclusive']==end and reviewed_table['source_sha256']==digest(original[base:end]),'Writing input table ownership differs')
        require([{k:r[k] for k in ('source','target','record_hex')} for r in reviewed_table['original_entries']]==old and all(r['status']=='reviewed' for r in reviewed_table['original_entries']),'Writing input original rows differ')
        table=bytearray(original[base:base+8*len(old)]);seen={}
        for row in old:
            ident=row['target']
            if family=='scroll':
                full=items[ident].get('canonical_name',items[ident]['name'])
                require(full.endswith(' scroll'),'Scroll effect naming source differs')
                labels={full.removesuffix(' scroll'),effects[ident],items[ident]['name']}
            else:labels={spells[ident]}
            for text in sorted(labels):
                key=text.casefold()
                if key in seen:require(seen[key]==ident,'Ambiguous inscription name');continue
                seen[key]=ident;require(1<=len(text)<=15,'English inscription exceeds15 slots')
                at=build.allocate('writing-input.'+family+'.'+str(ident)+'.'+str(len(entries)),encode(text),owner)
                table.extend(struct.pack('<IhH',at+0x08000000,ident,0));entries.append({'id':'writing-input.'+family+'.'+str(ident)+'.'+str(len(entries)),'family':family,'target':ident,'english':text,'offset':at,'encoded_hex':encode(text).hex()})
        table.extend(original[base+8*len(old):base+8*(len(old)+1)])
        at=build.allocate('writing-'+family+'-lookup',bytes(table),owner)
        build.patch('writing-'+family+'-lookup-reader',literal,struct.pack('<I',base+0x08000000),struct.pack('<I',at+0x08000000),owner)
        tables.append({'family':family,'source_offset':base,'end_exclusive':base+8*(len(old)+1),'source_sha256':digest(original[base:base+8*(len(old)+1)]),'original_entries':old,'offset':at,'english_names':seen})
    require([{k:r[k] for k in ('id','family','target','english')} for r in catalog['entries']]==[{k:r[k] for k in ('id','family','target','english')} for r in entries] and all(r['status']=='reviewed' for r in catalog['entries']),'Writing input English review differs')
    for table in catalog['tables']:
        for row in table['original_entries']:
            require(row['english_aliases']==[r['english'] for r in entries if r['family']==table['family'] and r['target']==row['target']],'Writing input source/English aliases differ')
    blank=build.allocate('writing-empty-fifteen',b'\1'*15+b'\0',owner)
    init_table=build.allocate('writing-initial-name-pointer',struct.pack('<II',struct.unpack_from('<I',original,0x140D68)[0],blank+0x08000000),owner)
    build.patch('writing-special-initial-pointer',0x182D8,struct.pack('<I',0x08140D68),struct.pack('<I',init_table+0x08000000),owner)
    helper_at=(len(build.data)+3)&~3;asm=helper_source(helper_at+0x08000000)
    with tempfile.TemporaryDirectory(prefix='t2-writing-input-') as directory:
        folder=Path(directory);(folder/'input.asm').write_text(asm)
        subprocess.run([str(ROOT/'.tools/bin/armips'),'input.asm'],cwd=folder,check=True)
        helpers=(folder/'input.bin').read_bytes()
    require(len(helpers)==896 and build.allocate('writing-input-helpers',helpers,owner)==helper_at,'Writing helpers allocation differs')
    specs=[(0x182E8,'584aff2010700021',0,3),(0x18344,'072001210f220123',128,3),
           (0x183A4,'0133072befdd694600200874',256,0),(0x1A2BA,'1a1c072906dc141c0123',384,0),
           (0x354A4,'2068694627f026fd',512,3),(0x3EF94,'206869461df0aeff',640,3)]
    for site,expected,inner,reg in specs:
        replacement=far(site,helper_at+0x08000000+inner,reg);old=bytes.fromhex(expected)
        replacement+=b'\xc0\x46'*((len(old)-len(replacement))//2)
        require(len(old)==len(replacement),'Writing trampoline size differs')
        build.patch('writing-input-code-'+hex(site),site,old,replacement,owner)
    for site,old,new in [(0x1828E,'85b0','89b0'),(0x1850C,'05b0','09b0'),(0x182C8,'0a22','1022'),(0x18432,'0820','0898'),
                         (0x3545A,'85b0','89b0'),(0x354CC,'05b0','09b0'),(0x35486,'072b','0e2b'),
                         (0x3EF4A,'85b0','89b0'),(0x3EFBC,'05b0','09b0'),(0x3EF76,'072b','0e2b')]:
        build.patch('writing-input-bound-'+hex(site),site,bytes.fromhex(old),bytes.fromhex(new),owner)
    return {'entries':entries,'tables':tables,'helper_offset':helper_at,'helper_source':asm,'catalog_sha256':digest(CATALOG.read_bytes()),'scope':catalog['scope']}
