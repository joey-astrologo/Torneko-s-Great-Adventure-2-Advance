"""Ordinary green-book entry, native trading and return from a quest-earned save.

Both peers cold-load the same naturally earned save. They deposit different
naturally carried items using buttons. No ROM/RAM/register/availability/item
overrides are used. This checks one story bank and one pair of item classes.
"""
import argparse
from contextlib import ExitStack
import json
from pathlib import Path

import mgba.log

from tools.emulator import Session, Debugger
from tools.holy_flame_playtest import items
from tools.link_emulator import LinkPair, compile_bridge
from tools.rom import ROOT, default_rom, digest, load_base, require
from tools.screen_text_audit import ScreenTextAudit
from tools.town_playtest import position
from tools.verify_link_exchange import audit_ok, stored_items
from tools.verify_storage import SAVE


def carried_records(game):
    m = game.core.memory
    return [dict(slot=i, raw_hex=bytes(m[at:at+120]).hex()) for i in range(20)
            if m.u32[at := 0x0200DF28+120*i] & 0x80000000]


def run(source, output):
    mgba.log.silence()
    rom = (source/'torneko-2-english.gba').read_bytes()
    build = json.loads((source/'build.json').read_text())
    require(digest(rom) == build['output_sha256'], 'Natural link ROM differs')
    original = digest(load_base())
    source_save = default_rom().with_suffix('.sav')
    source_save_hash = digest(source_save.read_bytes())
    battery = SAVE.read_bytes()
    library, bridge = compile_bridge(output/'native-bridge')
    records, saved = [], []
    with ExitStack() as stack:
        games = []
        for peer in range(2):
            g = stack.enter_context(Session(rom, output/f'peer-{peer}', initial_save=battery))
            games.append(g)
            audit = ScreenTextAudit(g)
            rec = dict(peer=peer, events=[], entries=[], returns=[], images=[], controls=[])
            records.append(rec)

            def callback(e, g=g, audit=audit, rec=rec):
                a, r = e['address'], e['registers']
                if a == 0x08057C54:
                    require(r[14] == 0x0804A18F, 'Link entered from another caller')
                    rec['entries'].append(e | dict(guard=bytes(g.core.memory[r[13]:r[13]+32]).hex()))
                elif a == 0x08057DAC:
                    old = rec['entries'][-1]
                    registers = old['registers']
                    require(r[4:12] == registers[4:12] and r[13] == registers[13]
                            and r[0] == registers[14]
                            and bytes(g.core.memory[r[13]:r[13]+32]).hex() == old['guard'],
                            'Natural link caller ABI/guard changed')
                    rec['returns'].append(e)
                elif a in (0x08050AA8, 0x08050580, 0x08058110, 0x08057D46,
                           0x08057C1C, 0x08015348):
                    rec['events'].append(e)
                audit.callback(e)

            d = stack.enter_context(Debugger(g, callback, max_events=220000))
            for address in set(audit.ADDRESSES) | {0x08057C54, 0x08057DAC, 0x08050AA8,
                    0x08050580, 0x08058110, 0x08057D46, 0x08057C1C, 0x08015348}:
                d.breakpoint(address)
            rec['audit_object'] = audit
            g.frames(600); g.press('START', wait=180); g.press('A', wait=300)
            require(position(g) == (288,224) and not stored_items(g)
                    and [i for _,i,_ in items(g)] == [204,51], 'Earned storage fixture differs')

            def capture(label, g=g, rec=rec):
                g.capture(label)
                rec['images'].append(dict(file=label+'.png', sha256=digest(
                    (g.output/(label+'.png')).read_bytes())))

            # Green book: demonstrate the actual empty-storage refusal first.
            g.press('RIGHT', hold=16, wait=60); g.press('UP', hold=3, wait=60)
            g.press('A', wait=120); capture('record-menu')
            g.press('DOWN', wait=30); g.press('DOWN', wait=30); g.press('A', wait=120)
            capture('empty-storehouse')
            require(not rec['entries'] and not stored_items(g), 'Empty gate admitted a trade')
            g.press('B', wait=120); g.press('B', wait=120)

            # Return to the blue book, deposit bread on peer 0 / staff on peer 1.
            g.press('LEFT', hold=16, wait=60); g.press('UP', hold=3, wait=60)
            require(position(g) == (288,224), 'Blue-book approach differs')
            g.press('A', wait=120); g.press('A', wait=120)
            if peer:
                g.press('DOWN', wait=30)
            g.press('R', wait=60); g.press('A', wait=120); capture('deposited')
            g.press('A', wait=120); g.press('B', wait=120)
            expected = [204,51][peer]
            require([r['id'] for r in stored_items(g)] == [expected], 'Ordinary deposit differs')
            rec['deposited'] = stored_items(g)
            rec['carried_before'] = bytes(g.core.memory[0x0200DF28:0x0200E888]).hex()
            rec['carried_live_before'] = carried_records(g)
            rec['capacity_before'] = g.core.memory.u16[0x02002C2A]
            rec['gold_before'] = g.core.memory.u32[g.core.memory.u32[0x02001624]+0x60]
            g.press('RIGHT', hold=16, wait=60); g.press('UP', hold=3, wait=60)
            g.press('A', wait=120); g.press('DOWN', wait=30); g.press('DOWN', wait=30)
            g.press('A', wait=240); capture('native-link-entry')
            require(len(rec['entries']) == 1, 'Green book did not enter original link owner')
            rec['ordinary_inputs'] = list(g.inputs)

        pair = stack.enter_context(LinkPair(games, library))
        for label in ('picker','actions','item-confirm','connect-confirm','traded','repeat'):
            pair.press('A', wait=360 if label == 'traded' else 120)
            for g, rec in zip(games, records):
                g.capture(label)
                rec['images'].append(dict(file=label+'.png', sha256=digest(
                    (g.output/(label+'.png')).read_bytes())))
        pair.press('B', wait=360)
        wire = pair.report()
        require(wire['started'] == wire['master_finished'] == wire['slave_finished'] > 0
                and wire['wire_capture_complete'], 'Native exchange incomplete')
        for peer, (g,rec) in enumerate(zip(games,records)):
            require(len(rec['returns']) == 1, 'Natural link owner did not return once')
            require(not any(e['address'] == 0x08057C1C for e in rec['events']), 'Link error reached')
            protocol = [e for e in rec['events'] if e['address'] == 0x08057D46]
            require(len(protocol) == 1 and protocol[0]['registers'][0] == 0, 'Protocol did not succeed')
            require([r['id'] for r in stored_items(g)] == [[51,204][peer]], 'Wrong received item')
            require(stored_items(g)[0]['raw_hex'] == records[1-peer]['deposited'][0]['raw_hex'],
                    'Trade changed the naturally acquired item properties')
            m = g.core.memory
            require(bytes(m[0x0200DF28:0x0200E888]).hex() == rec['carried_before']
                    and m.u16[0x02002C2A] == rec['capacity_before']
                    and m.u32[m.u32[0x02001624]+0x60] == rec['gold_before'],
                    'Trade changed carried items, capacity or gold')
            require(m.u8[0x0200FED8] == 21, 'Link did not return to home')
            g.capture('returned-to-town')
            saved.append(g.snapshot().battery)
            require(saved[-1] != battery, 'Ordinary exchange did not save')
            (g.output/'traded.sav').write_bytes(saved[-1])
            rec['received'] = stored_items(g)
            rec['audit'] = audit_ok(rec.pop('audit_object'))
            text = '\n'.join(r.get('text','') for r in rec['audit']['reads'])
            require(all(s in text for s in ('Trade items','Put items in the storehouse','Traded for')),
                    'Natural gate/completion messages missing')

    cold = []
    for peer, battery in enumerate(saved):
        with Session(rom, output/f'cold-{peer}', initial_save=battery) as g:
            g.frames(600); g.press('START', wait=180); g.press('A', wait=300)
            require([r['id'] for r in stored_items(g)] == [[51,204][peer]],
                    'Naturally traded item did not survive cold load')
            require(stored_items(g)[0]['raw_hex'] == records[peer]['received'][0]['raw_hex']
                    and carried_records(g) == records[peer]['carried_live_before']
                    and g.core.memory.u16[0x02002C2A] == records[peer]['capacity_before'],
                    'Cold load changed received properties, carried items or capacity')
            g.capture('received-after-cold-load')
            cold.append(dict(peer=peer, save_sha256=digest(battery), inputs=g.inputs,
                             stored=stored_items(g), position=position(g)))
    require(digest(load_base()) == original and digest(source_save.read_bytes()) == source_save_hash,
            'Source ROM/save changed')
    report = dict(passed=True, rom_sha256=digest(rom), source_rom_sha256=original,
        source_save_sha256=source_save_hash, fixture_save_sha256=digest(SAVE.read_bytes()),
        tool_sha256=digest(Path(__file__).read_bytes()), bridge=bridge, peers=records, wire=wire,
        cold_loads=cold, scope=__doc__, ordinary_inputs_only=True, source_files_unchanged=True)
    (output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Natural link:', len(records), 'green-book entries;', wire['started'], 'serial transfers')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=ROOT/'build/english')
    parser.add_argument('--output', type=Path, default=ROOT/'build/link-entry')
    args = parser.parse_args()
    run(args.source, args.output)
