"""Bind the native-confirmed missed consumers, preserving unowned table slots."""
import json
import re
import struct
from collections import defaultdict

from tools.compact_font import encode, measure
from tools.extract_items import source
from tools.extract_shared_text import START, END
from tools.inventory_action_text import CONTROL
from tools.rom import ROOT, digest, require

CATALOG = ROOT / 'translations/caller-repairs-review.json'
FIELD_WIDTHS = {'actor': 186, 'item': 162, 'amount': 66}
FIELD_BYTES = {'actor': 63, 'item': 63, 'amount': 11}


def add_caller_repairs(build, item_loss):
    catalog = json.loads(CATALOG.read_text())
    require(catalog['base_rom_sha256'] == digest(build.original), 'Caller repair base differs')
    require(len(catalog['entries']) == 35 and len(catalog['bindings']) == 55,
            'Caller repair cohort differs')
    rows = []
    for row in catalog['entries']:
        text, src = row['english'], row['source']
        require(row['status'] == 'reviewed' and source(build.original, src['offset']+0x08000000) == src,
                'Caller repair source/review differs')
        fields = re.findall(r'\{(actor|item|amount)\}', text)
        require(fields == row['fields'] and not re.search(r'[{}%\r]', re.sub(r'\{(?:actor|item|amount|fit)\}', '', text)),
                'Caller repair fields differ')
        payload = b''.join(b'%s' if p in ('{actor}', '{item}') else b'%d' if p == '{amount}'
                           else CONTROL if p == '{fit}' else encode(p)[:-1]
                           for p in re.split(r'(\{[^}]+\})', text)) + b'\0'
        require(re.findall(b'%[sd]', payload) == re.findall(b'%[sd]', bytes.fromhex(src['raw_hex'])),
                'Caller repair argument order differs')
        widths = [measure(re.sub(r'\{(?:actor|item|amount)\}', '', part)) +
                  sum(FIELD_WIDTHS[f] for f in re.findall(r'\{(actor|item|amount)\}', part))
                  for part in re.split(r'\{fit\}|\n', text)]
        maximum = len(payload) + sum(FIELD_BYTES[f]-2 for f in fields)
        require(max(widths) <= row['width_budget'] and maximum <= 256,
                f'Caller repair exceeds native bounds: {row["id"]}')
        # Reuse only an entire owned allocation with identical bytes.
        old = next((a for a in build.allocations if a['end_exclusive']-a['start'] == len(payload)
                    and build.data[a['start']:a['end_exclusive']] == payload), None)
        at = old['start'] if old else build.allocate(row['id'], payload, 'caller-repairs')
        rows.append(row | {'offset': at, 'encoded_hex': payload.hex(), 'maximum_bytes': maximum,
                          'maximum_line_widths': widths, 'capacity': 256 if fields else 'direct-ROM',
                          'reused_payload': bool(old)})
    by_source = {r['source']['offset']: r for r in rows}
    groups = defaultdict(list)
    for binding in catalog['bindings']:
        at = binding['call_context_offset']
        expected = bytes.fromhex(binding['call_context_hex'])
        require(build.original[at:at+len(expected)] == expected, 'Caller code evidence differs')
        groups[binding['literal_offset']].append(binding)
    tables, bindings = {}, []
    for literal, group in groups.items():
        original, relative = group[0]['expected_literal'], group[0]['table_relative']
        require(all(b['expected_literal'] == original and b['table_relative'] == relative for b in group),
                'Inconsistent caller literal ownership')
        sources = tuple(sorted({b['source_offset'] for b in group}))
        inherited = item_loss.get('table_offset') if literal == 0x38D08 else None
        signature = (inherited, sources)
        if relative is None:
            require(len(sources) == 1 and original == sources[0]+0x08000000, 'Direct caller source differs')
            pointer = by_source[sources[0]]['offset']+0x08000000
        else:
            require(original == START+relative+0x08000000, 'Caller table base differs')
            if signature not in tables:
                table = bytearray(build.data[inherited:inherited+END-START] if inherited is not None
                                  else build.original[START:END])
                for address in sources:
                    row = by_source[address]
                    slot = row['table_offset']
                    require(slot is not None and struct.unpack_from('<I', table, slot)[0] == address+0x08000000,
                            'Caller table slot differs')
                    struct.pack_into('<I', table, slot, row['offset']+0x08000000)
                tables[signature] = build.allocate(f'caller-private-table-{literal:x}', bytes(table), 'caller-repairs')
            pointer = tables[signature]+relative+0x08000000
        build.patch(f'caller-binding-{literal:x}', literal, struct.pack('<I', original),
                    struct.pack('<I', pointer), 'caller-repairs')
        bindings.extend(b | {'compiled_literal': pointer, 'compiled_source': by_source[b['source_offset']]['offset']+0x08000000}
                        for b in group)
    return {'entries': rows, 'bindings': bindings, 'table_count': len(tables),
            'literal_count': len(groups), 'new_source_count': 2,
            'catalog_sha256': digest(CATALOG.read_bytes()), 'scope': catalog['scope']}
