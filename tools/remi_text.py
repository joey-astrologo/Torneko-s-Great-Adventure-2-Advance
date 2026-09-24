"""Own the Remi consumer's town text without changing shared readers."""
import json
import struct
import subprocess
import tempfile
from pathlib import Path
from tools.rom import ROOT, digest, require
from tools.town_text import entries, resource, RAM
from tools.compact_font import encode, measure
from tools.dialogue_layout import compile_dialogue
from tools.town_service_layout import compile_format

CATALOG = ROOT / 'translations/remi-review.json'
INDICES = ({58,200,208,213} | set(range(124,177)) | set(range(201,206))) - {133,141}


COST = (b'\x03\x05%d\x05', 70, 10)
NUMBER = (b'%d', 21, 3)
FORMATS = {
    126: {'{cost}': COST}, 128: {'{level}': NUMBER},
    131: {'{level}': NUMBER, '{cost}': COST}, 132: {'{cost}': COST},
    142: {'{item}': (b'%s', 162, 63), '{charges}': NUMBER, '{cost}': COST},
    146: {'{charges}': NUMBER}, 152: {'{cost}': COST},
    153: {'{vocation}': (b'%s', 45, 16)}, 169: {'{items}': NUMBER},
    171: {'{floor}': NUMBER}, 172: {'{dungeon}': (b'%s', 168, 56), '{floor}': NUMBER},
    173: {'{cost}': COST},
}


def compile_row(row, source):
    index, text, raw = row['index'], row['english'], bytes.fromhex(row['source_hex'])
    if 201 <= index <= 205 or index in (154,155,156):
        labels = text if isinstance(text, list) else [text]
        budget = 60 if isinstance(text, list) else 100
        require(max(map(measure, labels)) <= budget, 'Remi menu exceeds cursor-adjusted budget')
        payload = b'\r'.join(b'  ' + encode(label)[:-1] for label in labels) + b'\0'
        return payload, {'pages': [labels], 'line_widths': [[12 + measure(label) for label in labels]],
                         'native_width': budget + 12, 'native_rows': len(labels), 'cursor_reserve': 12,
                         'text_budget': budget, 'direct_rom_stream': True, 'kind': 'menu'}
    if index in (129,140,176):
        require(text.count('{number}') == 1 and raw.count(b'%s') == 1, 'Remi picker conversion differs')
        payload = encode(text.replace('{number}', ''))  # Metrics exclude the native two-cell number.
        width = measure(text.replace('{number}', '')) + 14
        require(width <= 88 and len(payload) + 4 <= 128, 'Remi picker exceeds native region')
        payload = b'%s'.join(encode(part)[:-1] for part in text.split('{number}')) + b'\0'
        return payload, {'pages': [[text]], 'line_widths': [[width]], 'native_width': 88,
                         'capacity': 128, 'maximum_formatted_bytes': len(payload) + 2,
                         'direct_rom_stream': False, 'kind': 'picker'}
    if index in FORMATS:
        payload, layout = compile_format(text, raw, FORMATS[index], 256)
        return payload, layout | {'kind': 'prose-format'}
    if index == 213:
        require(raw.count(b'\x1f') == 1 and raw.count(b'%d') == 1 and b'%s' not in raw,
                'Remi saved-village controls differ')
        # For layout only, model the native saved-name reader as a112px field.
        # It expands while rendering; the256-byte printf buffer stores just1F.
        payload, layout = compile_format(text, raw.replace(b'\x1f', b'%s'),
            {'{cost}': COST, '{village}': (b'%s', 112, 16)}, 271)
        payload = payload.replace(b'%s', b'\x1f')
        layout['maximum_formatted_bytes'] -= 15
        require(layout['maximum_formatted_bytes'] <= 256, 'Remi warning exceeds256-byte output')
        layout.update(capacity=256, kind='saved-village-format', saved_village_width=112,
                      saved_village_content_bytes=16)
        return payload, layout
    payload, layout = compile_dialogue(text, source['tokens'])
    if index == 208:
        require(len(payload) <= 256, 'Remi copied restriction exceeds256-byte output')
    return payload, layout | {'direct_rom_stream': True, 'kind': 'argument' if index in (164,165,166) else 'prose'}


def add_remi(build):
    catalog = json.loads(CATALOG.read_text())
    require(catalog['base_rom_sha256'] == digest(build.original), 'Remi base differs')
    require(len(catalog['entries']) == len(INDICES) and {r['index'] for r in catalog['entries']} == INDICES, 'Remi source selection differs')
    sources = entries(); pointers = [RAM + r['start'] for r in sources]; rows = []
    for row in catalog['entries']:
        source = sources[row['index']]
        raw = resource()['data'][source['start']:source['end_exclusive']]
        require(row['status'] == 'reviewed' and row['prose_review'] and row['source_id'] == source['id'], 'Remi review differs')
        require(raw.hex() == row['source_hex'] and digest(raw) == row['source_sha256'], 'Remi source differs')
        payload, layout = compile_row(row, source)
        offset = build.allocate(row['id'], payload, 'remi-text')
        pointers[row['index']] = offset + 0x08000000
        rows.append(row | {'offset': offset, 'encoded_hex': payload.hex(), 'layout': layout})
    table = build.allocate('remi-private-town-table', struct.pack('<300I', *pointers), 'remi-text')
    helper = (len(build.data) + 3) & ~3
    assembly = f'''.gba
.create "remi.bin", 0x{helper + 0x08000000:08x}
.thumb
    push {{r4,r5,r6,r7,lr}}
    mov r7,r10
    mov r6,r9
    mov r5,r8
    ldr r0,=0x{table + 0x08000000:08x}
    ldr r4,=0x0801e765
    bx r4
    .align 4
    .pool
.close
'''
    with tempfile.TemporaryDirectory(prefix='remi-asm-') as directory:
        folder = Path(directory); (folder / 'remi.asm').write_text(assembly)
        subprocess.run([str(ROOT / '.tools/bin/armips'), 'remi.asm'], cwd=folder, check=True)
        payload = (folder / 'remi.bin').read_bytes()
    require(build.allocate('remi-entry-helper', payload, 'remi-text') == helper, 'Remi helper alignment differs')
    build.patch('remi-entry', 0x1E75C, bytes.fromhex('f0b557464e464546'),
                bytes.fromhex('00480047') + struct.pack('<I', helper + 0x08000001), 'remi-text')
    picker = add_picker_width(build, rows)
    from tools.remi_warp_text import add_warp_names
    warp_names = add_warp_names(build)
    return {'entries': rows, 'table_offset': table, 'helper_offset': helper, 'assembly': assembly,
            'picker_width': picker, 'warp_names': warp_names, 'catalog_sha256': digest(CATALOG.read_bytes()), 'scope': catalog['scope']}


def add_picker_width(build, rows):
    """Use proportional advance only for the three owned Remi templates.

    The shared picker stores its format at SP+A4. Preserve the original12px
    behavior for every other caller, and reproduce the displaced literal load.
    """
    pointers = [r['offset'] + 0x08000000 for r in rows if r['index'] in (129,140,176)]
    require(len(pointers) == 3, 'Remi picker template set differs')
    helper = (len(build.data) + 3) & ~3
    source = f'''.gba
.create "picker.bin", 0x{helper + 0x08000000:08x}
.thumb
    push {{r0,r2,r3,r4,lr}}
    ldr r2,[sp,0xb8]
    mov r1,12
    ldr r3,=0x{pointers[0]:08x}
    cmp r2,r3
    beq proportional
    ldr r3,=0x{pointers[1]:08x}
    cmp r2,r3
    beq proportional
    ldr r3,=0x{pointers[2]:08x}
    cmp r2,r3
    bne apply_width
proportional:
    mov r1,0
apply_width:
    ldr r3,=0x080018c1
    bl call_r3
    pop {{r0,r2,r3,r4}}
    pop {{r1}}
    mov lr,r1
    ldr r1,=0x02002c10
    ldr r0,=0x0801645d
    bx r0
call_r3:
    bx r3
    .align 4
    .pool
.close
'''
    with tempfile.TemporaryDirectory(prefix='remi-picker-') as directory:
        folder = Path(directory); (folder / 'picker.asm').write_text(source)
        subprocess.run([str(ROOT / '.tools/bin/armips'), 'picker.asm'], cwd=folder, check=True)
        payload = (folder / 'picker.bin').read_bytes()
    require(build.allocate('remi-picker-width-helper', payload, 'remi-text') == helper,
            'Remi picker helper alignment differs')
    build.patch('remi-picker-width', 0x16454, bytes.fromhex('0c21ebf733fa1249'),
                bytes.fromhex('00490847') + struct.pack('<I', helper + 0x08000001), 'remi-text')
    return {'offset': helper, 'format_pointers': pointers, 'assembly': source,
            'scope': 'Three exact private formats use proportional advance; unknown formats retain12px.'}
