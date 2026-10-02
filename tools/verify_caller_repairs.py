"""Fail-closed acceptance for every confirmed caller repair and field boundary."""
import argparse
import json
from pathlib import Path

from tools.audit_caller_cases import run as first_cases
from tools.audit_caller_followup import run as followup_cases, definitions
from tools.audit_dungeon_screens import save_json
from tools.rom import ROOT, digest, require
from tools.verify_location_banner import fresh_fixture


def run(source, output, fixture_path=None):
    rom = (source/'torneko-2-english.gba').read_bytes()
    build = json.loads((source/'build.json').read_text())
    require(digest(rom) == build['output_sha256'], 'Caller acceptance ROM/ledger mismatch')
    family = build['caller_repairs']
    expected = {b['call'] for b in family['bindings']}
    require(len(expected) == 55, 'Caller repair acceptance cohort differs')
    if fixture_path is None:
        fresh_fixture(rom, output/'fresh-fixture')
        fixture_path = output/'fresh-fixture/ready'
    # These two remain discovery leads; their probes never reached the target
    # caller. Excluding them here does not convert them into passing cases.
    excluded = {'monster-arrow-landing', 'disarmed-item-landing'}
    selected = {d['name'] for d in definitions()}-excluded
    reports, covered, formats = [], set(), set()
    for profile in (None, 'maximum-width', 'maximum-bytes', 'coloured'):
        folder = output/(profile or 'native-fields')
        first = first_cases(source, fixture_path, folder/'first',
                            ROOT/'build/caller-audit/followup-owners.txt', profile)
        followup = followup_cases(source, fixture_path, folder/'followup', selected, profile)
        cases = first['cases']+followup['cases']
        failed = [c['case'] for c in cases if not c['english_output']]
        require(not failed, 'Caller regression: '+', '.join(failed))
        observed = {b['call'] for c in cases for b in c['binding_checks']}
        require(expected <= observed, 'A repaired caller was not reached')
        field_rows = {r['id'] for r in family['entries'] if r['fields']}
        formatted = {f['id'] for c in cases for f in c['format_checks']}
        require(field_rows <= formatted, 'A repaired format lacks native boundary evidence')
        require(all(c['battery_unchanged'] and c['binding_checks_complete'] for c in cases),
                'Caller checks incomplete or battery changed')
        covered |= observed & expected
        formats |= formatted
        reports.append({'profile': profile, 'cases': len(cases), 'passed': True,
                        'reached_repaired_callers': sorted(observed & expected),
                        'exact_format_checks': sum(len(c['format_checks']) for c in cases),
                        'glyphs': sum(len(c['glyphs']) for c in cases),
                        'first_report': str((folder/'first/report.json').relative_to(ROOT)),
                        'followup_report': str((folder/'followup/report.json').relative_to(ROOT))})
    report = {'passed': True, 'rom_sha256': digest(rom), 'profiles': reports,
              'repaired_callers': sorted(covered), 'formatted_resources': sorted(formats),
              'excluded_discovery_probes': sorted(excluded),
              'tool_sha256': digest(Path(__file__).read_bytes()),
              'scope': '55 exact caller bindings, complete observed screens, native formatting and copy '
                       'bytes, original buffers/guards/ABI, ordinary menu inputs after recorded setup. '
                       'Three boundary profiles explicitly replace fields only, using existing scratch '
                       'and restoring it at formatter return; they are rendering preflights. '
                       'No text-source pointer or reader is substituted. Does not close remaining discovery.'}
    save_json(output/'report.json', report)
    print('Caller repairs:', len(covered), 'bindings;', sum(r['cases'] for r in reports), 'cases passed')
    return report


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path, default=ROOT/'build/english')
    p.add_argument('--output', type=Path, default=ROOT/'build/caller-repair/acceptance')
    p.add_argument('--fixture', type=Path)
    args = p.parse_args()
    run(args.source.resolve(), args.output.resolve(), args.fixture.resolve() if args.fixture else None)
