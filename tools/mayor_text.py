"""Own the village-renaming consumer's town text without changing shared readers."""
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

CATALOG = ROOT / 'translations/mayor-review.json'
INDICES = {99,206,207,209,210,211}


def compile_row(row, source):
    index, text = row['index'], row['english']
    if index in (206,210):
        # Eight legacy cells can reach this decoder even though new entry is seven.
        return compile_format(text, bytes.fromhex(row['source_hex']),
                              {'{village}': (b'%s', 112, 16)}, 256)
    payload, layout = compile_dialogue(text, source['tokens'])
    return payload, layout | {'direct_rom_stream': True}


def add_mayor(build):
    catalog = json.loads(CATALOG.read_text())
    require(catalog['base_rom_sha256'] == digest(build.original), 'Mayor base differs')
    require(len(catalog['entries']) == len(INDICES) and {r['index'] for r in catalog['entries']} == INDICES, 'Mayor source selection differs')
    sources = entries(); pointers = [RAM + r['start'] for r in sources]; rows = []
    for row in catalog['entries']:
        source = sources[row['index']]
        raw = resource()['data'][source['start']:source['end_exclusive']]
        require(row['status'] == 'reviewed' and row['prose_review'] and row['source_id'] == source['id'], 'Mayor review differs')
        require(raw.hex() == row['source_hex'] and digest(raw) == row['source_sha256'], 'Mayor source differs')
        payload, layout = compile_row(row, source)
        offset = build.allocate(row['id'], payload, 'mayor-text')
        pointers[row['index']] = offset + 0x08000000
        rows.append(row | {'offset': offset, 'encoded_hex': payload.hex(), 'layout': layout})
    table = build.allocate('mayor-private-town-table', struct.pack('<300I', *pointers), 'mayor-text')
    helper = (len(build.data) + 3) & ~3
    assembly = f'''.gba
.create "mayor.bin", 0x{helper + 0x08000000:08x}
.thumb
    push {{r4,r5,r6,r7,lr}}
    mov r7,r10
    mov r6,r9
    mov r5,r8
    ldr r0,=0x{table + 0x08000000:08x}
    ldr r3,=0x0802056d
    bx r3
    .align 4
    .pool
.close
'''
    with tempfile.TemporaryDirectory(prefix='mayor-asm-') as directory:
        folder = Path(directory); (folder / 'mayor.asm').write_text(assembly)
        subprocess.run([str(ROOT / '.tools/bin/armips'), 'mayor.asm'], cwd=folder, check=True)
        payload = (folder / 'mayor.bin').read_bytes()
    require(build.allocate('mayor-entry-helper', payload, 'mayor-text') == helper, 'Mayor helper alignment differs')
    build.patch('mayor-entry', 0x20564, bytes.fromhex('f0b557464e464546'),
                bytes.fromhex('004b1847') + struct.pack('<I', helper + 0x08000001), 'mayor-text')
    return {'entries': rows, 'table_offset': table, 'helper_offset': helper, 'assembly': assembly,
            'catalog_sha256': digest(CATALOG.read_bytes()), 'scope': catalog['scope']}
