"""Audit shared-message staging without implying insertion or native coverage."""
import json
import re
from tools.compact_font import measure
from tools.rom import ROOT, digest, require

FORMAT = re.compile(rb'%(?:[-+ #0]*\d*)?l?[dsc]')
ARG = re.compile(r'\{arg(\d+)\}')
TOKEN = re.compile(r'\{(?:arg\d+|player|center|tab|color:[56]|/color)\}')


def run():
    original = json.loads((ROOT / 'build/shared-text/catalog.json').read_text())
    sources = {row['table_offset']: row for row in original['entries']}
    path = ROOT / 'translations/shared-messages-draft.json'
    data = json.loads(path.read_text())
    rows, seen = [], set()
    for row in data['entries']:
        off, english = row['table_offset'], row['english_draft']
        require(off not in seen, 'Duplicate shared draft: ' + hex(off))
        seen.add(off)
        require(row['id'] == f'shared.{off:03x}', 'Incorrect shared draft ID')
        src = sources[off]
        require(row['source'] == src['source'] and row['pointer_offset'] == src['pointer_offset'],
                'Stale shared source: ' + row['id'])
        raw = bytes.fromhex(row['source']['raw_hex'])
        require(digest(raw) == row['source']['sha256'], 'Shared source digest differs')
        fields = [value.decode() for value in FORMAT.findall(raw)]
        require(fields == row['format_fields'], 'Incorrect format fields: ' + row['id'])
        args = [int(value) for value in ARG.findall(english)]
        require(sorted(args) == list(range(1, len(fields) + 1)), 'Lost/repeated argument: ' + row['id'])
        require(all(c == '\n' or 32 <= ord(c) <= 126 for c in english), 'Unsupported draft glyph')
        literal = TOKEN.sub('', english)
        require('{' not in literal and '}' not in literal, 'Unclassified English token')
        widths = [measure(line) for line in literal.split('\n')]
        require(widths == row['static_line_widths'], 'Stale draft static widths: ' + row['id'])
        order_changed = args != list(range(1, len(fields) + 1))
        if order_changed:
            require('reorder' in row['notes'] or 'reverses' in row['notes'],
                    'Undocumented argument reorder: ' + row['id'])
        rows.append({'id': row['id'], 'argument_reorder_needs_adapter': order_changed,
                     'static_line_widths': widths, 'dynamic_fields': fields,
                     'literal_exceeds_dialogue_budget': max(widths, default=0) > 216,
                     'dedicated_semantic_pass': bool(row.get('bilingual_review')),
                     'context_pending': row.get('bilingual_review', {}).get('context_pending', True),
                     'native_acceptance': False})
    dispositions = json.loads((ROOT / 'translations/shared-source-dispositions.json').read_text())
    require(dispositions['draft_catalog_sha256'] == digest(path.read_bytes()), 'Stale shared dispositions')
    for row in dispositions['entries']:
        off = row['table_offset']
        require(off not in seen, 'Overlapping shared disposition')
        seen.add(off)
        require(row['source'] == sources[off]['source'] and row['pointer_offset'] == sources[off]['pointer_offset'],
                'Stale shared disposition source')
    require(seen == set(sources), 'Unaccounted shared pointer slots')
    report = {'passed': True, 'catalog_sha256': digest(path.read_bytes()), 'drafts': len(rows),
              'dispositions': len(dispositions['entries']), 'accounted_pointer_slots': len(seen),
              'dedicated_semantic_pass': sum(row['dedicated_semantic_pass'] for row in rows),
              'entries': rows,
              'scope': 'Source bytes, format fields, placeholder multiplicity, documented argument reordering and static widths only. Dynamic widths, authored wrapping, controls, consumer ownership, gameplay reachability and native insertion remain unaccepted. Literal widths do not establish a one-line fit.'}
    out = ROOT / 'build/text-next/shared-draft-audit.json'
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + '\n')
    print('Shared drafts:', len(rows), '; source/placeholder/static-width audit passes')
    return report


if __name__ == '__main__':
    run()
