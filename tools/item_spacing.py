"""Bypass the Japanese byte-count compression for explicitly English item rows."""
from pathlib import Path
import struct, subprocess, tempfile
from tools.rom import ROOT, require


def add_spacing(build):
    offset=(len(build.data)+3)&~3
    source=f'''.gba
.create "helper.bin", 0x{offset+0x08000000:08x}
.thumb
    mov r0, r8
    mov r1, 0
    mov r2, 0
scan:
    ldrb r3, [r0]
    cmp r3, 0
    beq decide
    cmp r3, 0xF0
    bne next
    ldrb r3, [r0, 1]
    cmp r3, 0x20
    blo next
    cmp r3, 0x7E
    bhi next
    mov r2, 1
next:
    add r0, 1
    add r1, 1
    b scan
decide:
    cmp r2, 0
    bne uncompressed
    cmp r1, 20
    bls uncompressed
    ldr r0, =0x0800F01D
    bx r0
uncompressed:
    ldr r0, =0x0800F031
    bx r0
    .align 4
    .pool
.close
'''
    with tempfile.TemporaryDirectory(prefix='item-spacing-') as directory:
        p=Path(directory);(p/'helper.asm').write_text(source)
        subprocess.run([str(ROOT/'.tools/bin/armips'),'helper.asm'],cwd=p,check=True)
        data=(p/'helper.bin').read_bytes()
    require(build.allocate('english-item-spacing',data,'item-text')==offset,'Item helper moved')
    # Halfword-aligned 10-byte trampoline replaces mov/strlen/cmp/bls only.
    jump=bytes.fromhex('014800470046')+struct.pack('<I',0x08000000+offset+1)
    build.patch('english-item-spacing-entry',0xf012,bytes.fromhex('40464df0c4ff142809d9'),jump,'item-text')
    return {'offset':offset,'source':source,'english_spacing':0,'japanese_byte_threshold':20}
