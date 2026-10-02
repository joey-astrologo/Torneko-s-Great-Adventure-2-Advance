"""Continue caller discovery with branch-specific native probes, never text substitution."""
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
from tools.name_entry_playtest import MAP
from tools.audit_text_callers import CONSUMERS


def definitions():
    cases = []
    def add(name, entry, call, **kw):
        cases.append(dict(name=name, entry=entry, expected_call=call, **kw))
    add('putrid-strength-resisted', 0x33428, 0x33474, flags=0x40000000)
    add('strength-partial-recovery', 0x33A14, 0x33A9A, fields=[(0x76, 2, 7)])
    add('eyedrop-blindness-recovery', 0x337AC, 0x33802, fields=[(0x98, 1, 20)])
    add('map-blindness-recovery', 0x34834, 0x348D2, fields=[(0x98, 1, 20)])
    for who in ('player', 'monster'):
        add('sleep-resisted-'+who, 0x37848, 0x37880, target=who, fields=[(0xA4, 1, 20)])
    add('room-paralysis', 0x33DE8, 0x33E2A, adjacent=True)
    add('nearby-healing', 0x2C454, 0x2C5AE, args=['player', 5], fields=[(0x84, 2, 10)])
    add('summon-ally', 0x2C670, 0x2C692, target='monster')
    for entry, call in [(0x2C5F8, 0x2C65C), (0x2C670, 0x2C6F0), (0x2C704, 0x2C75A)]:
        add('summon-blocked-'+f'{entry:x}', entry, call, target='monster', block_neighbors=True)
    for outcome, call in [(0, 0x3336E), (2, 0x333A8), (5, 0x333FE)]:
        add('rotten-bread-effect-'+str(outcome), 0x332C8, call,
            fields=[(0x88, 2, 2)], random_result=outcome)
    add('rotten-bread-resisted', 0x332C8, 0x33332, flags=0x40000000, random_result=0)
    add('already-kaclang-target', 0x3E278, 0x3E2F8, target='monster',
        fields=[(0x9B, 1, 20)], args=['player', 'monster', 0])
    add('strength-halving-hit', 0x38550, 0x385F2, target='monster',
        fields=[(0x84, 2, 999), (0x86, 2, 999), (0x76, 2, 8)], args=['monster', 'player', 0])
    add('full-thief-pot', 0x35BD8, 0x35C32, item=(161, 0))
    add('storage-pot-marked-take-menu', None, 0x18002, item=(154, 3),
        contents=[203, 181], menu_action=42, marked=True)
    add('invisible-hocus-pocus-scroll', None, 0x258CA, item=(135, 1), menu_action=14)
    add('hocus-pocus-level-loss', 0x356E8, 0x35AEA, fields=[(0x88, 2, 2)],
        random_result=4, random_pc=0x080356F8)
    add('attack-strength-halving', 0xBCBC, 0xCC3C, target='monster',
        fields=[(0x84, 2, 999), (0x86, 2, 999), (0x76, 2, 8)],
        args=['player', 'monster', 1, 0], stack_args=[0, 1])
    add('landing-no-room', 0x38644, 0x387A4, item=(203, 1), no_floor=True,
        args=['x', 'y', 'item', 0], stack_args=[0, 0, 1, 1])
    add('landing-item-capacity', 0x38644, 0x3875A, item=(203, 1), full_floor_items=True,
        args=['x', 'y', 'item', 0], stack_args=[0, 0, 1, 1])
    add('pot-spill-item-capacity', 0x38834, 0x38C4A, item=(154, 3), contents=[203],
        full_floor_items=True, args=['x', 'y', 'item', 'x'], stack_args=['y'])
    add('scatter-item-capacity', 0x38D24, 0x39008, full_floor_items=True)
    add('thief-pot-stuck-item', 0x35BD8, 0x35DA8, item=(161, 3), stuck_ahead=True)
    add('summon-ally-after-grab', 0x2C258, 0x2C2EC, target='monster', flags=0x40,
        random_result=0, random_pc=0x0802C268)
    add('monster-arrow-landing', 0x2AB84, 0x2B0FC, target='monster',
        fields=[(0x91, 1, 10), (0x42, 1, 2)], nearby_shooter=True)
    add('disarmed-item-landing', 0x2C9A0, 0x2CD7E, target='monster',
        fields=[(0x42, 1, 2)], item=(30, 1), equipped=True, open_projectile_line=True)
    add('reflected-staff-hit', 0x263F8, 0x26706, item=(50, 2),
        reflector=True, args=['action'])
    add('golden-item-floor-empty', 0x36BF8, 0x36C22, dismiss=True)
    add('discover-adjacent-trap', None, 0x241FA, attack_trap=True)
    add('level-loss-at-level-one-control', 0x33824, 0x33864)
    add('rotten-bread-level-one-control', 0x332C8, 0x33410, random_result=5)
    add('hocus-pocus-level-one-control', 0x356E8, 0x35AFC, random_result=4, random_pc=0x080356F8)
    return cases


def run(source, fixture_path, output, select=None, field_profile=None):
    mgba.log.silence()
    rom = (source/'torneko-2-english.gba').read_bytes()
    build = json.loads((source/'build.json').read_text())
    require(digest(rom) == build['output_sha256'], 'ROM/ledger mismatch')
    fixture = Snapshot.load(fixture_path)
    require(fixture.rom_sha256 == digest(rom), 'Fixture ROM mismatch')
    protected = {str(p): digest(p.read_bytes()) for p in (default_rom(), default_rom().with_suffix('.sav'))}
    disassembly = ROOT/'build/caller-audit/remaining-owners.txt'
    owners = {}
    more_disassembly = ROOT/'build/caller-audit/modal-owners.txt'
    original_disassembly = ROOT/'build/caller-audit/followup-owners.txt'
    if not disassembly.exists():
        disassembly.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(['bash', 'tools/ghidra.sh', 'functions', str(disassembly),
                        *[hex(0x08000000+e) for e in sorted({d['entry'] for d in definitions() if d['entry']})]],
                       cwd=ROOT, check=True)
    if not more_disassembly.exists():
        subprocess.run(['bash', 'tools/ghidra.sh', 'functions', str(more_disassembly), '0x08036BF8'],
                       cwd=ROOT, check=True)
    for part in (disassembly.read_text()+more_disassembly.read_text()+original_disassembly.read_text()).split('\nFUNCTION ')[1:]:
        code = part.split('PROVISIONAL PSEUDOCODE')[0]
        owners[int(code.splitlines()[0], 16)] = dict((int(a, 16), int(r)) for a,r in
            re.findall(r'^(\w{8})  bx r([01])$', code, re.M))
    results = []
    for spec in definitions():
        name = spec['name']
        if select and name not in select:
            continue
        entry = 0x08000000+spec['entry'] if spec['entry'] else None
        exits = owners[entry] if entry else {}
        require(not entry or exits, 'No disassembled native exit')
        with AuditedSession(rom, output/name) as g:
            g.restore(fixture)
            m = g.core.memory
            g.audit = audit = ScreenTextAudit(g)
            bindings = CallerBindingChecks(g, build, field_profile)
            g.images = []
            player = m.u32[0x02001624]
            monster = next(m.u32[0x02001624+4*i] for i in range(1,56)
                           if m.u32[m.u32[0x02001624+4*i]+8] & 0x80000000 and
                           m.u16[m.u32[0x02001624+4*i]+0x84] > 0)
            actor = monster if spec.get('target') == 'monster' else player
            writes, entered, returns, calls, random_controls, stack_backup, flow = [], [], [], [], [], [], []
            def write(at, size, value, why):
                raw = value.to_bytes(size, 'little') if isinstance(value, int) else value
                require(len(raw) == size, 'Write length mismatch')
                writes.append(dict(address=at, before=bytes(m[at:at+size]).hex(), after=raw.hex(), reason=why))
                for i,b in enumerate(raw):
                    m.u8[at+i] = b
            def reg(event, index, value, why):
                writes.append(dict(pc=event['address'], register=index, before=event['registers'][index],
                                   after=value, reason=why))
                if index == 15:
                    require(g.core._core.writeRegister(g.core._core, b'pc', ffi.new('uint32_t*', value)), 'PC redirect failed')
                else:
                    g.core.cpu.gprs[index] = value
            for off,size,value in spec.get('fields', []):
                write(actor+off, size, value, 'Disassembled actor-state branch precondition')
            if spec.get('flags'):
                write(actor+8, 4, m.u32[actor+8] | spec['flags'], 'Disassembled actor resistance bit')
            if spec.get('adjacent'):
                for off, delta in [(0x66, 1), (0x68, 0)]:
                    write(monster+off, 2, m.u16[player+off]+delta, 'Controlled nearby monster for room-effect selection')
            if spec.get('block_neighbors'):
                x,y = m.u16[actor+0x66],m.u16[actor+0x68]
                for dx,dy in [(a,b) for a in (-1,0,1) for b in (-1,0,1) if a or b]:
                    at = MAP+((x+dx)*32+y+dy)*28+20
                    write(at, 4, m.u32[at] & ~0x4000, 'Controlled nonwalkable neighbors; native summoner must fail')
            if 'item' in spec:
                ident, capacity = spec['item']
                def item(ident, amount):
                    raw = bytearray(120)
                    struct.pack_into('<I', raw, 0, 0xC8000000)
                    raw[4], raw[5] = amount, 1
                    raw[8] = bytes(m[0x020013D0:0x020014D0]).index(ident)
                    at = 0x02003BAC+ident*20
                    write(at, 4, m.u32[at] | 0x40000000, 'Known item definition')
                    return raw
                raw = item(ident, capacity)
                if spec.get('equipped'):
                    struct.pack_into('<I', raw, 0, 0xC8800000)
                for i, child in enumerate(spec.get('contents', [])):
                    raw[24+i*12:36+i*12] = item(child, 1)[:12]
                write(0x0200DF28, 120, raw, 'Controlled known item, no inscription flag')
                write(player+0x43, 1, 0, 'Native selected inventory index')
            if spec.get('nearby_shooter') or spec.get('reflector'):
                for off,delta in [(0x66, 1),(0x68, 0)]:
                    write(monster+off, 2, m.u16[player+off]+delta, 'Controlled adjacent projectile actor')
                x,y = m.u16[monster+0x66],m.u16[monster+0x68]
                write(monster+0x10, 4, x*32, 'Matching actor render coordinate')
                write(monster+0x14, 4, y*32, 'Matching actor render coordinate')
                at = MAP+(x*32+y)*28+20
                write(at, 4, m.u32[at]|0x4000, 'Walkable projectile tile')
            if spec.get('nearby_shooter') or spec.get('open_projectile_line'):
                x,y = m.u16[actor+0x66],m.u16[actor+0x68]
                if spec.get('open_projectile_line'):
                    x,y = m.u16[player+0x66],m.u16[player+0x68]
                for tx in range(x, min(56,x+13)):
                    at = MAP+(tx*32+y)*28+20
                    write(at, 4, m.u32[at]|0x4000, 'Controlled open projectile trajectory')
            if spec.get('reflector'):
                write(monster+0x91, 1, 0x47, 'Native species tested by staff reflection branch')
                write(player+0x42, 1, 2, 'Face the controlled adjacent reflector')
            if spec.get('attack_trap'):
                write(player+0x42, 1, 2, 'Face the adjacent trap')
                x,y = m.u16[player+0x66]+1,m.u16[player+0x68]
                cell = MAP+(x*32+y)*28
                require(m.u16[cell+10] == 0xFFFF, 'Expected empty trap slot')
                write(cell+10, 2, 0, 'Controlled undiscovered native trap selector')
                write(cell+20, 4, m.u32[cell+20]|0x4000, 'Controlled walkable tile for trap search')
            if spec.get('stuck_ahead'):
                # Native direction table08140B18: selector2 is (+1,0).
                dx, dy = struct.unpack_from('<ii', rom, 0x140B18+8*2)
                require((dx,dy) == (1,0), 'Native direction table differs')
                write(player+0x42, 1, 2, 'Controlled facing right for floor item')
                x,y = m.u16[player+0x66]+dx,m.u16[player+0x68]+dy
                cell = MAP+(x*32+y)*28
                require(m.u32[cell+16] == 0, 'Controlled floor cell is already occupied')
                raw = item(203, 1)
                struct.pack_into('<I', raw, 0, 0xD8000000)
                write(0x0202EDA8, 120, raw, 'Controlled existing floor-item pool record with stuck flag')
                write(cell+16, 4, 0x0202EDA8, 'Controlled map association to floor item')
                write(cell+20, 4, m.u32[cell+20]|0x4000, 'Controlled walkable floor in front of actor')
            if spec.get('no_floor'):
                for x in range(56):
                    for y in range(32):
                        at = MAP+(x*32+y)*28+20
                        write(at, 4, m.u32[at] & ~0x4000, 'Controlled absence of item landing tiles')
            def argument(value):
                return {'player':player, 'monster':monster, 'actor':actor,
                        'item':0x0200DF28, 'action':player+0x40,
                        'x':m.u16[player+0x66], 'y':m.u16[player+0x68]}.get(value,value)
            def callback(event):
                a,r = event['address'],event['registers']
                audit.callback(event)
                bindings.callback(event)
                if a in (0x0802ABA6,0x0802B0A6,0x0802B0DE,0x0802CD3C,0x0802CD58,0x08038644):
                    flow.append(event)
                if entry and a == 0x08008F4C and not entered:
                    entered.append(event)
                    for i, value in enumerate(spec.get('args', ['actor'])):
                        reg(event, i, argument(value), 'Controlled invocation of verified native handler')
                    for i,value in enumerate(spec.get('stack_args', [])):
                        at = r[13]+4*i
                        stack_backup.append((at, bytes(m[at:at+4])))
                        write(at, 4, argument(value), 'Controlled native stack argument; restored at handler return')
                    if spec.get('full_floor_items'):
                        for i in range(128):
                            at = 0x0202EDA8+120*i
                            write(at, 4, m.u32[at]|0x80000000, 'Controlled occupied native floor-item pool slot')
                    reg(event, 15, entry, 'Controlled invocation of verified native handler')
                # Select an allowed random branch after the native RNG executes;
                # do not replace the handler, its format or any reader.
                if a == spec.get('random_pc', 0x080332DC) and 'random_result' in spec and entered:
                    reg(event, 0, spec['random_result'], 'Controlled allowed random-effect outcome')
                    random_controls.append(event)
                if a in CONSUMERS:
                    calls.append(dict(consumer=a, call=(r[14]&~1)-4, arguments=r[:4], frame=event['frame']))
                if a in exits and entered and r[exits[a]] == entered[0]['registers'][14]:
                    before = entered[0]['registers']
                    require(r[4:12] == before[4:12] and r[13] == before[13], 'Handler return ABI differs')
                    for at,raw in stack_backup:
                        write(at, 4, raw, 'Restore caller stack after controlled native arguments')
                    returns.append(dict(pc=a, frame=event['frame'], abi_preserved=True))
            error = None
            with Debugger(g, callback, max_events=160000) as debug:
                for a in set(audit.ADDRESSES) | bindings.addresses | set(CONSUMERS) | {0x08008F4C,
                                               0x0802ABA6,0x0802B0A6,0x0802B0DE,0x0802CD3C,0x0802CD58,0x08038644,
                                               spec.get('random_pc', 0x080332DC)} | set(exits):
                    debug.breakpoint(a)
                try:
                    if entry:
                        g.press('A', wait=0)
                        for _ in range(700):
                            if returns and audit.glyphs and g.core.frame_counter >= audit.glyphs[-1]['frame']+4:
                                break
                            if spec.get('dismiss') and _ % 60 == 59:
                                g.capture('panel')
                                g.press('B', hold=1, wait=0)
                            g.frames(1)
                        require(len(entered) == len(returns) == 1, 'Handler did not return exactly once')
                    else:
                        if spec.get('attack_trap'):
                            g.press('A', hold=1, wait=60)
                        else:
                            g.press('B', hold=8, wait=30)
                            g.press('A', wait=30)
                            g.press('A', wait=30)
                            actions = [m.u16[0x0200CDD0+i*2]&127 for i in range(8)]
                            require(spec['menu_action'] in actions, 'Requested item action absent')
                            for _ in range(actions.index(spec['menu_action'])):
                                g.press('DOWN', wait=15)
                            g.press('A', wait=60)
                            if spec.get('marked'):
                                g.press('R', wait=20)
                                g.press('DOWN', wait=20)
                                g.press('R', wait=20)
                                g.press('A', wait=60)
                        g.capture('panel')
                        if spec.get('marked') and not field_profile:
                            # Cancel to the parent item list, then reopen View
                            # and the marked-content action using normal inputs.
                            for cycle in range(2):
                                g.press('B', wait=30)
                                g.capture(f'cancel-{cycle}')
                                g.press('A', wait=30)
                                actions = [m.u16[0x0200CDD0+i*2]&127 for i in range(8)]
                                require(42 in actions, 'View missing after marked-menu cancellation')
                                for _ in range(actions.index(42)):
                                    g.press('DOWN', wait=15)
                                g.press('A', wait=40)
                                g.press('R', wait=20)
                                g.press('DOWN', wait=20)
                                g.press('R', wait=20)
                                g.press('A', wait=40)
                                g.capture(f'reopen-{cycle}')
                            require(sum(c['call'] == 0x08018002 for c in calls) == 3,
                                    'Marked Take menu did not reopen three times')
                            g.press('A', wait=90)
                            mapping = bytes(m[0x020013D0:0x020014D0])
                            ids = [mapping[m.u8[0x0200DF28+120*i+8]] for i in range(20)
                                   if m.u32[0x0200DF28+120*i] & 0x80000000]
                            require(203 in ids and 181 in ids, 'Take did not transfer both marked contents')
                            require(not any(m.u32[0x0200DF28+24+12*i] & 0x80000000 for i in range(7)),
                                    'Taken contents remain in Storage pot')
                            g.capture('taken')
                    require(any(c['call'] == 0x08000000+spec['expected_call'] for c in calls), 'Expected caller not reached')
                    require(audit.glyphs, 'No output was drawn')
                    if 'random_result' in spec:
                        require(len(random_controls) == 1, 'RNG branch control not applied exactly once')
                    if not entry:
                        g.press('B', wait=30)
                except Exception as exc:
                    error = str(exc) + (': '+str(exc.__cause__) if exc.__cause__ else '')
            g.capture('result')
            result = dict(case=name, entry=entry, spec=spec, rom_sha256=digest(rom),
                          fixture_state_sha256=digest(fixture.state), route_error=error, overrides=writes,
                          inputs=g.inputs, images=g.images, calls=calls, returns=returns,
                          flow_probes=flow,
                          battery_unchanged=g.snapshot().battery == fixture.battery, **audit.report(), **bindings.report())
            result['confirmed_japanese_output'] = error is None and bool(audit.unclassified)
            result['english_output'] = error is None and result['binding_checks_complete'] and result['battery_unchanged'] and not (audit.unclassified or audit.unreadable or audit.layout_violations)
            save_json(g.output/'report.json', result)
            results.append(result)
            print(name, 'JAPANESE' if result['confirmed_japanese_output'] else 'ENGLISH' if result['english_output'] else 'INCOMPLETE', error, flush=True)
    require(all(digest(Path(p).read_bytes()) == h for p,h in protected.items()), 'Supplied source changed')
    report = dict(rom_sha256=digest(rom), cases=results, source_hashes=protected, original_files_unchanged=True,
                  tool_sha256=digest(Path(__file__).read_bytes()), disassembly_sha256=digest(disassembly.read_bytes()),
                  modal_disassembly_sha256=digest(more_disassembly.read_bytes()),
                  original_disassembly_sha256=digest(original_disassembly.read_bytes()),
                  scope='Branch-specific handler controls, including explicitly selected allowed RNG results. '
                  'No text pointers or readers replaced. Actual inputs and all overrides retained. '
                  'Failed routes are not confirmations; ordinary acquisition/encounters remain separate.')
    save_json(output/'report.json', report)
    return report


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path, default=ROOT/'build/english')
    p.add_argument('--fixture', type=Path, default=ROOT/'build/status-expiry/native/fresh-fixture/ready')
    p.add_argument('--output', type=Path, default=ROOT/'build/caller-audit/followup')
    p.add_argument('--case', action='append')
    p.add_argument('--field-profile', choices=['maximum-width', 'maximum-bytes', 'coloured'])
    args = p.parse_args()
    run(args.source, args.fixture, args.output, args.case, args.field_profile)
