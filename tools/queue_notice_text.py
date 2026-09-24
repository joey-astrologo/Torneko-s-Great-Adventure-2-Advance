"""Closed pointer mapping for complete static notices at the dialogue queue."""
import json
import struct

from tools.compact_font import encode, load_font, measure
from tools.extract_shared_text import extract
from tools.rom import ROOT, digest, require

CATALOG = ROOT / 'translations/queue-notices-review.json'


def add_queue_notices(build):
    catalog = json.loads(CATALOG.read_text())
    require(catalog['base_rom_sha256'] == digest(build.original), 'Queue notice base differs')
    sources = {r['table_offset']: r['source'] for r in extract()['entries']}
    mapping, rows, seen, wordings = bytearray(), [], set(), {}
    font = load_font()
    for row in catalog['entries']:
        source, text = row['source'], row['english']
        require(row['status'] == 'reviewed' and row['review']['revised'] == text and
                row['review']['reason'], 'Queue notice review missing')
        require(source == sources[row['table_offset']] and
                all(sources[slot] == source for slot in row['equivalent_slots']),
                'Queue notice source/alias changed')
        raw = bytes.fromhex(source['raw_hex'])
        require(raw.endswith(b'\0') and b'\0' not in raw[:-1] and b'%' not in raw and
                all(c >= 32 or c == 13 for c in raw[:-1]) and '{' not in source['japanese'],
                'Queue notice contains controls or dynamic arguments')
        multiline = row.get('layout') == 'bounded-static-lines'
        require(not any(c in text for c in ('{}%\r' if multiline else '{}%\r\n')),
                'Queue notice contains unsupported English controls')
        lines = text.split('\n')
        require(1 <= len(lines) <= (2 if multiline else 1) and all(lines), 'Queue notice line count differs')
        widths = [measure(line, font) for line in lines]
        payload = b'\r'.join(encode(line)[:-1] for line in lines) + b'\0'
        width = max(widths)
        require(raw not in wordings or wordings[raw] == payload,
                'Identical static source bytes have conflicting English')
        wordings[raw] = payload
        require(width <= 216 and len(payload) <= 256, 'Queue notice exceeds native limits')
        pointer = 0x08000000 + source['offset']
        require(pointer not in seen, 'Duplicate queue notice source pointer')
        seen.add(pointer)
        offset = build.allocate(row['id'], payload, 'queue-notices')
        mapping.extend(struct.pack('<II', pointer, 0x08000000 + offset))
        rows.append(row | {'offset': offset, 'encoded_hex': payload.hex(),
                           'maximum_width': width, 'encoded_bytes': len(payload)})
        if multiline:
            rows[-1]['line_widths'] = widths
    require(0 < len(rows) <= 255, 'Unsupported queue mapping count')
    offset = build.allocate('queue-notice-pointer-map', bytes(mapping), 'queue-notices')
    return {'entries': rows, 'mapping_offset': offset, 'catalog_sha256': digest(CATALOG.read_bytes()),
            'scope': catalog['scope']}
