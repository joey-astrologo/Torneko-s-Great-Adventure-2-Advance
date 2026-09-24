"""Checked English name-editor resources, preserving the original indexed names."""

from pathlib import Path
import string
import struct
import subprocess
import tempfile

from tools.compact_font import encode, measure
from tools.rom import ROOT, require

OWNER = 'english-name-entry'
MAX_NAME = 7
STORED = 0x02003B46
HERO = 0x02003B58
EDIT = 0x0200CCF4
TABLE = 0x141A28
ID_FIRST = 0xB9
CHARACTERS = string.ascii_uppercase + string.ascii_lowercase + string.digits + " '-.,!?"
IDS = {char: ID_FIRST + i for i, char in enumerate(CHARACTERS)}
TABLE_REFERENCES = (0xF584, 0x14970, 0x14C64, 0x15634, 0x18474,
                    0x1FB08, 0x205E0, 0x354BC, 0x3EFAC, 0x4202C)


def indexed(text, maximum=MAX_NAME):
    require(0 < len(text) <= maximum <= 8, 'Name length outside supported range')
    require(all(char in IDS for char in text), 'Unsupported name character')
    return bytes(IDS[char] for char in text) + b'\x01' * (8 - len(text)) + b'\0' * 8


def keyboard_pages(original):
    # Keep original symbol/kana selections, including the voiced/small-kana keys.
    old = [original[0x147F00 + i * 64:0x147F40 + i * 64] for i in range(3)]
    english = []
    for alphabet in (string.ascii_uppercase, string.ascii_lowercase):
        chars = alphabet + string.digits + " '-.,!?"
        english.append(b'\x01' * 4 + bytes(IDS[c] for c in chars) + b'\x01' * (60 - len(chars)))
    return english + [old[2], old[0], old[1]]


def grid_text(page, glyphs):
    text = bytearray()
    for row in range(6):
        for col in range(10):
            ident = page[4 + row * 10 + col]
            if ident == 1:
                continue
            # Match the native keyboard cursor coordinates and original gap.
            x = 0x0E + col * 0x14 + (0x12 if col >= 5 else 0)
            text.extend((4, x))
            text.extend(encode('Sp')[:-1] if ident == IDS[' '] else
                        glyphs[ident * 2:ident * 2 + 2])
        if row != 5:
            text.append(13)
    text.append(0)
    return bytes(text)


def assemble_helpers(address, glyph_table, default_ids, default_glyphs, player_format):
    source = f'''.gba
.create "helpers.bin", 0x{address:08X}
.thumb
.area 128, 0xFF
; r1: current name position; r2: name window. Return cursor x in r0.
; Preserve r2 and r4-r7, including across the native glyph-width call.
    push {{r2,r4-r7,lr}}
    mov r4, r1
    mov r5, r2
    ldrb r6, [r5,0]
; Only the shared editor has its format pointer at caller SP+0x54. Its
; 28-byte input frame plus our 24-byte frame put that word at SP+0x88.
; The item editor has a different frame and never enters this branch.
    mov r0, lr
    ldr r1, =0x080155FD
    cmp r0, r1
    bne prefix_done
    ldr r0, [sp,0x88]
    ldr r1, =0x{player_format:08X}
    cmp r0, r1
    bne prefix_done
    add r6, {measure('Name: ')}
prefix_done:
    ldr r7, =0x{EDIT:08X}
loop:
    cmp r4, 0
    beq done
    ldrb r0, [r7,0]
    lsl r0, r0, 1
    ldr r1, =0x{glyph_table:08X}
    add r1, r1, r0
    ldrb r0, [r1,0]
    lsl r0, r0, 8
    ldrb r1, [r1,1]
    orr r0, r1
    ldr r3, =0x08001C71
    bl cursor_call_r3
    ldrb r1, [r5,6]
    cmp r1, 0
    beq measured
    mov r0, r1
measured:
    ldrb r1, [r5,8]
    add r0, r0, r1
    add r6, r6, r0
    add r7, 1
    sub r4, 1
    b loop
done:
    mov r0, r6
    pop {{r2,r4-r7}}
    pop {{r1}}
    mov lr, r1
    ldr r1, =0x08019F73
    bx r1
cursor_call_r3:
    bx r3
    .align 4
    .pool
.endarea
.area 128, 0xFF
; Same destination fields and calling convention as the original initializer.
    push {{lr}}
    ldr r0, =0x{STORED:08X}
    ldr r1, =0x{default_ids:08X}
    mov r2, 16
    ldr r3, =0x0805D0D5
    bl init_call_r3
    ldr r0, =0x{HERO:08X}
    ldr r1, =0x{default_glyphs:08X}
    mov r2, 15
    ldr r3, =0x0805CD71
    bl init_call_r3
    pop {{r0}}
    bx r0
init_call_r3:
    bx r3
    .align 4
    .pool
.endarea
.close
'''
    with tempfile.TemporaryDirectory(prefix='name-entry-asm-') as directory:
        folder = Path(directory)
        (folder / 'helpers.asm').write_text(source)
        subprocess.run([str(ROOT / '.tools/bin/armips'), 'helpers.asm'], cwd=folder, check=True)
        payload = (folder / 'helpers.bin').read_bytes()
    require(len(payload) == 256, 'Name helpers exceeded allocation')
    return payload, source


def add_name_entry(build):
    original = build.original
    require(len(CHARACTERS) == 69 and max(IDS.values()) == 0xFD, 'Name IDs collide with special keys')
    require(original[0x15466:0x15468] == bytes.fromhex('99b0') and
            original[0x19F3C:0x19F44] == bytes.fromhex('f0b54f464646c0b4'),
            'Editor frame layout used by cursor prefix differs')
    def allocate(ident, payload):
        return 0x08000000 + build.allocate('name-' + ident, payload, OWNER)
    def patch(ident, offset, expected, replacement):
        build.patch('name-' + ident, offset, bytes.fromhex(expected), replacement, OWNER)
    def pointer(ident, offset, expected, target):
        build.patch('name-' + ident, offset, struct.pack('<I', expected), struct.pack('<I', target), OWNER)

    # Preserve original glyph identities. Vacant slots get a narrow underscore.
    glyphs = bytearray(original[TABLE:TABLE + ID_FIRST * 2] + b'\x81\x94' * (256 - ID_FIRST))
    glyphs[2:4] = encode('_')[:2]
    for char, ident in IDS.items():
        glyphs[ident * 2:ident * 2 + 2] = encode(char)[:2]
    table = allocate('glyph-table', bytes(glyphs))
    for offset in TABLE_REFERENCES:
        pointer(f'glyph-reference-{offset:06x}', offset, 0x08000000 + TABLE, table)

    pages = keyboard_pages(original)
    keys = allocate('keyboard-ids', b''.join(pages))
    labels = []
    for next_page in ('abc', 'Symbols', 'Hiragana', 'Katakana', 'ABC'):
        label = encode(next_page)[:-1]
        for x, text in ((0x40, 'Next'), (0x80, 'Back'), (0xC0, 'Done')):
            label += bytes((4, x)) + encode(text)[:-1]
        labels.append(allocate('actions-' + str(len(labels)), label + b'\0'))
    # Keep native symbol/kana display strings, paired with their original IDs.
    bodies = [allocate('grid-' + str(i), grid_text(pages[i], glyphs)) for i in range(2)]
    bodies += [0x080600F8, 0x080646BC, 0x080645C4]
    texts = allocate('page-text-pointers', struct.pack('<10I', *(labels + bodies)))
    actions = allocate('action-indices', struct.pack('<5I', *range(5)))
    grids = allocate('grid-indices', struct.pack('<5I', *range(5, 10)))
    for offset in (0x15630, 0x18470):
        pointer(f'page-table-{offset:06x}', offset, 0x08140D68, texts)
    for offset in (0x15638, 0x18478):
        pointer(f'action-indices-{offset:06x}', offset, 0x08147EE8, actions)
    for offset in (0x1563C, 0x1847C):
        pointer(f'grid-indices-{offset:06x}', offset, 0x08147EF4, grids)
    pointer('keyboard-map', 0x1A238, 0x08147F00, keys)
    patch('five-pages', 0x1A1CE, '0228', bytes.fromhex('0428'))
    for offset, expected in ((0x14BE6, '0622'), (0x14C2C, '0422'), (0x205C4, '0622')):
        patch(f'limit-{offset:06x}', offset, expected, bytes((MAX_NAME, 0x22)))
    secret = allocate('original-secret', original[0x147DE4:0x147DEA] + b'\x01\0')
    pointer('secret-reference', 0x14C58, 0x08147DE4, secret)
    patch('secret-exact-length', 0x14C10, '0622', bytes.fromhex('0722'))
    patch('secret-clear-eight-slots', 0x14C1E, '0622', bytes.fromhex('0822'))
    patch('window-origin', 0x154E0, '0820', bytes.fromhex('0420'))
    patch('window-width', 0x154E4, '0d22', bytes.fromhex('1622'))
    for offset in (0x15572, 0x183BA):
        patch(f'vwf-{offset:06x}', offset, '0e21', bytes.fromhex('0021'))
    village = allocate('village-format', b'%s' + encode(' Village'))
    pointer('village-format-reference', 0x140EF4, 0x08063D60, village)
    player = allocate('player-format', encode('Name: ')[:-1] + b'%s\0')
    pointer('player-format-reference', 0x1416CC, 0x080603AC, player)
    default_ids = allocate('default-ids', indexed('Torneko'))
    default_glyphs = allocate('default-glyphs', encode('Torneko'))
    helper_at = 0x08000000 + ((len(build.data) + 3) & ~3)
    helpers, source = assemble_helpers(helper_at, table, default_ids, default_glyphs, player)
    require(allocate('helpers', helpers) == helper_at, 'Name helper allocation moved')
    # Far jumps reach the appended ROM; the cursor helper preserves LR and
    # resumes explicitly at the first instruction after the replaced sequence.
    cursor_site = 0x08019F68
    jump = bytes.fromhex('00480047') + struct.pack('<I', helper_at | 1) + bytes.fromhex('c046')
    patch('cursor-entry', cursor_site - 0x08000000, 'c800401a400011784018', jump)
    init_jump = bytes.fromhex('004b1847') + struct.pack('<I', (helper_at + 128) | 1)
    patch('default-initializer', 0x590D0, '00b50f4800227521', init_jump)
    return {'maximum_characters': MAX_NAME, 'item_maximum_characters': 8,
            'characters': CHARACTERS, 'ids': IDS, 'glyph_table': table,
            'keyboard_pages': [p.hex() for p in pages], 'keyboard_map': keys,
            'default': 'Torneko', 'default_advance_pixels': measure('Torneko'),
            'helpers_source': source, 'helper_address': helper_at,
            'save_layout_changed': False}
