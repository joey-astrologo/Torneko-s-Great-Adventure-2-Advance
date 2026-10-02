"""Unfiltered native follow-up of callers flagged by audit_text_callers.

Diagnostic evidence, with explicit handler/argument/state controls. It does not
replace ordinary acquisition routes or turn static candidates into bug counts.
"""
import argparse
import json
from pathlib import Path
import re
import struct
import subprocess

import mgba.log

from tools.audit_dungeon_screens import AuditedSession, save_json
from tools.emulator import Debugger, Snapshot, ffi
from tools.rom import ROOT, default_rom, digest, require
from tools.screen_text_audit import ScreenTextAudit
from tools.caller_binding_checks import CallerBindingChecks

# Entry, semantic label, target actor choices, precondition field (offset,value).
# Entries and arguments checked in caller-audit/followup-owners.txt.
HANDLERS = [
    (0x33238, 'maximum-fullness', ['player'], None),
    (0x33428, 'weakening-effect', ['player'], None),
    (0x33824, 'level-reduction', ['player'], (0x88, 2)),
    (0x33A14, 'strength-recovery', ['player'], None),
    (0x37848, 'sleep-effect', ['player', 'monster'], None),
    (0x390B4, 'berserk-effect', ['player', 'monster'], None),
    (0x39124, 'delusion-effect', ['player', 'monster'], None),
    (0x39208, 'speed-effect', ['player', 'monster'], None),
    (0x39314, 'wakefulness-effect', ['player', 'monster'], None),
    (0x39420, 'blindness-recovery-effect', ['player', 'monster'], (0x98, 20)),
    (0x394F4, 'blindness-effect', ['player', 'monster'], None),
    (0x395B0, 'strength-increase-effect', ['player', 'monster'], None),
    (0x3962C, 'paralysis-effect', ['player', 'monster'], None),
    (0x39694, 'kaclang-effect', ['player', 'monster'], None),
    (0x39C80, 'fear-effect', ['player', 'monster'], None),
    (0x39D6C, 'paralysis-special-effect', ['player', 'monster'], None),
    (0x39F88, 'defence-reduction-effect', ['player', 'monster'], None),
    (0x39FE8, 'fear-alternate-effect', ['player', 'monster'], None),
    (0x40D44, 'kaclang-alternate-effect', ['player', 'monster'], None),
    (0x2866C, 'dancing-trap-disabled', ['unused'], None),
    (0x286B4, 'berserk-trap-disabled', ['unused'], None),
]


def run(source, fixture_path, output, disassembly, field_profile=None):
    mgba.log.silence()
    rom = (source/'torneko-2-english.gba').read_bytes()
    build = json.loads((source/'build.json').read_text())
    require(digest(rom) == build['output_sha256'], 'Caller probe ROM/ledger differs')
    fixture = Snapshot.load(fixture_path)
    require(fixture.rom_sha256 == digest(rom), 'Caller probe fixture belongs to another ROM')
    protected = {str(p): digest(p.read_bytes()) for p in (default_rom(), default_rom().with_suffix('.sav'))}
    if not disassembly.exists():
        disassembly.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(['bash', 'tools/ghidra.sh', 'functions', str(disassembly.resolve()),
                        *[hex(0x08000000+entry) for entry, _, _, _ in HANDLERS]], cwd=ROOT, check=True)
    owners = {}
    for part in disassembly.read_text().split('\nFUNCTION ')[1:]:
        code = part.split('PROVISIONAL PSEUDOCODE')[0]
        entry = int(code.splitlines()[0], 16)
        exits = [(int(a, 16), int(r)) for a, r in re.findall(r'^(\w{8})  bx r([01])$', code, re.M)]
        owners[entry] = exits
    results = []
    cases = [(entry, label+'-'+target, target, pre) for entry, label, targets, pre in HANDLERS for target in targets]
    cases += [(None, 'item-info-normal', 'menu', None), (None, 'item-info-recognition-blocked', 'menu', (0xAB, 100))]
    cases += [(None, 'peep-scroll-target-selector', 'selector', None)]
    cases += [(None, 'eat-giant-bread', 'eat-206', None),
              (None, 'eat-putrid-bread', 'eat-208', None),
              (None, 'drink-strength-seed', 'drink-181', None)]
    for offset, name, target, pre in cases:
        entry = 0x08000000+offset if offset is not None else None
        exits = dict(owners[entry]) if entry else {}
        require(not entry or exits, 'Unverified native handler exit')
        with AuditedSession(rom, output/name) as g:
            g.restore(fixture)
            m = g.core.memory
            g.audit = audit = ScreenTextAudit(g)
            bindings = CallerBindingChecks(g, build, field_profile)
            g.images = []
            writes, calls, entered, returns = [], [], [], []
            error = None
            actor = m.u32[0x02001624]
            if target == 'monster':
                actor = next(m.u32[0x02001624+4*i] for i in range(1, 56)
                             if 0x02000000 <= m.u32[0x02001624+4*i] < 0x0203FF00 and
                             m.u32[m.u32[0x02001624+4*i]+8] & 0x80000000 and
                             m.u16[m.u32[0x02001624+4*i]+0x84] > 0)
            def write(address, raw, reason):
                writes.append({'address': address, 'before': bytes(m[address:address+len(raw)]).hex(),
                               'after': raw.hex(), 'reason': reason})
                for i, value in enumerate(raw):
                    m.u8[address+i] = value
            def reg(event, index, value):
                writes.append({'pc': event['address'], 'register': index,
                               'before': event['registers'][index], 'after': value,
                               'reason': 'Controlled invocation of the disassembled native handler'})
                if index == 15:
                    require(g.core._core.writeRegister(g.core._core, b'pc', ffi.new('uint32_t*', value)),
                            'Caller probe redirect failed')
                else:
                    g.core.cpu.gprs[index] = value
            if pre:
                at, value = pre
                write(actor+at, value.to_bytes(2 if at == 0x88 else 1, 'little'), 'Controlled branch precondition')
            if target == 'selector' or target.startswith(('eat-', 'drink-')):
                # Retain the opening bread, then add the known test item.
                # Subsequent Read/Eat/Drink selections use ordinary buttons.
                write(0x0200DF28+120, bytes(m[0x0200DF28:0x0200DF28+120]), 'Retain opening bread in second slot')
                item = bytearray(120)
                struct.pack_into('<I', item, 0, 0xC8000000)
                item[4:6] = b'\1\1'
                ident = 117 if target == 'selector' else int(target.split('-')[1])
                item[8] = bytes(m[0x020013D0:0x020014D0]).index(ident)
                write(0x0200DF28, bytes(item), f'Controlled known item {ident}; no inscription flag')
                at = 0x02003BAC+ident*20
                write(at, struct.pack('<I', m.u32[at] | 0x40000000), 'Known item definition')
            def callback(event):
                a, r = event['address'], event['registers']
                audit.callback(event)
                bindings.callback(event)
                if entry and a == 0x08008F4C and not entered:
                    entered.append(event)
                    reg(event, 0, 0 if target == 'unused' else actor)
                    reg(event, 1, 1 if target == 'unused' else m.u32[0x02001624])
                    reg(event, 15, entry)
                if a in (0x08000FB8, 0x08015848, 0x0801588C, 0x08002298):
                    calls.append({'consumer': a, 'call': (r[14] & ~1)-4, 'arguments': r[:4], 'frame': event['frame']})
                if a in exits and entered and r[exits[a]] == entered[0]['registers'][14]:
                    before = entered[0]['registers']
                    require(r[4:12] == before[4:12] and r[13] == before[13], 'Controlled handler return ABI differs')
                    returns.append({'pc': a, 'frame': event['frame'], 'abi_preserved': True})
            with Debugger(g, callback, max_events=120000) as debug:
                for a in set(audit.ADDRESSES) | bindings.addresses | {0x08008F4C, 0x08015848, 0x08002298} | set(exits):
                    debug.breakpoint(a)
                try:
                    if entry:
                        g.press('A', wait=0)
                        for _ in range(500):
                            if returns and audit.glyphs and g.core.frame_counter >= audit.glyphs[-1]['frame']+4:
                                break
                            g.frames(1)
                        require(len(entered) == len(returns) == 1, 'Controlled native handler did not return')
                    else:
                        g.press('B', hold=8, wait=30)
                        g.press('A', wait=30)
                        g.press('A', wait=30)
                        actions = [m.u16[0x0200CDD0+i*2] & 127 for i in range(8)]
                        action = 12 if target == 'selector' else 11 if target.startswith('eat-') else 13 if target.startswith('drink-') else 40
                        require(action in actions, 'Requested menu action absent')
                        for _ in range(actions.index(action)):
                            g.press('DOWN', wait=15)
                        g.press('A', wait=60)
                        g.capture('panel')
                        if target == 'selector':
                            require(any(c['call'] == 0x0801768A for c in calls), 'Dungeon target selector not reached')
                        for variant, expected in [('eat-206', 0x080332AE), ('eat-208', 0x080334B8),
                                                  ('drink-181', 0x08033A5C)]:
                            if target == variant:
                                require(any(c['call'] == expected for c in calls), 'Native item-effect caller not reached')
                        if pre:
                            require(any(c['call'] == 0x08017A9C for c in calls), 'Blocked Info reader not reached')
                        if not field_profile and (target == 'selector' or pre):
                            expected_call = 0x0801768A if target == 'selector' else 0x08017A9C
                            for cycle in range(2):
                                g.press('B', wait=30)
                                g.capture(f'cancel-{cycle}')
                                if target == 'selector':
                                    g.press('A', wait=30)
                                g.press('A', wait=30)
                                actions = [m.u16[0x0200CDD0+i*2]&127 for i in range(8)]
                                require(action in actions, 'Item action missing after cancellation')
                                for _ in range(actions.index(action)):
                                    g.press('DOWN', wait=15)
                                g.press('A', wait=45)
                                g.capture(f'reopen-{cycle}')
                            require(sum(c['call'] == expected_call for c in calls) == 3,
                                    'Repaired menu did not reopen three times')
                        g.press('B', wait=30)
                    require(audit.glyphs, 'No native output observed')
                except Exception as exc:
                    error = str(exc) + (': '+str(exc.__cause__) if exc.__cause__ else '')
            g.capture('result')
            report = {'case': name, 'entry': entry, 'target': target, 'actor': actor,
                      'rom_sha256': digest(rom), 'fixture_state_sha256': digest(fixture.state),
                      'route_error': error, 'overrides': writes, 'inputs': g.inputs, 'images': g.images,
                      'calls': calls, 'returns': returns, 'battery_unchanged': g.snapshot().battery == fixture.battery,
                      **audit.report(), **bindings.report()}
            report['confirmed_japanese_output'] = error is None and bool(audit.unclassified)
            report['english_output'] = error is None and report['binding_checks_complete'] and report['battery_unchanged'] and not (audit.unclassified or audit.unreadable or audit.layout_violations)
            save_json(g.output/'report.json', report)
            results.append(report)
            print(name, 'JAPANESE' if report['confirmed_japanese_output'] else 'ENGLISH' if report['english_output'] else 'INCOMPLETE', error, flush=True)
    require(all(digest(Path(p).read_bytes()) == h for p, h in protected.items()), 'Source ROM/save changed')
    report = {'rom_sha256': digest(rom), 'cases': results, 'source_hashes': protected,
              'tool_sha256': digest(Path(__file__).read_bytes()), 'disassembly_sha256': digest(disassembly.read_bytes()),
              'original_files_unchanged': True,
              'scope': 'Diagnostic native follow-up. Info, Read, Eat and Drink use ordinary buttons after '
                       'explicit inventory/status setup. '
                       'Effect/trap cases redirect a normal action to disassembled native handlers and control '
                       'arguments/preconditions. Source pointers and formatters/renderers are never substituted. '
                       'Entire observed text is audited; incomplete routes are not counted as confirmations. '
                       'Does not establish ordinary acquisition, every caller or whole-game coverage.'}
    save_json(output/'report.json', report)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=ROOT/'build/english')
    parser.add_argument('--fixture', type=Path, default=ROOT/'build/status-expiry/native/fresh-fixture/ready')
    parser.add_argument('--output', type=Path, default=ROOT/'build/caller-audit/native')
    parser.add_argument('--disassembly', type=Path, default=ROOT/'build/caller-audit/followup-owners.txt')
    parser.add_argument('--field-profile', choices=['maximum-width', 'maximum-bytes', 'coloured'])
    args = parser.parse_args()
    run(args.source, args.fixture, args.output, args.disassembly, args.field_profile)
