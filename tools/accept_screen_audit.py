"""Bind the bounded screen matrix to its ROM, actual frames and audit tools."""
import argparse
import html
import json
from pathlib import Path

from tools.audit_dungeon_screens import CASES, save_json
from tools.rom import ROOT, digest, require
from tools.screen_text_audit import glyph_text

OUT = ROOT/'build/coverage-audit'


def figure(path, caption):
    return (f'<figure><a href="{html.escape(path)}"><img loading="lazy" src="{html.escape(path)}" '
            f'alt="{html.escape(caption)}"></a><figcaption>{html.escape(caption)}</figcaption></figure>')


def drawn_text(glyphs):
    output, previous_row = [], None
    for glyph in glyphs:
        row = glyph.get('row')
        if previous_row is not None and row is not None and row != previous_row:
            output.append('\n')
        output.append({0x874F: '', 0x8750: '[equipped] '}.get(glyph['code'], glyph_text(glyph['code'])))
        previous_row = row
    return ''.join(output)


def run(controls=False):
    rom = (ROOT/'build/torneko-2-english.gba').read_bytes()
    release = json.loads((ROOT/'build/torneko-2-english.release.json').read_text())
    require(release['rom_sha256'] == digest(rom) and release['patch_apply_matches_rom'],
            'Release pair does not match the audited build')
    groups = {name: json.loads((OUT/name/'report.json').read_text()) for name in ('dungeon','town')}
    require({r['case'] for r in groups['dungeon']['cases']} == set(CASES), 'Missing dungeon scenario')
    require({r['case'] for r in groups['town']['cases']} ==
            {'town-root-outside','town-root-inside','bank-roundtrip','storage-roundtrip'}, 'Missing town scenario')
    matrix, sections = [], []
    for group, report in groups.items():
        require(report['rom_sha256'] == digest(rom) and report['original_files_unchanged'],
                'Screen report has stale build identity or changed originals')
        for row in report['cases']:
            folder = OUT/group/row['case']
            require(row['rom_sha256'] == digest(rom) and row['passed'] and not row['route_error'] and
                    not row['unclassified_glyphs'] and not row['unreadable_streams'] and
                    not row['layout_violations'], 'Screen audit has unresolved findings')
            for name, sha in row['tools_sha256'].items():
                require(digest((ROOT/'tools'/name).read_bytes()) == sha, 'Screen audit tooling changed: '+name)
            for capture in row['images']:
                require(digest((folder/capture['path']).read_bytes()) == capture['png_sha256'],
                        'Screen capture changed')
            controlled = bool(row['controlled_overrides'])
            matrix.append({'case': row['case'], 'ordinary_inputs_only': not controlled,
                'readers': len(row['reads']), 'queued_messages': sum(bool(q['drawn_codes']) for q in row['final_queues']),
                'glyphs': len(row['glyphs']), 'unclassified_glyphs': 0, 'layout_violations': 0,
                'capture_count': len(row['images']),
                'contextual_exceptions': sorted({x['reason'] for x in row['contextual_exceptions']}),
                'report': str((folder/'report.json').relative_to(OUT)),
                'report_sha256': digest((folder/'report.json').read_bytes())})
            scope = 'Controlled state, recorded in report' if controlled else 'Ordinary inputs; no state overrides'
            captures = [x for x in row['images'] if x['path'].startswith('text-')]
            selected = captures[-3:]
            if row['case'] == 'tutorial-three-floors':
                # Show one retained message image near each actual pickup.
                selected = []
                for pickup in row['pickups']:
                    found = next((x for x in captures if x['frame'] >= pickup['frame']), None)
                    if found and found not in selected:
                        selected.append(found)
            elif row['case'] in ('natural-gold-arrows-combat','maximum-gold'):
                selected = [x for x in captures if any(q['frame'] <= x['frame'] <= q['frame']+8 and
                    'Picked up' in q['text'] for q in row['final_queues'])]
            def image(capture):
                lo, hi = capture['glyph_range']
                caption = drawn_text(row['glyphs'][lo:hi])
                return figure(f"{group}/{row['case']}/{capture['path']}", caption)
            transcripts = [drawn_text(q['glyph_positions']) for q in row['reads']] + [
                ''.join(glyph_text(c) for c in q['drawn_codes']) for q in row['final_queues'] if q['drawn_codes']]
            sections.append(f'<section><h2>{html.escape(row["case"])}</h2><p>{scope}. '
                f'<a href="{group}/{row["case"]}/report.json">Inputs, readers and scope</a></p>'+
                ''.join(image(x) for x in selected)+
                f'<details><summary>All {len(captures)} timed text captures</summary>'+
                ''.join(image(x) for x in captures)+'</details>'+
                '<details><summary>Observed text</summary><pre>'+html.escape('\n\n'.join(transcripts))+'</pre></details></section>')
    tutorial = next(r for r in groups['dungeon']['cases'] if r['case']=='tutorial-three-floors')
    require(tutorial['all_14_pickups_matched'] and len(tutorial['pickups']) == 14, 'Tutorial pickup coverage differs')
    controls_result = None
    if controls:
        gold = json.loads((OUT/'negative-control/natural-gold-arrows-combat/report.json').read_text())
        banner = json.loads((OUT/'untranslated-banner-control/report.json').read_text())
        require(gold['route_error'] == 'Gold pickup lacks the English word space' and not gold['passed'],
                'Old gold control did not fail as expected')
        require(banner['rejected'] and banner['unclassified_glyphs'] and
                banner['generator_sha256'] == digest((ROOT/'tools/screen_text_audit.py').read_bytes()),
                'Unfiltered Japanese-banner rejection is absent/stale')
        controls_result = {'old_gold_rom': gold['rom_sha256'], 'old_banner_rom': banner['rom_sha256'],
                           'both_rejected': True}
    receipt = {'passed': True, 'rom_sha256': digest(rom), 'patch_sha256': release['patch_sha256'],
        'matrix': matrix, 'tutorial_pickups': 14, 'historical_controls': controls_result,
        'scope': '11 bounded scenarios, nine ordinary and two controlled. Every shared reader and glyph '
                 'observed; separate artwork/HUD paths reviewed visually in selected captures. '
                 'No claim of full-game, all-item or all-town-service coverage.'}
    save_json(OUT/'acceptance.json', receipt)
    table = '<table><tr><th>Scenario</th><th>Route</th><th>Reads</th><th>Messages</th><th>Unclassified</th></tr>'
    for r in matrix:
        table += f'<tr><td>{r["case"]}</td><td>{"ordinary" if r["ordinary_inputs_only"] else "controlled"}</td><td>{r["readers"]}</td><td>{r["queued_messages"]}</td><td>0</td></tr>'
    table += '</table>'
    before = OUT/'negative-control/natural-gold-arrows-combat/gold.png'
    comparison = '<h2>Gold spacing correction</h2>'
    if before.exists():
        comparison += figure(str(before.relative_to(OUT)), 'Before: Picked up 321Gold.')
    comparison += figure('dungeon/natural-gold-arrows-combat/gold.png', 'After: Picked up 321 Gold.')
    (OUT/'index.html').write_text('<!doctype html><html lang="en"><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1"><title>Torneko 2 text coverage audit</title>'
        '<style>body{background:#15212b;color:#edf5fb;font:16px system-ui;margin:32px;line-height:1.5}'
        'a{color:#9de6d0}figure{display:inline-block;vertical-align:top;margin:12px;max-width:480px}'
        'img{width:480px;max-width:100%;image-rendering:pixelated}figcaption{max-width:480px;overflow-wrap:anywhere}'
        'table{border-collapse:collapse}td,th{padding:8px;border:1px solid #526474;text-align:left}'
        'pre{white-space:pre-wrap}section{border-top:1px solid #526474;padding-top:16px;margin-top:32px}</style>'
        '<h1>Dungeon and town text audit</h1><p>11 checked scenarios: nine ordinary routes and two explicitly '
        'controlled cases. Includes 14 natural tutorial pickups across three floors. Whole-game coverage remains unverified.</p>'
        '<p>Actual mGBA frames. The earned Japanese save retains its player name トルネコ in item-use messages. '
        'That exact saved-name substitution is recorded separately from game-authored Japanese.</p>'
        '<p><a href="acceptance.json">Coverage receipt</a> · <a href="../torneko-2-english.gba">Latest ROM</a> · '
        '<a href="../torneko-2-english.bps">BPS patch</a></p>'+table+comparison+''.join(sections)+
        f'<p>ROM SHA256: {digest(rom)}</p></html>')
    print('Screen audit accepted:', len(matrix), 'scenarios; 14 tutorial pickups.')
    return receipt


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--historical-controls', action='store_true')
    run(parser.parse_args().historical_controls)
