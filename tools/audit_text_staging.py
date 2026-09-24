"""Separate reviewed coverage, available draft wording and unresolved inventory."""
import json
from collections import Counter
from tools.rom import ROOT, digest, require
from tools.compact_font import encode, measure


def run():
    inventory = json.loads((ROOT / 'build/text-inventory/catalog.json').read_text())['entries']
    by_id = {r['id']: r for r in inventory}
    available = {}
    catalogs = {}

    def add(source, english, path, ident):
        raw = source['raw_hex']
        sha = source.get('sha256', source.get('source_sha256'))
        require(digest(bytes.fromhex(raw)) == sha, 'Stale staged source: ' + str(ident))
        require(any(r['source_sha256'] == sha and r['raw_hex'] == raw for r in inventory),
                'Staged source absent from inventory: ' + str(ident))
        if english is not None and english.strip():
            available.setdefault(sha, []).append({'catalog': str(path.relative_to(ROOT)), 'id': ident})

    for path in sorted((ROOT / 'translations').glob('*-draft.json')):
        catalogs[str(path.relative_to(ROOT))] = digest(path.read_bytes())
        data = json.loads(path.read_text())
        for row in data.get('entries', []):
            if 'source_sha256' in row:
                require(row['id'] in by_id, 'Unknown draft identity')
                original = by_id[row['id']]
                require(all(row[k] == original[k] for k in ('raw_hex', 'source_sha256', 'japanese')),
                        'Stale staged identity: ' + row['id'])
                add(row, row.get('english_draft'), path, row['id'])
                if path.name == 'remaining-labels-draft.json':
                    require(row['static_line_widths'] == [measure(s) for s in row['english_draft'].split('\n')]
                            and row['encoded_bytes'] == len(encode(row['english_draft'])), 'Stale label measurements')
            elif path.name == 'shared-messages-draft.json':
                add(row['source'], row['english_draft'], path, row['id'])
            elif path.name == 'item-aliases-draft.json':
                if row['source']['disposition'] == 'end-marker':
                    continue
                add(row['source']['name'], row['canonical_name'], path, row['id'])
                require(row['name'] and measure(row['name']) <= 80 and len(encode(row['name'])) <= 31,
                        'Appearance display exceeds the proposed existing reserve')
                require(row['display_width_px'] == measure(row['name'])
                        and row['display_encoded_bytes'] == len(encode(row['name'])), 'Stale appearance measurement')
            elif path.name == 'items-remaining-draft.json':
                if row.get('canonical_name'):
                    add(row['source']['name'], row['canonical_name'], path, row['id'])
                if row.get('description_draft') and row['source'].get('description'):
                    add(row['source']['description'], row['description_draft'], path, row['id'])
    counts, families, unresolved = Counter(), {}, []
    for row in inventory:
        status = row['language_status']
        if status == 'untranslated':
            status = 'draft_wording_available' if row['source_sha256'] in available else 'unresolved_without_draft'
        counts[status] += 1
        families.setdefault(row['family'], Counter())[status] += 1
        if status == 'unresolved_without_draft':
            unresolved.append({k: row[k] for k in ('id', 'family', 'japanese', 'source_sha256')})
    report = {'passed': True, 'inventory_sources': len(inventory), 'counts': counts,
              'families': families, 'catalog_sha256': catalogs, 'unresolved': unresolved,
              'scope': 'Known extracted inventory only; not proof of complete ROM extraction. Draft wording is matched by exact source bytes/hash and is not promoted to a reviewed translation or accepted native consumer. Aliases retain full canonical names plus measured display proposals; marker/control/placeholder reachability still needs investigation.'}
    out = ROOT / 'build/text-next/staging-coverage.json'
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print('Known inventory staging:', dict(counts))
    return report


if __name__ == '__main__':
    run()
