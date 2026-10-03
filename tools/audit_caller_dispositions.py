"""Join unresolved static callers with versioned, unfiltered native observations.

Observation of a caller establishes only the recorded cases, not all its states.
Historical ROM evidence stays separate and does not accept a newer ROM.
"""
import argparse
from collections import Counter
import json
from pathlib import Path

from tools.rom import ROOT, digest, require


def run(source, static, storage, evidence, output, selectors=None):
    rom = (source / 'torneko-2-english.gba').read_bytes()
    sha = digest(rom)
    scan = json.loads(static.read_text())
    store = json.loads(storage.read_text())
    require(scan['rom_sha256'] == store['rom_sha256'] == sha,
            'Caller disposition input ROMs differ')
    unknown = {r['call']: r for r in scan['argument_followup']
               if r['classification'] == 'unresolved-data-flow'}
    storage_calls = {r['call'] for r in store['routes']}
    for call in set(unknown) & storage_calls:
        matches = [r for r in store['routes'] if r['call'] == call]
        if all(r.get('binding') == 'bound-english-resource' for r in matches):
            del unknown[call]
    rows = {call: dict(call=call, call_hex=f'{call:08X}', consumer=row['consumer'],
                      current_observations=[], historical_observations=[])
            for call, row in unknown.items()}
    reports = []
    for root in evidence:
        root = root.resolve()
        for report_path in sorted(root.glob('*/report.json')):
            report = json.loads(report_path.read_text())
            if not report.get('passed') or not report.get('module'):
                continue
            report_sha = report['rom_sha256']
            found = {}
            for case in report['cases']:
                if not case['passed']:
                    continue
                path = report_path.parent / case['report']
                data = json.loads(path.read_text())
                calls = {r['call'] for r in data['calls']} & rows.keys()
                for call in calls:
                    found.setdefault(call, []).append(str(path.relative_to(ROOT)))
            reports.append(dict(path=str(report_path.relative_to(ROOT)),
                                sha256=digest(report_path.read_bytes()),
                                rom_sha256=report_sha, module=report['module'],
                                sessions=len(report['cases']),
                                hash_capture='start' if 'tools_unchanged' in report else
                                'legacy end-of-run capture; no loaded-code identity claim'))
            column = 'current_observations' if report_sha == sha else 'historical_observations'
            for call, cases in found.items():
                rows[call][column].append(dict(report=reports[-1]['path'],
                                               rom_sha256=report_sha, cases=cases))
    static_evidence = {}
    if selectors:
        proven = json.loads(selectors.read_text())
        require(proven['passed'] and proven['rom_sha256']==sha, 'Computed selector evidence differs')
        for entry in proven['actor_name_copies']:
            static_evidence[entry['copy_call']] = dict(kind='actor-name-getter-copy',evidence=entry)
        for entry in proven['bypassed_calls']:
            static_evidence[entry['old_interior_call']] = dict(kind='bypassed-by-owned-hook',evidence=entry)
    for row in rows.values():
        row['disposition'] = ('observed-on-current-ROM' if row['current_observations'] else
                              'observed-on-earlier-ROM-only' if row['historical_observations'] else
                              'not-observed-in-these-unfiltered-reports')
        row['static_evidence'] = static_evidence.get(row['call'])
        row['investigation'] = ('current-native-observation' if row['current_observations'] else
                                row['static_evidence']['kind'] if row['static_evidence'] else
                                'requires-current-evidence')
    report = dict(rom_sha256=sha, tool_sha256=digest(Path(__file__).read_bytes()),
                  static_report_sha256=digest(static.read_bytes()),
                  storage_report_sha256=digest(storage.read_bytes()),
                  counts=dict(Counter(r['disposition'] for r in rows.values())),
                  investigation_counts=dict(Counter(r['investigation'] for r in rows.values())),
                  selector_report_sha256=digest(selectors.read_bytes()) if selectors else None,
                  callers=list(rows.values()), evidence=reports, scope=__doc__)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2)+'\n')
    print('Caller observations:', report['counts'], flush=True)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=ROOT/'build/english')
    parser.add_argument('--static', type=Path, required=True)
    parser.add_argument('--storage', type=Path, required=True)
    parser.add_argument('--evidence', type=Path, action='append', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--selectors', type=Path)
    args = parser.parse_args()
    run(args.source, args.static, args.storage, args.evidence, args.output, args.selectors)
