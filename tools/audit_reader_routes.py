"""Account for direct Floor/empty-inventory calls and the status-expiry reader.

Also retain unfiltered shared-table literal candidates for further analysis.
Those candidates are not a count of broken paths: queue hooks, formatted text,
dynamic selectors, dead code and literal data require different dispositions.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import struct

from tools.rom import ROOT, digest, load_base, require
from tools.status_expiry_text import SLOTS, LITERAL

BASE = 0x08000000
TABLE, END = 0x08140D68, 0x081417A0
MODAL = 0x08017068
# Calls and source selectors checked in Ghidra from owners08016C78/080171E0.
ROUTES = [
    (0x08016F28, 'trap-or-stairs-refusal', 0x17154, [0xC8, 0x3C8, 0x3E4, 0x408]),
    (0x08016F56, 'item-or-floor-refusal', 0x17154, [0xC8, 0x3C8, 0x3E4, 0x408]),
    (0x08016FAA, 'empty-floor', 0x16FB0, [0x30]),
    (0x08017224, 'empty-inventory', 0x17238, [0x34]),
]


def direct_calls(rom, target):
    calls = []
    for offset in range(0, len(rom)-3, 2):
        first, second = struct.unpack_from('<HH', rom, offset)
        if first & 0xF800 != 0xF000 or second & 0xF800 != 0xF800:
            continue
        displacement = ((first & 2047) << 12) | ((second & 2047) << 1)
        if displacement & (1 << 22):
            displacement -= 1 << 23
        if BASE + offset + 4 + displacement == target:
            calls.append(BASE + offset)
    return calls


def audit(rom, build):
    original = load_base()
    require(digest(rom) == build['output_sha256'], 'Reader audit ROM/ledger mismatch')
    expected = sorted(r[0] for r in ROUTES)
    original_calls, compiled_calls = direct_calls(original, MODAL), direct_calls(rom, MODAL)
    require(original_calls == expected and compiled_calls == expected,
            'Unaccounted modal call pattern; disassemble and classify before acceptance')
    entries = {r['table_offset']: r for r in build['floor_notices']['entries']}
    routes = []
    for call, name, literal, slots in ROUTES:
        table = struct.unpack_from('<I', rom, literal)[0]
        selectors = []
        for slot in slots:
            source = struct.unpack_from('<I', original, TABLE-BASE+slot)[0]
            actual = struct.unpack_from('<I', rom, table-BASE+slot)[0]
            row = entries.get(slot)
            matched = row is not None and actual == row['offset']+BASE
            if matched:
                raw = bytes.fromhex(row['encoded_hex'])
                matched = rom[actual-BASE:actual-BASE+len(raw)] == raw and row['width'] <= 168
            selectors.append({'slot': slot, 'original_source': source, 'compiled_source': actual,
                              'english': row['english'] if row else None, 'binding_verified': matched})
        routes.append({'call': call, 'role': name, 'literal': literal, 'selectors': selectors,
                       'passed': all(s['binding_verified'] for s in selectors)})
    expiry_table = struct.unpack_from('<I', rom, LITERAL)[0]
    expiry_rows = {r['table_offset']: r for r in build.get('status_expiry', {}).get('entries', [])}
    expiry_bindings = []
    for slot in sorted(SLOTS):
        actual = struct.unpack_from('<I', rom, expiry_table-BASE+slot)[0]
        row = expiry_rows.get(slot)
        matched = row is not None and actual == row['offset']+BASE
        if matched:
            raw = bytes.fromhex(row['encoded_hex'])
            matched = (rom[actual-BASE:actual-BASE+len(raw)] == raw and
                       row['maximum_bytes'] <= 256 and max(row['maximum_line_widths']) <= 216)
        expiry_bindings.append({'slot': slot, 'compiled_source': actual,
                                'english': row['english'] if row else None, 'binding_verified': matched})
    siblings_preserved = all(rom[expiry_table-BASE+s:expiry_table-BASE+s+4] ==
                             original[TABLE-BASE+s:TABLE-BASE+s+4]
                             for s in range(0, END-TABLE, 4) if s not in SLOTS)
    expiry_passed = siblings_preserved and all(r['binding_verified'] for r in expiry_bindings)
    # Same provisional native-code scan interval as the earlier lead tools.
    # Every matching literal is retained irrespective of source review status.
    # LDR-shaped data and computed/indirect loads remain explicit limitations.
    patches = {p['start']: p for p in build['patches']}
    candidates = []
    for offset in range(0, 0x5E000, 2):
        opcode = struct.unpack_from('<H', original, offset)[0]
        if opcode & 0xF800 != 0x4800:
            continue
        literal = ((offset+4) & ~3) + (opcode & 255)*4
        value = struct.unpack_from('<I', original, literal)[0]
        if not TABLE <= value < END:
            continue
        current = struct.unpack_from('<I', rom, literal)[0]
        patch = patches.get(literal)
        candidates.append({'load': BASE+offset, 'literal': literal, 'original_value': value,
                           'compiled_value': current, 'patch_owner': patch['owner'] if patch else None,
                           'instruction_changed': rom[offset:offset+2] != original[offset:offset+2],
                           'disposition': 'changed_literal_needs_route_binding' if current != value
                                          else 'original_literal_needs_consumer_classification'})
    return {'rom_sha256': digest(rom), 'source_sha256': digest(original),
            'modal_routes_passed': all(r['passed'] for r in routes),
            'status_expiry_passed': expiry_passed,
            'status_expiry': {'load': 0x080096C6, 'format_call': 0x080096EC,
                             'literal': LITERAL, 'table': expiry_table, 'selectors': expiry_bindings,
                             'other_647_selectors_preserved': siblings_preserved},
            'modal_direct_calls': compiled_calls, 'modal_routes': routes,
            'shared_table_literal_candidates': candidates,
            'candidate_counts': dict(Counter(r['disposition'] for r in candidates)),
            'global_path_count_known': False,
            'scope': 'Four direct modal call sites exhaust the matching Thumb BL patterns in the '
                     'source and compiled images and have Ghidra-confirmed callers. Six selector '
                     'bindings are checked, including the fallback. The computed timer reader has '
                     'seven bound English formats and 647 preserved sibling entries. Dynamic/indirect callers and '
                     'unrelated readers are not proven absent. The unfiltered literal list is a '
                     'triage inventory, not a failure count or a whole-game coverage result.'}


def run(source, output, allow_findings=False):
    report = audit((source/'torneko-2-english.gba').read_bytes(),
                   json.loads((source/'build.json').read_text()))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2)+'\n')
    print('Modal routes:', len(report['modal_routes']),
          'passed:', sum(r['passed'] for r in report['modal_routes']))
    print('Shared-table literal candidates (not defects):', report['candidate_counts'])
    print('Status expiry bindings:', report['status_expiry_passed'])
    require(allow_findings or report['modal_routes_passed'] and report['status_expiry_passed'],
            'Untranslated modal/status-expiry reader binding')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=ROOT/'build/english')
    parser.add_argument('--output', type=Path, default=ROOT/'build/reader-audit/routes.json')
    parser.add_argument('--allow-findings', action='store_true')
    args = parser.parse_args()
    run(args.source, args.output, args.allow_findings)
