"""Complete native two-core trades, repeat/cancel, and battery-only cold loads.

The initial storage records and entry through a bank call are controlled. After
that entry every menu, serial transfer, item conversion and save is native.
"""
import argparse
from contextlib import ExitStack
import json
from pathlib import Path
import struct

import mgba.log

from tools.bakery_playtest import service_ready
from tools.emulator import Session, Debugger, ffi
from tools.link_emulator import LinkPair, compile_bridge
from tools.rom import ROOT, default_rom, digest, load_base, require
from tools.screen_text_audit import ScreenTextAudit


def stored_items(game):
    m = game.core.memory
    rows = []
    for slot in range(250):
        at = 0x0200F008+12*slot
        if m.u32[at] & 0x80000000:
            rows.append(dict(slot=slot, id=m.u8[0x020013D0+m.u8[at+8]],
                             raw_hex=bytes(m[at:at+12]).hex()))
    return rows


def audit_ok(audit):
    report = audit.report()
    require(not any(report[k] for k in ('unclassified_glyphs', 'unreadable_streams',
                                      'layout_violations')), 'Unfiltered link text audit failed')
    return report


def run(source, output):
    mgba.log.silence()
    rom = (source/'torneko-2-english.gba').read_bytes()
    ledger = json.loads((source/'build.json').read_text())
    require(digest(rom) == ledger['output_sha256'], 'Stale link ROM')
    original_hash = digest(load_base())
    source_save = default_rom().with_suffix('.sav')
    source_save_hash = digest(source_save.read_bytes())
    library, bridge = compile_bridge(output/'native-bridge')
    fixture = service_ready(rom, output)
    results = []
    batteries = []
    with ExitStack() as stack:
        games, records = [], []
        for peer in range(2):
            g = stack.enter_context(Session(rom, output/f'peer-{peer}'))
            g.restore(fixture)
            games.append(g)
            m = g.core.memory
            mapping = bytes(m[0x020013D0:0x020014D0])
            stored = bytearray(3000)
            struct.pack_into('<I', stored, 0, 0xC8000000)
            stored[5], stored[8] = 1, mapping.index(peer+1)
            audit = ScreenTextAudit(g)
            rec = dict(peer=peer, controls=[], events=[], initial=None, returns=[],
                       images=[], states=[], original_battery_sha256=digest(fixture.battery))
            rec['storage_capacity_before'] = m.u16[0x02002C2A]
            records.append(rec)
            identity = 0x02003BAC+20*(peer+1)
            for address, raw in ((0x0200F008, stored),
                                 (identity, struct.pack('<I', m.u32[identity] | 0x40000000))):
                rec['controls'].append(dict(address=address,
                    before_hex=bytes(m[address:address+len(raw)]).hex(), after_hex=raw.hex()))
                for offset, value in enumerate(raw):
                    m.u8[address+offset] = value
            rec['initial_items'] = stored_items(g)
            rec['carried_before'] = bytes(m[0x0200DF28:0x0200E888]).hex()
            hero = m.u32[0x02001624]
            rec['gold_before'] = m.u32[hero+0x60]

            def callback(e, g=g, rec=rec, audit=audit):
                address, registers = e['address'], e['registers']
                if address == 0x0801DFAC and rec['initial'] is None:
                    rec['initial'] = e | dict(guard=bytes(g.core.memory[
                        registers[13]:registers[13]+32]).hex())
                    rec['controls'].append(dict(event=e, pc_after=0x08057C54,
                        reason='Enter the complete original link owner from the bank call.'))
                    require(g.core._core.writeRegister(g.core._core, b'pc',
                        ffi.new('uint32_t*', 0x08057C54)), 'Link owner entry failed')
                elif address in (0x08058110, 0x08057C1C, 0x08057D46, 0x08015348):
                    rec['events'].append(e)
                elif address == 0x08057DAC:
                    old = rec['initial']['registers']
                    require(registers[4:12] == old[4:12] and registers[13] == old[13]
                            and registers[0] == old[14] and bytes(g.core.memory[
                                old[13]:old[13]+32]).hex() == rec['initial']['guard'],
                            'Link owner caller ABI or stack guard differs')
                    rec['returns'].append(e)
                audit.callback(e)

            d = stack.enter_context(Debugger(g, callback, max_events=180000))
            for address in set(audit.ADDRESSES) | {0x0801DFAC, 0x08058110, 0x08057C1C,
                                                 0x08057D46, 0x08057DAC, 0x08015348}:
                d.breakpoint(address)
            rec['audit_object'] = audit
        pair = stack.enter_context(LinkPair(games, library))

        def capture(label):
            for g, rec in zip(games, records):
                g.capture(label)
                rec['images'].append(dict(file=label+'.png', sha256=digest(
                    (g.output/(label+'.png')).read_bytes())))
                rec['states'].append(dict(label=label, frame=g.core.frame_counter,
                    stored=stored_items(g), capacity=g.core.memory.u16[0x02002C2A],
                    battery_sha256=digest(g.snapshot().battery)))
            print('Link exchange:', label, flush=True)

        # Instruction modal -> item list -> Trade/Info -> item confirmation ->
        # cable confirmation. These are actual A inputs on both cores.
        for label in ('instructions', 'picker', 'actions', 'item-confirm', 'connect-confirm'):
            pair.press('A', wait=120)
            capture(label)
        for round_index in range(2):
            pair.press('A', wait=360)
            capture(f'traded-{round_index}')
            for peer, (g, rec) in enumerate(zip(games, records)):
                expected = 2-peer if round_index == 0 else peer+1
                require([r['id'] for r in stored_items(g)] == [expected]
                        and g.core.memory.u16[0x02002C2A] == rec['storage_capacity_before'],
                        'Native exchange lost/duplicated an item or changed capacity')
                require('Traded for' in '\n'.join(r.get('text', '') for r in
                        rec['audit_object'].report()['reads']), 'Native completion message absent')
                battery = g.snapshot().battery
                require(battery != fixture.battery, 'Native trade did not persist a save')
                (g.output/f'trade-{round_index}.sav').write_bytes(battery)
                if round_index == 0:
                    batteries.append(battery)
            pair.press('A', wait=120)
            capture(f'repeat-{round_index}')
            if round_index == 0:
                for label in ('repeat-instructions', 'repeat-picker', 'repeat-actions',
                              'repeat-item-confirm', 'repeat-connect-confirm'):
                    pair.press('A', wait=120)
                    capture(label)
        pair.press('B', wait=180)
        capture('cancel-repeat')
        wire = pair.report()
        require(wire['started'] > 0 and wire['started'] == wire['master_finished'] ==
                wire['slave_finished'] and wire['wire_capture_complete'], 'Incomplete native serial exchange')
        for g, rec in zip(games, records):
            require(len(rec['returns']) == 1, 'Link owner did not return exactly once')
            require(not any(e['address'] == 0x08057C1C for e in rec['events']), 'Native link error path reached')
            transfers = [e for e in rec['events'] if e['address'] == 0x08057D46]
            require(len(transfers) == 2 and all(e['registers'][0] == 0 for e in transfers),
                    'Both complete protocol calls must succeed')
            m = g.core.memory
            require(bytes(m[0x0200DF28:0x0200E888]).hex() == rec['carried_before'] and
                    m.u32[m.u32[0x02001624]+0x60] == rec['gold_before'], 'Trade changed carried items or gold')
            rec['audit'] = audit_ok(rec.pop('audit_object'))
            rec['caller_abi_guard_preserved'] = True
            results.append(rec)

    cold = []
    for peer, battery in enumerate(batteries):
        with Session(rom, output/f'cold-{peer}', initial_save=battery) as g:
            g.frames(600)
            audit = ScreenTextAudit(g)
            with Debugger(g, audit.callback, max_events=50000) as d:
                for address in audit.ADDRESSES:
                    d.breakpoint(address)
                g.press('START', wait=180)
                g.press('A', wait=300)
                require([r['id'] for r in stored_items(g)] == [2-peer] and
                        g.core.memory.u16[0x02002C2A] == results[peer]['storage_capacity_before'],
                        'Received item/capacity did not survive battery-only cold load')
                g.capture('cold-loaded')
            cold.append(dict(peer=peer, save_sha256=digest(battery), inputs=g.inputs,
                             stored=stored_items(g), audit=audit_ok(audit)))
    require(digest(load_base()) == original_hash and digest(source_save.read_bytes()) == source_save_hash,
            'Source ROM or save changed during link research')
    report = dict(passed=True, rom_sha256=digest(rom), source_rom_sha256=original_hash,
        source_save_sha256=source_save_hash, bridge=bridge, peers=results, wire=wire,
        cold_loads=cold, scope='Controlled stored Oaken club/Gold sword and bank-call entry. '
        'Complete native owner, menus, two real bidirectional serial exchanges, receive formatting, '
        'automatic saves, repeat and B cancellation, caller ABI/guard, carried/gold preservation and '
        'battery-only cold loads of both first-trade results. Unfiltered text/glyph/layout audit. '
        'Natural title entry, asymmetric/disconnect/error cases and other item classes are separate.')
    (output/'report.json').write_text(json.dumps(report, indent=2)+'\n')
    print('Two-core native link exchange passed:', wire['master_finished'], 'serial transfers')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=ROOT/'build/english')
    parser.add_argument('--output', type=Path, default=ROOT/'build/link-exchange')
    args = parser.parse_args()
    run(args.source, args.output)
