"""Join caller arguments to downstream Japanese glyphs, preserving unresolved leads."""
import argparse
import html
import json
from pathlib import Path
import struct

from tools.audit_text_callers import CONSUMERS
from tools.rom import ROOT, digest, load_base, require


def output_evidence(row, case):
    """Follow the observed destination through native copies/wrappers to glyphs."""
    if case['route_error'] or not case['confirmed_japanese_output']:
        return []
    matches = []
    for index, event in enumerate(case['calls']):
        if (event['call'] != row['call'] or event['consumer'] != row['consumer'] or
            event['arguments'][CONSUMERS[row['consumer']][1]] != row['compiled_argument']):
            continue
        destinations = {event['arguments'][0] if row['consumer'] in (0x08000FB8,0x0805CF54)
                        else row['compiled_argument']}
        # The player wrapper formats the first buffer into a second stack buffer.
        # Observe that native forwarding; an unrelated Japanese glyph is not proof.
        for later in case['calls'][index+1:]:
            if later['consumer'] in (0x08000FB8,0x0805CF54) and later['arguments'][1] in destinations:
                destinations.add(later['arguments'][0])
        glyphs = [g for g in case['unclassified_glyphs'] if g['frame'] >= event['frame']]
        readers = sorted({g['reader_source'] for g in glyphs if g['reader_source'] in destinations})
        queues = [i for i,q in enumerate(case['final_queues']) if q['source'] in destinations and
                  q['frame'] >= event['frame'] and any(g.get('final_queue') == i for g in glyphs)]
        if readers or queues:
            matches.append(dict(case=case['case'], caller_frame=event['frame'],
                                reader_sources=readers, final_queue_indices=queues,
                                observed_destinations=sorted(destinations)))
    return matches


def run(folder):
    static_path = folder/'static-wrappers.json'
    static = json.loads(static_path.read_text())
    build = json.loads((ROOT/'build/english/build.json').read_text())
    require(static['rom_sha256'] == build['output_sha256'], 'Static/build ROM mismatch')
    require(static['tool_sha256'] == digest((ROOT/'tools/audit_text_callers.py').read_bytes()), 'Static tool changed')
    native_paths = [folder/'native/report.json',folder/'followup/report.json']
    cases = []
    for path, tool in zip(native_paths, ['audit_caller_cases','audit_caller_followup']):
        native = json.loads(path.read_text())
        require(native['rom_sha256'] == static['rom_sha256'], 'Native ROM mismatch')
        require(native['tool_sha256'] == digest((ROOT/f'tools/{tool}.py').read_bytes()), 'Native tool changed')
        require(native['original_files_unchanged'] and all(c['battery_unchanged'] for c in native['cases']), 'Battery/source changed')
        for case in native['cases']:
            for img in case['images']:
                require(digest((path.parent/case['case']/img['path']).read_bytes()) == img['png_sha256'], 'Screenshot changed')
            cases.append(case | {'evidence_directory': str(path.parent.relative_to(folder))})
    findings, copies = [], []
    for row in static['candidate_routes']:
        if row['disposition'] not in ('original_japanese_argument_needs_followup','copied_japanese_requires_reader_followup'):
            continue
        witnesses = [w for c in cases for w in output_evidence(row,c)]
        matched = sorted({w['case'] for w in witnesses})
        item = {k:v for k,v in row.items() if k != 'path'} | dict(
            status='native-japanese-confirmed' if matched else 'static-candidate-unconfirmed',
            native_cases=matched, downstream_evidence=witnesses,
            normal_buttons_after_state_setup=[c['case'] for c in cases if c['case'] in matched and c['entry'] is None])
        if row['consumer'] == 0x0805CF54:
            controls = [c['case'] for c in cases if c['english_output'] and any(
                e['consumer'] == row['consumer'] and e['call'] == row['call'] and
                e['arguments'][1] == row['compiled_argument'] for e in c['calls'])]
            item['english_control_cases'] = controls
            if controls and not matched:
                item['status'] = 'native-english-through-downstream-remap'
            copies.append(item)
        else:
            findings.append(item)
    confirmed = [r for r in findings if r['native_cases']]
    first_path = folder/'first-pass-summary.json'
    first = json.loads(first_path.read_text())
    old_open = {r['call'] for r in first['findings'] if r['status']=='static-candidate-unconfirmed'}
    confirmed_calls = {r['call'] for r in confirmed}
    # Options help selects four finite 8-entry rows, not an unbounded table walk.
    original = load_base()
    selectors = list(struct.unpack_from('<32H', original, 0x6B736))
    require(all(struct.unpack_from('<I', original, 0x140D68+4*i)[0] != 0x08064410 for i in selectors),
            'Options false-positive exclusion differs')
    require(not any(r['call']==0x0801A9B0 and r['original_argument']==0x08064410 for r in findings),
            'Impossible options candidate survived bounded comparisons')
    excluded = dict(call=0x0801A9B0, original_argument=0x08064410,
                    status='excluded-impossible-option-help-selector', selectors=selectors,
                    evidence='remaining-owners.txt:0801A794. Four modes, eight entries per mode; '
                             'no selector points to the cursed notice. CMP-aware loop tracing removes the false lead.')
    negative_path = folder/'static-negative-control-current.json'
    negative = json.loads(negative_path.read_text())
    require(negative['tool_sha256'] == static['tool_sha256'], 'Negative-control tool differs')
    checks = []
    for call in (0x08016FAA,0x08017224):
        before = [r for r in negative['candidate_routes'] if r['call']==call]
        now = [r for r in static['candidate_routes'] if r['call']==call]
        require(len(before)==len(now)==1 and before[0]['disposition']=='original_japanese_argument_needs_followup'
                and now[0]['disposition']=='bound_english_resource', 'Known-reader negative control failed')
        checks.append(dict(call=call,before=before[0]['disposition'],current=now[0]['disposition']))
    expiry_path = ROOT/'build/status-expiry/native/report.json'
    expiry = json.loads(expiry_path.read_text())
    require(expiry['rom_sha256']==static['rom_sha256'], 'Expiry evidence differs')
    resolved = [c for c in expiry['cases'] if c['case'] in ('timer-9a-selector-0f0','timer-9c-selector-0f8')]
    require(len(resolved)==2 and all(c['english_output'] for c in resolved), 'Earlier expiry is not fixed')
    incomplete = [dict(case=c['case'],reason=c['route_error']) for c in cases if c['route_error']]
    report = dict(audit_pass_finished=True, discovery_complete=False,
                  localization_coverage_passed=False, rom_sha256=static['rom_sha256'],
                  tool_sha256=digest(Path(__file__).read_bytes()),
                  quoted_expiry_finding_resolved=True, confirmed_call_sites=len(confirmed),
                  confirmed_distinct_sources=len({r['original_argument'] for r in confirmed}),
                  additional_confirmed_since_first_pass=len(confirmed)-first['confirmed_call_sites'],
                  original_34_triage=dict(confirmed=len(old_open & confirmed_calls), excluded=1,
                      unresolved=sorted(old_open-confirmed_calls-{excluded['call']})),
                  static_candidates_unconfirmed=len(findings)-len(confirmed),
                  copied_source_followups=copies, excluded_candidates=[excluded],
                  native_cases=len(cases), native_japanese_cases=sum(c['confirmed_japanese_output'] for c in cases),
                  native_english_controls=sum(c['english_output'] for c in cases), incomplete_native_cases=incomplete,
                  normal_button_cases=sorted({c for r in confirmed for c in r['normal_buttons_after_state_setup']}),
                  unresolved_call_arguments=len(static['unresolved_calls']), direct_call_patterns=static['direct_call_patterns'],
                  consumer_counts=static['consumer_counts'], candidate_dispositions=static['disposition_counts'],
                  budget_limited_seeds=len(static['budget_limits']), findings=findings,
                  known_reader_negative_control=checks,
                  scope='Diagnostic audit; confirmed sources are linked from caller arguments through observed native '
                  'buffers to Japanese glyphs. Handler/state/RNG controls are distinguished from normal buttons. '
                  'Incomplete probes, static candidates, copied sources and unresolved arguments remain open. '
                  'No ROM fixes, whole-game pass, natural reachability proof or exhaustive defect count.')
    evidence = [static_path,*native_paths,first_path,negative_path,expiry_path,
                ROOT/'build/text-inventory/catalog.json']
    evidence += [folder/name for name in ['remaining-owners.txt','followup-owners.txt','dispatchers.txt',
                 'container-owners.txt','selection-helpers.txt','branch-helpers.txt','landing-helpers.txt',
                 'modal-owners.txt','extra-readers.txt','modal-reader.txt','exchange-success-block.txt']]
    pages = ['<!doctype html><meta charset="utf-8"><title>Caller audit evidence</title>',
             '<style>body{font:16px system-ui;background:#181818;color:#eee;margin:30px}a{color:#9cf}img{width:480px;image-rendering:pixelated}figure{display:inline-block;vertical-align:top;margin:12px}figcaption{max-width:480px}</style>',
             '<h1>Caller coverage audit — open findings</h1>',
             f'<p>{len(confirmed)} confirmed callers; {report["additional_confirmed_since_first_pass"]} added in the continuation. '
             f'{report["static_candidates_unconfirmed"]} further static candidates remain unconfirmed. '
             '<a href="summary.json">Full evidence and limitations</a></p>',
             '<p>These routes use normal buttons after recorded inventory/status/trap setup. '
             'The wider report includes controlled handlers and RNG choices. Findings have not been fixed.</p>']
    for name in report['normal_button_cases']:
        case = next(c for c in cases if c['case']==name)
        path = folder/case['evidence_directory']/name/'panel.png'
        require(path.exists(), 'Missing normal-button panel')
        evidence.append(path)
        ref = path.relative_to(folder).as_posix()
        pages.append(f'<figure><img src="{ref}" alt="{html.escape(name)}"><figcaption>'
                     f'<a href="{path.parent.relative_to(folder).as_posix()}/report.json">{html.escape(name)}</a></figcaption></figure>')
    report['evidence_sha256'] = {str(p.relative_to(ROOT)):digest(p.read_bytes()) for p in evidence}
    (folder/'summary.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    (folder/'index.html').write_text('\n'.join(pages)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in
          ('findings','copied_source_followups','evidence_sha256','scope','candidate_dispositions','excluded_candidates')},indent=2))
    return report


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--folder',type=Path,default=ROOT/'build/caller-audit')
    run(p.parse_args().folder)
