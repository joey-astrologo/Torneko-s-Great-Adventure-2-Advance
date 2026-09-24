"""Require matching-ROM static notice coverage, fallbacks and exact captures."""
import json

from tools.rom import ROOT, digest, require


def validate(build, receipt, counts):
    folder = ROOT / 'build/english/queue-notice-validation'
    report = json.loads((folder / 'report.json').read_text())
    entries = build['combat']['queue_notices']['entries']
    ids = {r['id'] for r in entries} | {'fallback-japanese', 'fallback-english', 'fallback-ram'}
    require(report.get('visible_window_recipe') and all(r.get('final_screen_glyph_pixels_match') and
            r.get('screen_pixels_checked', 0) > 0 for r in report['cases']), 'Static queue captures lack visible glyph proof')
    require(report.get('copied_strings_tested'), 'Copied static notices were not tested')
    ids |= {r['id'] + '-copied' for r in entries} | {'fallback-japanese-prefix'}
    expected = {f'{ident}-flag{flag}' for ident in ids for flag in (0, 1)}
    cases = report['cases']
    require(report['passed'] and report['rom_sha256'] == build['output_sha256'],
            'Stale queue-notice native evidence')
    require(len(cases) == len(expected) and {r['case'] for r in cases} == expected,
            'Missing or duplicate queue-notice cases')
    by_id = {r['id']: r for r in entries}
    for case in cases:
        row = by_id.get(case['id'].removesuffix('-copied'))
        lines = row['english'].split('\n') if row else ['fallback']
        widths = case['queue']['line_widths']
        require(len(widths) == len(lines) <= 2 and max(widths) <= 216 and
                case['queue']['one_line'] == (len(lines) == 1), 'Queue notice authored line budget differs')
    preview = json.loads((folder / 'preview.json').read_text())
    images = {r['case'] + '/' + path: sha for r in cases for path, sha in r['images'].items()}
    require(preview['rom_sha256'] == build['output_sha256'] and
            preview['cases'] == len(cases) and preview['images'] == images,
            'Stale queue-notice gallery')
    for relative, sha in images.items():
        require(digest((folder / relative).read_bytes()) == sha, 'Queue-notice capture changed')
    for pattern in ('*.json', 'index.html', '*/*.png', '*/*.json', 'native/*.json'):
        for path in folder.glob(pattern):
            if path.is_file():
                receipt['artifacts'][str(path.relative_to(ROOT))] = digest(path.read_bytes())
    counts['queue-notices'] = len(cases)
    receipt.update(queue_notice_resources=len(entries), queue_notice_native_cases=len(cases),
                   queue_notice_scope=report['scope'])
