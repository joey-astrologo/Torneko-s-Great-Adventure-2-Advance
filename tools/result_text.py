"""Private result/history actor names and monster-defeat format, with original geometry."""
import json
import struct
from tools.compact_font import encode, measure
from tools.extract_monsters import extract
from tools.extract_shared_text import extract as shared
from tools.rom import ROOT, digest, require

CATALOG = ROOT / 'translations/results-review.json'
NAMES = ROOT / 'translations/monsters-review.json'


def add_results(build):
    catalog = json.loads(CATALOG.read_text())
    names = json.loads(NAMES.read_text())
    original = build.original
    require(catalog['base_rom_sha256'] == names['base_rom_sha256'] == digest(original), 'Result base changed')
    sources = extract()['entries']
    require([r['id'] for r in names['entries']] == list(range(141)), 'Raw actor coverage differs')
    table, rows = bytearray(), []
    for row, source in zip(names['entries'], sources):
        require(row['status'] == 'reviewed' and row['raw_table'] == source['raw_table'], 'Raw actor review differs')
        text, payload = row['english'], encode(row['english'])
        require(measure(text) <= 114 and len(payload) <= 64, 'Raw actor budget exceeded')
        offset = build.allocate('result-actor-' + str(row['id']), payload, 'results')
        table.extend(struct.pack('<I', offset + 0x08000000))
        rows.append({'id': row['id'], 'english': text, 'source': row['raw_table'], 'offset': offset,
                     'encoded_hex': payload.hex(), 'width_px': measure(text)})
    table.extend(b'\0' * 4)
    raw_table = build.allocate('result-actor-table', bytes(table), 'results')
    for offset in (0x1CBBC, 0x56FEC):
        build.patch('result-actor-pointer-' + hex(offset), offset, struct.pack('<I', 0x08144C38),
                    struct.pack('<I', raw_table + 0x08000000), 'results')
    row = next(r for r in catalog['entries'] if r['table_offset'] == 0x654)
    source = next(r['source'] for r in shared()['entries'] if r['table_offset'] == 0x654)
    require(row['status'] == 'reviewed' and row['source'] == source and row['english'] == 'Defeated by {actor}.',
            'Result format review differs')
    payload = encode('Defeated by ')[:-1] + b'%s' + encode('.')
    width = max(measure(row['english'].replace('{actor}', r['english'])) for r in rows)
    size = max(len(payload) - 3 + len(bytes.fromhex(r['encoded_hex'])) for r in rows)
    require(width <= 212 and size <= 128, 'Result format exceeds tighter history/result capacity')
    offset = build.allocate(row['id'], payload, 'results')
    private = bytearray(original[0x140D68:0x140D68 + 654 * 4])
    struct.pack_into('<I', private, 0x654, offset + 0x08000000)
    causes, other = [], None
    shared_sources = {r['table_offset']: r['source'] for r in shared()['entries']}
    for reviewed in catalog['entries']:
        if reviewed['table_offset'] == 0x654: continue
        require(reviewed['status'] == 'reviewed' and reviewed['source'] == shared_sources[reviewed['table_offset']],
                'Result cause source/review differs')
        is_format = reviewed['table_offset'] == 0x6D4
        if is_format:
            require(reviewed['english'] == 'Fell {cause}.', 'Result cause wrapper changed')
            encoded = encode('Fell ')[:-1] + b'%s' + encode('.')
        else:
            require(reviewed['reason'] in set(range(28)) - {21} and
                    reviewed['table_offset'] == 0x658 + 4 * reviewed['reason'], 'Unowned result cause')
            require(not any(c in reviewed['english'] for c in '{}%\n\r'), 'Result cause controls unsupported')
            encoded = encode(reviewed['english'])
            require(measure('Fell '+reviewed['english']+'.') <= 212 and len(encoded)+len(encode('Fell .'))-1 <= 128,
                    'Result cause exceeds original limits')
        address = build.allocate(reviewed['id'], encoded, 'results')
        struct.pack_into('<I', private, reviewed['table_offset'], address+0x08000000)
        compiled = reviewed | {'offset': address, 'encoded_hex': encoded.hex()}
        if is_format: other = compiled
        else: causes.append(compiled)
    if causes:
        require(other and {r['reason'] for r in causes} == set(range(28))-{21}, 'Result cause coverage differs')
        other['maximum_width'] = max(measure('Fell '+r['english']+'.') for r in causes)
        other['maximum_bytes'] = max(len(bytes.fromhex(r['encoded_hex']))+len(bytes.fromhex(other['encoded_hex']))-3 for r in causes)
    from tools.result_ui_text import compile_ui
    ui_entries = compile_ui(build, catalog, private, shared_sources)
    copy = build.allocate('result-shared-table', bytes(private), 'results')
    for literal in (0x1CBA4, 0x56FE4):
        build.patch('result-shared-pointer-' + hex(literal), literal, struct.pack('<I', 0x08140D68),
                    struct.pack('<I', copy + 0x08000000), 'results')
    if ui_entries:
        for literal in (0x1CD3C,0x1CDC4,0x1CE30,0x1CE8C,0x1CF5C) + ((0x570A4,0x571B4) if any(r['table_offset']==0x6D8 for r in ui_entries) else ()):
            build.patch('result-ui-table-'+hex(literal),literal,struct.pack('<I',0x08140D68),
                        struct.pack('<I',copy+0x08000000),'results-ui')
    fallback = catalog['history_zero_actor']
    s = fallback['source']; raw = original[s['offset']:s['end_exclusive']]
    require(fallback['status'] == 'reviewed' and fallback['english'] == 'Torneko' and
            raw.hex() == s['raw_hex'] and digest(raw) == s['sha256'], 'History zero actor differs')
    encoded = encode(fallback['english'])
    target = build.allocate(fallback['id'], encoded, 'results')
    pointer = build.allocate('result-history-zero-pointer', struct.pack('<I', target + 0x08000000), 'results')
    build.patch('result-history-zero-literal', 0x57008, struct.pack('<I', 0x0815460C),
                struct.pack('<I', pointer + 0x08000000), 'results')
    result = {'entries': rows, 'causes': causes, 'other_defeat': other, 'formats': [row | {'offset': offset, 'encoded_hex': payload.hex(),
            'maximum_width': width, 'maximum_bytes': size}],
            'history_zero_actor': fallback | {'offset': target, 'encoded_hex': encoded.hex()},
            'raw_table': raw_table, 'shared_table': copy,
            'catalog_sha256': digest(CATALOG.read_bytes()), 'names_sha256': digest(NAMES.read_bytes()),
            'scope': catalog['scope']}
    if ui_entries: result['ui_entries'] = ui_entries
    return result
