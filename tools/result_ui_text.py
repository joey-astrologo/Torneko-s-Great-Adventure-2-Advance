"""Compile optional, owned result-panel labels into its private shared table."""
import re
import struct
from tools.compact_font import encode, measure
from tools.rom import require


def compile_ui(build, catalog, private, sources):
    rows = []
    fields = {'dungeon': ('s', 'More Magic Dungeon'), 'number': ('d', '-32768'),
              'score': ('d', '-2147483648'), 'exp': ('d', '-2147483648'),
              'strength': ('d', '-32768'), 'rank': ('s', 'Rank -32768'), 'item': ('s', 'W'*27)}
    permitted = set(range(0x5D0, 0x604, 4)) | {0x650,0x6E0,0x6E4,0x6CC,0x930,0x934,0x938,0x93C,0x940}
    supplied = catalog.get('ui_entries', [])
    if any(r['table_offset'] == 0x97C for r in supplied): permitted |= {0x97C,0x980,0x984}
    if any(r['table_offset']==0x6D8 for r in supplied): permitted |= {0x6D8,0x6DC,0x70C,0x71C,0x720,0x724,0x798,0x79C}
    if supplied: require({r['table_offset'] for r in supplied} == permitted, 'Result UI cohort incomplete')
    for row in supplied:
        slot, text = row['table_offset'], row['english']
        require(row['status'] == 'reviewed' and row['source'] == sources[slot] and slot in permitted,
                'Result UI source/review differs')
        raw = bytes.fromhex(row['source']['raw_hex'])
        payload, expanded, display, kinds = bytearray(), bytearray(), '', ''
        for part in re.split(r'(\{[^{}]+\})', text):
            if part in ('{color:6}', '{/color}'):
                value = b'\x03\x06' if part == '{color:6}' else b'\x05'
                payload.extend(value); expanded.extend(value)
            elif part.startswith('{'):
                require(part[1:-1] in fields, 'Unknown result UI field')
                kind, bound = fields[part[1:-1]]
                payload.extend(b'%' + kind.encode()); kinds += kind
                expanded.extend(bound.encode() if kind == 'd' else encode(bound)[:-1]); display += bound
            else:
                require(not any(c in part for c in '{}%\r\n'), 'Result UI contains unsupported controls')
                value = encode(part)[:-1]; payload.extend(value); expanded.extend(value); display += part
        require(re.findall(rb'%[sd]', raw) == [b'%' + c.encode() for c in kinds], 'Result UI field order/type changed')
        capacity = 64 if slot in (0x934, 0x938) else 128 if slot in (0x650, 0x6E0, 0x6E4) else 256
        budget = 224 if slot == 0x940 else 212
        payload.append(0); expanded.append(0)
        maximum_bytes = len(expanded) + (9 if '{item}' in text else 0)  # Independent63-content-byte item field.
        require(maximum_bytes <= capacity and measure(display) <= budget, 'Result UI exceeds native bounds')
        address = build.allocate(row['id'], bytes(payload), 'results-ui')
        struct.pack_into('<I', private, slot, address + 0x08000000)
        rows.append(row | {'offset': address, 'encoded_hex': payload.hex(), 'maximum_width': max(measure(display), 204 if '{item}' in text else 0),
                           'maximum_bytes': maximum_bytes, 'capacity': capacity, 'budget': budget, 'printf_kinds': kinds})
    return rows
