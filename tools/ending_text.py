"""Private ending dialogue descriptors, preserving native timing and controls."""
import json
import re
import struct

from tools.rom import ROOT, digest, require
from tools.extract_items import source
from tools.text_codec import tokenize
from tools.dialogue_layout import compile_dialogue

CATALOG = ROOT / 'translations/ending-review.json'
TABLE = 0x153F20
END = 0x1541D8
SITES = ((0x55920, 0), (0x559B8, 18), (0x55A3C, 31),
         (0x55AD8, 35), (0x55B7C, 44))
SPECIAL = re.compile(r'\{wait:([Ww]):([0-9]+)\}|\{mode:([01])\}')


def special_command(raw):
    if len(raw) == 4 and raw[0] == raw[3] == 64 and raw[1] in (87, 119):
        require(raw[2] > 0, 'Ending delay operand must be nonzero')
        return '{wait:' + chr(raw[1]) + ':' + str(raw[2]) + '}'
    if raw in (b'\x130', b'\x131'):
        return '{mode:' + chr(raw[1]) + '}'
    return None


def compile_ending(english, tokens):
    controls = []
    adapted = []
    for token in tokens:
        raw = bytes.fromhex(token['raw_hex'])
        label = special_command(raw) if token['kind'] == 'command' else None
        if label:
            controls.append((label, raw))
            adapted.append({'kind': 'command', 'name': 'at-command', 'raw_hex': '404140'})
        else:
            adapted.append(token)
    require([m.group(0) for m in SPECIAL.finditer(english)] == [c[0] for c in controls],
            'Ending timing/mode controls changed')
    raw, layout = compile_dialogue(SPECIAL.sub('@A@', english), adapted)
    parts = raw.split(b'@A@')
    require(len(parts) == len(controls) + 1, 'Ending control adaptation count differs')
    compiled = parts[0] + b''.join(c[1] + p for c, p in zip(controls, parts[1:]))
    # The generic compiler also checks ordering relative to player/initial.
    # Reconstruct the human-readable layout without exposing adapter commands.
    labels = iter(c[0] for c in controls)
    layout['pages'] = [[re.sub('@A@', lambda _: next(labels), line) for line in page]
                       for page in layout['pages']]
    layout['ending_controls'] = [{'token': label, 'raw_hex': raw.hex()} for label, raw in controls]
    layout['encoded_bytes'] = len(compiled)
    layout.pop('commands')
    require([special_command(bytes.fromhex(t['raw_hex'])) for t in tokenize(compiled)[0]
             if t['kind'] == 'command' and special_command(bytes.fromhex(t['raw_hex']))]
            == [c[0] for c in controls], 'Compiled ending controls differ')
    return compiled, layout


def add_ending(build):
    catalog = json.loads(CATALOG.read_text())
    require(catalog['base_rom_sha256'] == digest(build.original), 'Ending base differs')
    require([r['index'] for r in catalog['entries']] == [i for i in range(58) if i != 43],
            'Ending descriptor cohort differs')
    table = bytearray(build.original[TABLE:END])
    require(struct.unpack_from('<III', table, 43 * 12) == (0x0806DADC, 0x300, 60),
            'Ending empty sentinel differs')
    rows = []
    for row in catalog['entries']:
        index = row['index']
        ptr, flags, timer = struct.unpack_from('<III', table, index * 12)
        original = source(build.original, ptr)
        require(row['status'] == 'reviewed' and row['source'] == original
                and row['record_offset'] == TABLE + 12 * index
                and (row['flags'], row['timer']) == (flags, timer), 'Ending source/descriptor differs')
        raw, layout = compile_ending(row['english'], tokenize(bytes.fromhex(original['raw_hex']))[0])
        at = build.allocate(row['id'], raw, 'ending-text')
        struct.pack_into('<I', table, 12 * index, 0x08000000 + at)
        rows.append(row | {'offset': at, 'encoded_hex': raw.hex(), 'layout': layout})
    at = build.allocate('ending-private-descriptors', bytes(table), 'ending-text')
    for literal, index in SITES:
        build.patch('ending-reader-' + hex(literal), literal,
                    struct.pack('<I', TABLE + 0x08000000 + 12 * index),
                    struct.pack('<I', at + 0x08000000 + 12 * index), 'ending-text')
    return {'entries': rows, 'table_offset': at, 'catalog_sha256': digest(CATALOG.read_bytes()),
            'scope': catalog['scope']}
