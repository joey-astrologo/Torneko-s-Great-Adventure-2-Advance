"""Core combat formats and a bounded, conditional one-line queue adapter."""
import json,re,struct,subprocess,tempfile
from pathlib import Path
from tools.rom import ROOT,digest,require
from tools.compact_font import encode,measure
CATALOG=ROOT/'translations/combat-review.json'

def compile_format(text):
 require(not any(c in text.replace('{actor}','').replace('{value}','') for c in '{}'),'Unknown combat format field')
 return b''.join({'{actor}':b'%s','{value}':b'%d'}[p] if p in ('{actor}','{value}') else encode(p)[:-1].replace(b'%',b'%%') for p in re.split(r'(\{actor\}|\{value\})',text))+b'\0'

def assemble(address,damage_format,notices,match_copied_strings=True):
 copied = '''    mov r4, r0
notice_compare:
    ldrb r5, [r1]
    ldrb r6, [r4]
    cmp r5, r6
    bne notice_next
    cmp r5, 0
    beq notice_found
    add r1, 1
    add r4, 1
    b notice_compare
notice_next:
''' if match_copied_strings else ''
 source=f'''.gba
.create "combat.bin", 0x{address:08x}
.thumb
; Save the caller ABI before identifying the three owned combat queue sites.
    push {{r0-r7,lr}}
; Map only reviewed original static-message pointers at this dialogue reader.
; No shared table or caller-owned text buffer is changed. Saved r0 carries the
; replacement to the native queue; all other saved arguments remain intact.
    ldr r2, =0x{notices['mapping_offset']+0x08000000:08x}
    mov r3, {len(notices['entries'])}
notice_scan:
    ldr r1, [r2]
    cmp r0, r1
    beq notice_found
{copied}    add r2, 8
    sub r3, 1
    bne notice_scan
    b notice_done
notice_found:
    ldr r0, [r2,4]
    str r0, [sp]
notice_done:
    mov r4, r0
    mov r5, lr
    ldr r0, =0x0800C9F7
    cmp r5, r0
    beq skip_fragment
    ldr r0, =0x0800C9CF
    cmp r5, r0
    beq incoming
    ldr r0, =0x0800CEFB
    cmp r5, r0
    beq measure_message
    ldr r0, =0x0800D487
    cmp r5, r0
    beq measure_message
    ldr r0, =0x0800D4D1
    cmp r5, r0
    beq measure_message
    b native_queue
incoming:
; The prefix and final damage belong to the same native 256-byte stack buffer.
; Append before its first queue call. Original damage animation still executes.
    mov r0, r4
find_end:
    ldrb r1, [r0]
    cmp r1, 0
    beq append_damage
    add r0, 1
    b find_end
append_damage:
    ldr r1, =0x{damage_format:08x}
    ldr r2, [sp,0x290]
    ldr r3, =0x08000FB9
    bl call_r3
measure_message:
    mov r6, r4
    mov r7, 0
scan:
    ldrb r0, [r6]
    add r6, 1
    cmp r0, 0
    beq measured
    cmp r0, 13
    beq scan
    cmp r0, 0x80
    bls ascii
    cmp r0, 0xA0
    blo pair
    cmp r0, 0xDF
    bls native_queue ; Unsupported halfwidth source: preserve authored breaks.
pair:
    lsl r0, r0, 8
    ldrb r1, [r6]
    add r6, 1
    orr r0, r1
    b glyph
ascii:
    cmp r0, 0x30
    blo native_queue
    cmp r0, 0x39
    bhi native_queue
    ldr r1, =0x821F
    add r0, r0, r1
glyph:
    ldr r3, =0x08001C71
    bl call_r3
    add r7, r7, r0
    cmp r7, 216
    bhi native_queue
    b scan
measured:
; Every removable break follows an encoded English space, so joining cannot
; fuse words. All source templates are separately bounded for two/three lines.
    mov r5, r4
    mov r6, r4
copy:
    ldrb r0, [r5]
    add r5, 1
    cmp r0, 13
    beq copy
    strb r0, [r6]
    add r6, 1
    cmp r0, 0
    bne copy
native_queue:
    pop {{r0-r7}}
    pop {{r3}}
    mov lr, r3
; Reproduce the original eight-byte entry, including its conditional branch.
    push {{r4-r6,lr}}
    mov r6, r0
    cmp r1, 0
    beq queue_zero
    ldr r3, =0x08015895
    bx r3
queue_zero:
    ldr r3, =0x080158CF
    bx r3
skip_fragment:
; Its already-displayed damage is still formatted/animated by original code.
    pop {{r0-r7}}
    pop {{r3}}
    bx r3
call_r3:
    bx r3
    .align 4
    .pool
.close
'''
 with tempfile.TemporaryDirectory(prefix='combat-asm-') as directory:
  folder=Path(directory);(folder/'combat.asm').write_text(source)
  subprocess.run([str(ROOT/'.tools/bin/armips'),'combat.asm'],cwd=folder,check=True)
  payload=(folder/'combat.bin').read_bytes()
 return payload,source

def add_combat(build):
 from tools.queue_notice_text import add_queue_notices
 notices=add_queue_notices(build)
 review=json.loads(CATALOG.read_text());require(review['source_rom_sha256']==digest(build.original),'Combat base changed');rows=[]
 for row in review['entries']:
  src=row['source'];raw=bytes.fromhex(src['raw_hex']);require(build.original[src['offset']:src['end_exclusive']]==raw and row['status']=='reviewed','Combat source/review changed')
  require(all(line.endswith(' ') for line in row['english'].split('\n')[:-1]),'Combat soft break needs an existing space')
  payload=compile_format(row['english']);require(re.findall(b'%[sd]',payload)==re.findall(b'%[sd]',raw),'Combat substitutions changed')
  # Max level is positive signed16. Native int formatting is tested separately.
  max_actor=114+measure(' Lv')+5*6;max_number=11*6
  widths=[measure(line.replace('{actor}','').replace('{value}',''))+line.count('{actor}')*max_actor+line.count('{value}')*max_number for line in row['english'].split('\n')]
  require(max(widths)<=216,'Combat fallback line exceeds widest substitution')
  max_bytes=len(payload)+row['english'].count('{actor}')*61+row['english'].count('{value}')*9
  require(max_bytes<=200,'Combat message leaves insufficient append reserve')
  offset=build.allocate(row['id'],payload,'combat-text');site=0x140d68+row['table_offset']
  build.patch(row['id']+'-pointer',site,struct.pack('<I',src['offset']+0x8000000),struct.pack('<I',offset+0x8000000),'combat-text')
  rows.append(row|{'offset':offset,'encoded_hex':payload.hex(),'maximum_fallback_widths':widths,'maximum_formatted_bytes':max_bytes})
 damage_row=next(r for r in rows if r['id']=='combat.1c4')
 for prefix in (r for r in rows if r['id'] in ('combat.1b4','combat.1b8')):
  require(prefix['maximum_formatted_bytes']+damage_row['maximum_formatted_bytes']-1<=256,'Combined incoming damage exceeds buffer')
  require(prefix['maximum_fallback_widths'][-1]+damage_row['maximum_fallback_widths'][0]<=216,'Combined incoming damage exceeds fallback width')
 damage=damage_row['offset']+0x8000000
 offset=(len(build.data)+3)&~3;payload,source=assemble(offset+0x8000000,damage,notices)
 require(build.allocate('combat-queue-helper',payload,'combat-text')==offset,'Combat helper moved')
 build.patch('combat-queue-entry',0x1588c,bytes.fromhex('70b5061c00291cd0'),bytes.fromhex('004b1847')+struct.pack('<I',offset+0x8000001),'combat-text')
 return {'entries':rows,'queue_notices':notices,'helper_offset':offset,'helper_source':source,'review_sha256':digest(CATALOG.read_bytes()),'line_budget':216,'message_buffer_bytes':256,'extra_stack_bytes':36,'scope':'Core combat format insertion. Owned queue calls merge incoming fragments and remove authored soft breaks only when measured contents fit one line. Closed static-notice pointers are mapped only at this queue. Native validation required.'}
