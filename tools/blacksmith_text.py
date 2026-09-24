"""Private text for the audited blacksmith consumer; original town table intact."""
import json
import re
import struct
import subprocess
import tempfile
from pathlib import Path
from tools.rom import ROOT, digest, require
from tools.town_text import entries, resource, RAM
from tools.compact_font import encode, measure
from tools.dialogue_layout import compile_dialogue
from tools.text_codec import tokenize

CATALOG = ROOT / 'translations/blacksmith-review.json'
INDICES = ({0} | set(range(3, 27)) | set(range(60, 79))) - {68}
FIELDS = {'{item1}': (b'%s', 80, 30), '{item2}': (b'%s', 80, 30),
          '{count}': (b'%d', 21, 3), '{player}': (b'\x7e', 98, 1)}
MARKER = re.compile(r'(\{[^{}]+\})')


def compile_row(row, source):
    text = row['english']
    raw = bytes.fromhex(row['source_hex'])
    original_fields = re.findall(b'%[sd]', raw)
    if not original_fields:
        payload, layout = compile_dialogue(text, source['tokens'])
        return payload, layout | {'direct_rom_stream': True}
    markers = MARKER.findall(text)
    require(all(m in FIELDS for m in markers), 'Unknown blacksmith field')
    require([FIELDS[m][0] for m in markers if m != '{player}'] == original_fields,
            'Blacksmith printf argument order differs')
    roles = ['{count}'] if original_fields == [b'%d'] else ['{item' + str(i + 1) + '}' for i in range(len(original_fields))]
    require([m for m in markers if m != '{player}'] == roles, 'Blacksmith argument roles differ')
    require(len(set(m for m in markers if m != '{player}')) == len(original_fields),
            'Repeated blacksmith printf field')
    # Enforce native non-printf controls independently of custom field layout.
    clean = re.sub(b'%[sd]', b'', raw)
    compile_dialogue(re.sub(r'\{(?:item[12]|count)\}', '', text), tokenize(clean)[0])

    def width(line):
        return measure(MARKER.sub('', line)) + sum(FIELDS[m][1] for m in MARKER.findall(line))

    pages = []
    for paragraph in text.split('\n\n'):
        lines, line = [], ''
        for word in paragraph.split():
            require(width(word) <= 216, 'Blacksmith word exceeds region')
            candidate = line + (' ' if line else '') + word
            if width(candidate) > 216:
                lines.append(line)
                line = word
            else:
                line = candidate
        require(line, 'Empty blacksmith paragraph')
        lines.append(line)
        pages.extend(lines[i:i + 2] for i in range(0, len(lines), 2))
    stream = ''
    for i, page in enumerate(pages):
        stream += '\n'.join(page)
        if i + 1 < len(pages):
            stream += '\n' * (3 - len(page))
    payload = b''.join(FIELDS[p][0] if p in FIELDS else encode(p)[:-1] for p in MARKER.split(stream)) + b'\0'
    maximum = len(payload) + sum(FIELDS[m][2] - len(FIELDS[m][0]) for m in markers)
    require(maximum <= 512, 'Blacksmith format exceeds 512-byte output')
    return payload, {'pages': pages, 'line_widths': [[width(line) for line in page] for page in pages],
                     'native_width': 224, 'capacity': 512, 'maximum_formatted_bytes': maximum,
                     'direct_rom_stream': False}


def add_blacksmith(build):
    catalog = json.loads(CATALOG.read_text())
    require(catalog['base_rom_sha256'] == digest(build.original), 'Blacksmith base differs')
    require(len(catalog['entries']) == len(INDICES) and {r['index'] for r in catalog['entries']} == INDICES,
            'Blacksmith owned source selection differs')
    sources = entries()
    pointers = [RAM + r['start'] for r in sources]
    rows = []
    for row in catalog['entries']:
        source = sources[row['index']]
        raw = resource()['data'][source['start']:source['end_exclusive']]
        require(row['status'] == 'reviewed' and row['prose_review'] and row['source_id'] == source['id'], 'Blacksmith review differs')
        require(raw.hex() == row['source_hex'] and digest(raw) == row['source_sha256'], 'Blacksmith source differs')
        payload, layout = compile_row(row, source)
        offset = build.allocate(row['id'], payload, 'blacksmith-text')
        pointers[row['index']] = offset + 0x08000000
        rows.append(row | {'offset': offset, 'encoded_hex': payload.hex(), 'layout': layout})
    table = build.allocate('blacksmith-private-town-table', struct.pack('<300I', *pointers), 'blacksmith-text')
    helper = (len(build.data) + 3) & ~3
    assembly = f'''.gba
.create "blacksmith.bin", 0x{helper + 0x08000000:08x}
.thumb
    push {{r4,r5,r6,r7,lr}}
    mov r7,r10
    mov r6,r9
    mov r5,r8
    ldr r0,=0x{table + 0x08000000:08x}
    ldr r3,=0x0801d119
    bx r3
    .align 4
    .pool
.close
'''
    with tempfile.TemporaryDirectory(prefix='blacksmith-asm-') as directory:
        folder = Path(directory)
        (folder / 'blacksmith.asm').write_text(assembly)
        subprocess.run([str(ROOT / '.tools/bin/armips'), 'blacksmith.asm'], cwd=folder, check=True)
        payload = (folder / 'blacksmith.bin').read_bytes()
    require(build.allocate('blacksmith-entry-helper', payload, 'blacksmith-text') == helper, 'Blacksmith helper alignment differs')
    build.patch('blacksmith-entry', 0x1D110, bytes.fromhex('f0b557464e464546'),
                bytes.fromhex('004b1847') + struct.pack('<I', helper + 0x08000001), 'blacksmith-text')
    return {'entries': rows, 'table_offset': table, 'helper_offset': helper, 'assembly': assembly,
            'catalog_sha256': digest(CATALOG.read_bytes()), 'scope': catalog['scope']}
