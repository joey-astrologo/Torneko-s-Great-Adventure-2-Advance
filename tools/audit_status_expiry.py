"""Verify all recovered timer branches and the repaired expiry reader natively.

Timers are injected at ordinary turn-handler entry. Native code decrements,
selects, formats and displays the messages; no message pointers are overridden.
The default is a failing regression gate; --allow-findings retains old-ROM evidence.
"""
import argparse
import json
from pathlib import Path

import mgba.log

from tools.audit_dungeon_screens import AuditedSession, save_json
from tools.emulator import Debugger, Snapshot
from tools.rom import ROOT, default_rom, digest, require
from tools.screen_text_audit import ScreenTextAudit
from tools.dialogue_checks import player_layout_cases
from tools.name_entry import HERO
from tools.status_expiry_text import SLOTS
from tools.verify_inventory_action_prototype import ActionCheck
from tools.verify_location_banner import fresh_fixture
from tools.verify_service_ui import materialize

# Actor byte and shared-table index, recovered from CPU08008F4C's branches.
TIMERS = [(0xBF, 0x25C), (0xBE, 0x25B), (0x9A, 0xF0), (0xB9, 0x1DA),
          (0x95, 0x5F), (0x96, 0x60), (0xAB, 0x23F), (0x97, 0x61),
          (0xB0, 0x21A), (0xB1, 0x220), (0xA3, 0xB9), (0x99, 0xB9),
          (0x98, 0x62), (0x9C, 0xF8), (0xAA, 0x149), (0x9E, 0xFD),
          (0xB3, 0x276), (0x9B, 0x1D6), (0x94, 0x7E), (0x93, 0x7E)]


def run(source, fixture_path, output, allow_findings=False, baseline_only=False):
    mgba.log.silence()
    rom = (source/'torneko-2-english.gba').read_bytes()
    build = json.loads((source/'build.json').read_text())
    require(digest(rom) == build['output_sha256'], 'Expiry ROM/ledger mismatch')
    protected = {str(p): digest(p.read_bytes()) for p in
                 (default_rom(), default_rom().with_suffix('.sav'))}
    fixture = Snapshot.load(fixture_path) if fixture_path else fresh_fixture(rom, output/'fresh-fixture')
    require(fixture.rom_sha256 == digest(rom), 'Expiry fixture belongs to another ROM')
    rows = {r['table_offset']//4: r for r in build.get('status_expiry', {}).get('entries', [])}
    repaired = [(t, s) for t, s in TIMERS if s*4 in SLOTS]
    cases = [(f'timer-{t:02x}-selector-{s:03x}', [(t, s)], None, None) for t, s in TIMERS]
    widest_form = max(build['monsters']['entries'], key=lambda r: r['width_px'])
    if not baseline_only:
        for label, payload in player_layout_cases()[1:]:
            cases += [(f'timer-{t:02x}-{label}', [(t, s)], payload, None) for t, s in repaired]
        cases += [(f'timer-{t:02x}-transformed', [(t, s)], None, widest_form) for t, s in repaired]
        cases += [(f'simultaneous-{label}', repaired, payload, None)
                  for label, payload in player_layout_cases()]
    results = []
    for name, timers, player, form in cases:
        with AuditedSession(rom, output/name) as g:
            g.restore(fixture)
            g.audit = audit = ScreenTextAudit(g)
            g.images = []
            m = g.core.memory
            writes, formats, checks, entries, returns = [], [], [], [], []
            pending = None
            error = None

            def write(address, raw, reason, frame=None):
                writes.append({'frame': frame, 'address': address,
                               'before': bytes(m[address:address+len(raw)]).hex(),
                               'after': raw.hex(), 'reason': reason})
                for i, value in enumerate(raw):
                    m.u8[address+i] = value

            if player is not None:
                write(HERO, player.ljust(16, b'\0'), 'Controlled maximum saved name')
            expected_name = bytes(m[HERO:HERO+16])

            def callback(event):
                nonlocal pending
                r, a, m = event['registers'], event['address'], g.core.memory
                audit.callback(event)
                if a == 0x08008F4C and not entries:
                    entries.append(event)
                    for timer, _ in timers:
                        write(m.u32[0x02001624]+timer, b'\1',
                              'Controlled one-turn timer at normal turn-handler entry', event['frame'])
                    if form:
                        write(m.u32[0x02001624]+0xBF, b'\2', 'Transformation remains active through expiry', event['frame'])
                        write(0x02003BAA, form['id'].to_bytes(2, 'little'), 'Widest native transformed identity', event['frame'])
                if a == 0x080096EC:
                    selector = m.u32[r[8]-4]
                    record = {'frame': event['frame'], 'source': r[1], 'selector': selector,
                              'name_pointer': r[2], 'destination': r[0],
                              'queue_flag': m.u32[r[13]+0x350], **audit.stream(r[1], event)}
                    formats.append(record)
                    if selector in rows:
                        row = rows[selector]
                        require(pending is None and (not checks or checks[-1].complete and checks[-1].returned),
                                'Previous expiry output unfinished')
                        require(r[1] == row['offset']+0x08000000 and r[0] == r[13]+0x50,
                                'Expiry reader source or stack destination differs')
                        expected_pointer = form['offset']+0x08000000 if form else HERO
                        require(r[2] == expected_pointer, 'Native expiry identity differs')
                        expected = materialize(bytes.fromhex(row['encoded_hex']), [r[2]], m)
                        require(len(expected) <= row['maximum_bytes'] <= 256, 'Expiry expansion exceeds capacity')
                        guard = bytes(m[r[0]+256:r[0]+272])
                        pending = (r[0], expected, guard, r[4:12], r[13], record)
                        checks.append(ActionCheck(g, expected[:-1], 0x080096F9, 256, guard))
                if a == 0x080096F0 and pending:
                    dest, expected, guard, regs, sp, record = pending
                    require(bytes(m[dest:dest+len(expected)]) == expected and
                            bytes(m[dest+256:dest+272]) == guard and r[4:12] == regs and r[13] == sp,
                            'Expiry formatter bytes, guard or ABI differs')
                    record.update(output_hex=expected.hex(), output_bytes=len(expected),
                                  capacity=256, guard_and_abi_preserved=True)
                    pending = None
                if a == 0x0801588C and r[14] == 0x080096F9:
                    require(r[1] == formats[-1]['queue_flag'], 'Expiry queue flag differs')
                if checks and not (checks[-1].complete and checks[-1].returned):
                    checks[-1].callback(event)
                if a == 0x08009830 and entries:
                    original = entries[0]['registers']
                    require(r[4:12] == original[4:12] and r[13] == original[13] and r[1] == original[14],
                            'Turn-handler return ABI differs')
                    returns.append({'frame': event['frame'], 'abi_preserved': True})

            with Debugger(g, callback, max_events=90000) as debug:
                for a in set(audit.ADDRESSES) | {0x08008F4C, 0x080096EC, 0x080096F0,
                                               0x080096F8, 0x08009830, 0x08001C68}:
                    debug.breakpoint(a)
                try:
                    g.press('A', wait=600 if len(timers) > 1 else 240)
                    expected_selectors = [s for _, s in timers]
                    reached = sorted(f['selector'] for f in formats) == sorted(expected_selectors)
                    if timers[0][0] == 0xBF:
                        # This branch queues slot9F8 directly. The earlier25C
                        # scratch selector is cleared before the common loop.
                        reached = any(q['caller'] == 0x08008FB1 for q in audit.final_queues)
                    require(len(entries) == len(returns) == 1 and reached, 'Expected expiry route/return not reached')
                    require(pending is None and all(c.complete and c.returned for c in checks), 'Expiry rendering incomplete')
                    require(len(checks) == sum(s in rows for _, s in timers), 'Missing exact expiry check')
                    require(all(m.u8[m.u32[0x02001624]+t] == 0 for t, _ in timers), 'Native timer did not expire')
                    require(bytes(m[HERO:HERO+16]) == expected_name, 'Expiry changed saved name')
                except Exception as exc:
                    error = str(exc)
            g.capture('result')
            report = {'case': name, 'timers': timers, 'transformed_identity': form['english'] if form else None,
                      'rom_sha256': digest(rom), 'route_error': error,
                      'actual_route': 'direct-transformation-notice' if timers[0][0] == 0xBF else 'expiry-selector-loop',
                      'fixture_state_sha256': digest(fixture.state), 'overrides': writes,
                      'inputs': g.inputs, 'images': g.images, 'expiry_formats': formats,
                      'handler_returns': returns, 'exact_queues': [c.queued for c in checks],
                      'exact_glyph_draws': sum(len(c.draws) for c in checks),
                      'battery_unchanged': g.snapshot().battery == fixture.battery, **audit.report()}
            report['english_output'] = (not error and not audit.unclassified and not audit.unreadable and
                                        not audit.layout_violations and report['battery_unchanged'])
            save_json(g.output/'report.json', report)
            results.append(report)
            print(name, 'PASS' if report['english_output'] else 'FINDING', error, flush=True)
    require(all(digest(Path(p).read_bytes()) == sha for p, sha in protected.items()), 'Original files changed')
    report = {'rom_sha256': digest(rom), 'cases': results,
              'passed': all(r['english_output'] for r in results),
              'source_hashes': protected, 'original_files_unchanged': True,
              'tool_sha256': digest(Path(__file__).read_bytes()),
              'scope': 'All 20 timer branches identified in the disassembled expiry loop; controlled '
                       'one-turn values, normal action and native handler. Repaired outputs also check '
                       'exact formatting, 256-byte guards, formatter/queue/handler ABI and glyph pixels; '
                       'maximum saved names, widest transformed identity and simultaneous expiries. '
                       'Not ordinary status acquisition or whole-game coverage.'}
    save_json(output/'report.json', report)
    require(allow_findings or report['passed'], 'Status-expiry reader regression; see report.json')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=ROOT/'build/english')
    parser.add_argument('--fixture', type=Path)
    parser.add_argument('--output', type=Path, default=ROOT/'build/status-expiry/native')
    parser.add_argument('--allow-findings', action='store_true')
    parser.add_argument('--baseline-only', action='store_true')
    args = parser.parse_args()
    run(args.source, args.fixture, args.output, args.allow_findings, args.baseline_only)
