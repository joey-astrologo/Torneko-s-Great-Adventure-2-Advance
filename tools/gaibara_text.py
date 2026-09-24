"""Own the synthesis consumer's town text without changing shared readers."""
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

CATALOG = ROOT / 'translations/gaibara-review.json'
INDICES = {30,31,32,33,34,36,198,199} | set(range(39,55)) | set(range(110,120))


def compile_row(row, source):
    index, text = row['index'], row['english']
    if index == 112:
        require(text == ['Synthesise', 'Explain', 'Leave'], 'Synthesis menu choices differ')
        require(max(map(measure, text)) <= 60, 'Synthesis menu exceeds60px after cursor reserve')
        # Original structural ASCII padding is two six-pixel cells, not word spaces.
        payload = b'\r'.join(b'  ' + encode(label)[:-1] for label in text) + b'\0'
        return payload, {'pages': [text], 'line_widths': [[12 + measure(label) for label in text]],
                         'native_width': 72, 'native_rows': 3, 'cursor_reserve': 12, 'text_budget': 60,
                         'direct_rom_stream': True}
    if index in (52,113,114):
        fields = {'{cost}': (b'\x03\x05%d\x05', 70, 10)} if index == 52 else {'{item}': (b'%s', 162, 63)}
        return compile_format(text, bytes.fromhex(row['source_hex']), fields, 256)
    payload, layout = compile_dialogue(text, source['tokens'])
    return payload, layout | {'direct_rom_stream': True}


def add_gaibara(build):
    catalog = json.loads(CATALOG.read_text())
    require(catalog['base_rom_sha256'] == digest(build.original), 'Synthesis base differs')
    require(len(catalog['entries']) == len(INDICES) and {r['index'] for r in catalog['entries']} == INDICES, 'Synthesis source selection differs')
    sources = entries(); pointers = [RAM + r['start'] for r in sources]; rows = []
    for row in catalog['entries']:
        source = sources[row['index']]
        raw = resource()['data'][source['start']:source['end_exclusive']]
        require(row['status'] == 'reviewed' and row['prose_review'] and row['source_id'] == source['id'], 'Synthesis review differs')
        require(raw.hex() == row['source_hex'] and digest(raw) == row['source_sha256'], 'Synthesis source differs')
        payload, layout = compile_row(row, source)
        offset = build.allocate(row['id'], payload, 'gaibara-text')
        pointers[row['index']] = offset + 0x08000000
        rows.append(row | {'offset': offset, 'encoded_hex': payload.hex(), 'layout': layout})
    table = build.allocate('gaibara-private-town-table', struct.pack('<300I', *pointers), 'gaibara-text')
    helper = (len(build.data) + 3) & ~3
    assembly = f'''.gba
.create "gaibara.bin", 0x{helper + 0x08000000:08x}
.thumb
    push {{r4,r5,r6,r7,lr}}
    mov r7,r10
    mov r6,r9
    mov r5,r8
    ldr r0,=0x{table + 0x08000000:08x}
    ldr r3,=0x0801d54d
    bx r3
    .align 4
    .pool
.close
'''
    with tempfile.TemporaryDirectory(prefix='gaibara-asm-') as directory:
        folder = Path(directory); (folder / 'gaibara.asm').write_text(assembly)
        subprocess.run([str(ROOT / '.tools/bin/armips'), 'gaibara.asm'], cwd=folder, check=True)
        payload = (folder / 'gaibara.bin').read_bytes()
    require(build.allocate('gaibara-entry-helper', payload, 'gaibara-text') == helper, 'Synthesis helper alignment differs')
    build.patch('gaibara-entry', 0x1D544, bytes.fromhex('f0b557464e464546'),
                bytes.fromhex('004b1847') + struct.pack('<I', helper + 0x08000001), 'gaibara-text')
    return {'entries': rows, 'table_offset': table, 'helper_offset': helper, 'assembly': assembly,
            'catalog_sha256': digest(CATALOG.read_bytes()), 'scope': catalog['scope']}
