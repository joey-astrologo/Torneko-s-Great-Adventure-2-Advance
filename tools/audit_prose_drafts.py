"""Check staged prose identities and layouts without promoting it to acceptance."""
import json
import re
import unicodedata
from tools.dialogue_layout import compile_dialogue
from tools.rom import ROOT, digest, require
from tools.text_codec import tokenize


def normalized_japanese(text):
    text = unicodedata.normalize('NFKC', text)
    return re.sub(r'\s+', '', ''.join(chr(ord(c) - 0x60) if 'ァ' <= c <= 'ヶ' else c for c in text))


def run():
    inventory = json.loads((ROOT / 'build/text-inventory/catalog.json').read_text())
    source = {row['id']: row for row in inventory['entries']}
    files, seen = [], set()
    for path in sorted((ROOT / 'translations').glob('*-draft.json')):
        data = json.loads(path.read_text())
        entries = [row for row in data.get('entries', [])
                   if isinstance(row.get('id'), str)
                   and row['id'].startswith(('event-bank-', 'town-common.'))]
        if not entries:
            continue
        translated, reviewed, reconciled, layouts, blockers, fragments, blanks = [], [], [], [], [], [], []
        for row in entries:
            ident = row['id']
            require(ident not in seen, 'Duplicate prose draft identity: ' + ident)
            seen.add(ident)
            require(ident in source, 'Draft source is absent from inventory: ' + ident)
            for field in ('source_sha256', 'raw_hex', 'japanese'):
                require(row[field] == source[ident][field], 'Stale draft ' + field + ': ' + ident)
            require(digest(bytes.fromhex(row['raw_hex'])) == row['source_sha256'],
                    'Draft source hash differs: ' + ident)
            english = row.get('english_draft')
            if english == '' and not row['japanese'].strip():
                blanks.append(ident)
                continue
            if english is None:
                fragments.append(ident)
                continue
            require(isinstance(english, str) and english.strip(), 'Empty prose draft: ' + ident)
            translated.append(ident)
            if row.get('prose_review'):
                if row['prose_review'].get('method') == 'normalized-exact-reconciliation':
                    evidence = row['prose_review']['reviewed_source']
                    reference = json.loads((ROOT / 'translations' / evidence['catalog']).read_text())
                    original = next(r for r in reference['entries'] if r['id'] == evidence['id'])
                    require(original.get('prose_review') and original['source_sha256'] == evidence['source_sha256']
                            and normalized_japanese(original['japanese']) == normalized_japanese(row['japanese'])
                            and original['english_draft'] == english, 'Stale reconciled prose review: ' + ident)
                    reconciled.append(ident)
                else:
                    reviewed.append(ident)
            if ident.startswith('event-bank-'):
                try:
                    _, layout = compile_dialogue(english, tokenize(bytes.fromhex(row['raw_hex']))[0])
                except ValueError as exc:
                    require(row.get('layout_blocker') == str(exc), 'Unrecorded layout blocker: ' + ident)
                    blockers.append({'id': ident, 'reason': str(exc)})
                else:
                    require('layout_blocker' not in row and row.get('draft_layout') == layout,
                            'Stale draft layout: ' + ident)
                    layouts.append(ident)
        files.append({'path': str(path.relative_to(ROOT)), 'sha256': digest(path.read_bytes()),
                      'sources': len(entries), 'translated': len(translated),
                      'dedicated_bilingual_pass': len(reviewed), 'checked_event_layouts': len(layouts),
                      'reconciled_with_reviewed_source': len(reconciled),
                      'layout_blockers': blockers, 'untranslated_fragments': fragments,
                      'blank_sources_pending_control_review': blanks})
    report = {'passed': True, 'catalogs': files, 'unique_sources': len(seen),
              'translated_drafts': sum(row['translated'] for row in files),
              'dedicated_bilingual_pass': sum(row['dedicated_bilingual_pass'] for row in files),
              'reconciled_with_reviewed_source': sum(row['reconciled_with_reviewed_source'] for row in files),
              'scope': 'Staged prose only. Source identity and recorded compiler layouts checked. Counts include superseded drafts; native branch flow, control timing, terminology approval and insertion are separate. This does not promote drafts to reviewed master or accepted ROM coverage.'}
    output = ROOT / 'build/text-next/prose-draft-audit.json'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + '\n')
    print('Prose drafts:', report['translated_drafts'], 'translated;', len(seen), 'sources; identities/layouts pass')
    return report


if __name__ == '__main__':
    run()
