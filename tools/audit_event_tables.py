"""Account for every entry in the seven known event-bank text tables."""

from collections import Counter
import json

from tools.event_text import table_entries
from tools.opening_text import banks, manifest
from tools.rom import ROOT, digest, load_base, require
from tools.text_codec import readable, source_bytes
from tools.town_text import entries as town_entries, resource as town_resource

OUTPUT = ROOT / 'build/text-extraction'


def run(output=OUTPUT):
    catalog_bytes = (ROOT / 'translations/master.json').read_bytes()
    catalog = json.loads(catalog_bytes)
    require(catalog['source_rom_sha256'] == digest(load_base()), 'Catalog base differs')
    verified = {r['id']: r for r in catalog['entries']}
    entries, by_resource = [], {}
    for bank in banks():
        rows = table_entries(bank)
        by_resource[bank['id']] = rows
        for row in rows:
            raw = source_bytes(row['tokens'])
            require(raw == bank['data'][row['start']:row['end_exclusive']], 'Event source round trip differs')
            native = verified.get(row['id'])
            if native:
                require(native['raw_hex'] == raw.hex(), 'Table/native source bytes differ')
            entries.append({'id': row['id'], 'bank': bank['id'], 'group': row['group'], 'index': row['index'],
                            'slot': row['slot'], 'offset': row['start'], 'end_exclusive': row['end_exclusive'],
                            'raw_hex': raw.hex(), 'source_sha256': digest(raw), 'japanese': readable(row['tokens']),
                            'english': native.get('english') if native else None,
                            'status': 'native-source-verified' if native else 'table-referenced; natural use unverified',
                            'unresolved_tokens': [t for t in row['tokens'] if t.get('semantic_status') == 'unresolved']})
    town_rows = town_entries()
    by_resource['town-common'] = town_rows
    town_sources = []
    for row in town_rows:
        raw = source_bytes(row['tokens'])
        native = verified.get(row['id'])
        require(raw == town_resource()['data'][row['start']:row['end_exclusive']] and
                (native is None or raw.hex() == native['raw_hex']), 'Town source round trip differs')
        town_sources.append({k:v for k,v in row.items() if k != 'tokens'} |
                            {'raw_hex':raw.hex(), 'source_sha256':digest(raw), 'japanese':readable(row['tokens']),
                             'english':native.get('english') if native else None,
                             'status':'native-source-verified' if native else 'table-referenced; natural use unverified'})
    candidates_path = output / 'candidates.json'
    require(candidates_path.exists(), 'Candidate inventory missing; run tools.extract_text first')
    candidate_bytes = candidates_path.read_bytes()
    candidates = json.loads(candidate_bytes)
    if isinstance(candidates, dict):
        candidates = candidates['candidates']
    dispositions = []
    for candidate in candidates:
        related = by_resource.get(candidate['resource'], [])
        exact = [row['id'] for row in related if (row['start'], row['end_exclusive']) ==
                 (candidate['offset'], candidate['end_exclusive'])]
        inside = [row['id'] for row in related if row['start'] <= candidate['offset'] < candidate['end_exclusive'] <= row['end_exclusive']]
        dispositions.append({'id': candidate['id'], 'disposition': 'table-source' if exact else
                             'inside-table-source' if inside else 'unresolved', 'source_ids': exact or inside})
    report = {'passed': True, 'source_rom_sha256': digest(load_base()), 'bank_resources': manifest(),
              'catalog_sha256': digest(catalog_bytes), 'candidate_inventory_sha256': digest(candidate_bytes),
              'candidate_inventory_count': len(candidates),
              'table_entries': len(entries), 'unique_sources': len({r['id'] for r in entries}),
              'entries_per_bank': dict(Counter(r['bank'] for r in entries)),
              'native_sources': len({r['id'] for r in entries if r['status'] == 'native-source-verified'}),
              'shared_town': {'pointer_slots':len(town_rows), 'unique_sources':len({r['id'] for r in town_rows}),
                              'native_sources':len({r['id'] for r in town_sources if r['status'] == 'native-source-verified'})},
              'combined_unique_sources': len({r['id'] for r in entries + town_sources}),
              'candidate_dispositions': dict(Counter(r['disposition'] for r in dispositions)),
              'scope': 'Seven event tables, plus the separate shared-town table of 300 linked pointers. Event counts retain their original meaning; shared-town counts are separate. Candidate dispositions account for both families. Other resources and natural reachability remain open; no whole-game coverage percentage.'}
    output.mkdir(parents=True, exist_ok=True)
    for name, data in [('event-tables.json', entries), ('town-tables.json', town_sources), ('event-candidate-dispositions.json', dispositions),
                       ('event-table-audit.json', report)]:
        (output / name).write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({k:v for k,v in report.items() if k != 'bank_resources'}))
    return report


if __name__ == '__main__':
    run()
