"""Join repaired callers to the frozen failure audit and current native evidence."""
import argparse
import html
import json
from pathlib import Path

from tools.rom import ROOT, digest, require


def run(source, folder):
    build = json.loads((source/'build.json').read_text())
    rom_hash = digest((source/'torneko-2-english.gba').read_bytes())
    require(rom_hash == build['output_sha256'], 'Acceptance ROM/ledger mismatch')
    family = build['caller_repairs']
    require(family['catalog_sha256'] == digest((ROOT/'translations/caller-repairs-review.json').read_bytes()),
            'Repair catalog changed')
    paths = [folder/'acceptance/report.json', folder/'floor/report.json', folder/'expiry/report.json',
             source/'item-loss-validation/report.json', folder/'repro.json', folder/'static.json']
    evidence = {}
    reports = []
    for path in paths:
        report = json.loads(path.read_text())
        require(report['rom_sha256'] == rom_hash, 'Mixed-ROM acceptance evidence')
        if path.name == 'report.json':
            require(report['passed'], 'Native acceptance failed')
        evidence[str(path.relative_to(ROOT))] = digest(path.read_bytes())
        reports.append(report)
    acceptance, floor, expiry, sibling, repro, static = reports
    baseline_path = ROOT/'build/caller-audit/summary.json'
    baseline = json.loads(baseline_path.read_text())
    confirmed = [r for r in baseline['findings'] if r['native_cases']]
    bindings = {b['call']: b for b in family['bindings']}
    require(len(confirmed) == 54 and all(r['call'] in bindings and
            bindings[r['call']]['source_offset']+0x08000000 == r['original_argument'] for r in confirmed),
            'Frozen failure cohort is not fully repaired')
    for binding in bindings.values():
        require(any(r['call'] == binding['call'] and r['compiled_argument'] == binding['compiled_source']
                    and r['disposition'] == 'bound_english_resource' for r in static['candidate_routes']),
                'Missing independent static binding')
    native_cases = []
    for profile in acceptance['profiles']:
        for name in ('first_report', 'followup_report'):
            path = ROOT/profile[name]
            report = json.loads(path.read_text())
            require(report['rom_sha256'] == rom_hash and all(c['english_output'] for c in report['cases']),
                    'Native caller case failed or ROM changed')
            tool = 'audit_caller_cases.py' if name == 'first_report' else 'audit_caller_followup.py'
            require(report['tool_sha256'] == digest((ROOT/'tools'/tool).read_bytes()), 'Native caller tool changed')
            evidence[str(path.relative_to(ROOT))] = digest(path.read_bytes())
            for case in report['cases']:
                for img in case['images']:
                    require(digest((path.parent/case['case']/img['path']).read_bytes()) == img['png_sha256'],
                            'Native screenshot changed')
                if profile['profile'] is None:
                    native_cases.append((path.parent, case))
    evidence[str(baseline_path.relative_to(ROOT))] = digest(baseline_path.read_bytes())
    for name in ('caller_binding_checks.py', 'caller_repair_text.py', 'screen_text_audit.py',
                 'verify_caller_repairs.py', 'audit_text_callers.py'):
        path = ROOT/'tools'/name
        evidence[str(path.relative_to(ROOT))] = digest(path.read_bytes())
    open_rows = [r for r in static['candidate_routes'] if r['disposition'] == 'original_japanese_argument_needs_followup']
    result = {'passed': True, 'rom_sha256': rom_hash, 'repaired_previously_confirmed_callers': 54,
              'additional_placeholder_binding': 0x0800EF64,
              'native_cases': sum(p['cases'] for p in acceptance['profiles']),
              'floor_cases': len(floor['cases']), 'expiry_cases': len(expiry['cases']),
              'pot_sibling_cases': len(sibling['cases']), 'reproduction': repro,
              'static_candidates_unconfirmed': len({r['call'] for r in open_rows}),
              'unresolved_call_arguments': len(static['unresolved_calls']),
              'unconfirmed_candidates': [{k:v for k,v in r.items() if k != 'path'} for r in open_rows],
              'evidence_sha256': evidence,
              'scope': 'All 54 confirmed untranslated callers repaired, plus compact recognition-blocked '
                       'placeholder. Remaining static/discovery leads are not counted as fixed or as '
                       'confirmed failures. The source catalog and whole-game discovery remain incomplete.'}
    (folder/'receipt.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
    pages = ['<!doctype html><meta charset="utf-8"><title>Caller repairs</title>',
             '<style>body{font:16px system-ui;background:#181818;color:#eee;margin:30px}a{color:#9cf}'
             'img{width:480px;image-rendering:pixelated}figure{display:inline-block;vertical-align:top;margin:12px}'
             'figcaption{max-width:480px}</style><h1>Caller repairs</h1>',
             '<p>54 confirmed failures repaired, plus the item placeholder; 308 native cases. '
             'Normal inputs after recorded item/status/trap setup are shown below. '
             '<a href="receipt.json">Evidence and remaining leads</a>.</p>']
    for parent, case in native_cases:
        if case['entry'] is not None or not case['binding_checks']:
            continue
        path = parent/case['case']/'panel.png'
        if path.exists():
            ref = path.relative_to(folder).as_posix()
            pages.append(f'<figure><img src="{ref}" alt="{html.escape(case["case"])}">'
                         f'<figcaption>{html.escape(case["case"])}</figcaption></figure>')
    (folder/'index.html').write_text('\n'.join(pages)+'\n')
    print('Accepted caller repairs:', rom_hash)
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path, default=ROOT/'build/english')
    p.add_argument('--folder', type=Path, default=ROOT/'build/caller-repair')
    args = p.parse_args()
    run(args.source.resolve(), args.folder.resolve())
