"""NPC-bank loader, actual side/front contacts, service calls and script returns."""
import argparse
import json
from pathlib import Path
import struct

import mgba.log

from tools.bakery_playtest import service_ready
from tools.emulator import Session, Debugger, ffi
from tools.lz77 import decompress
from tools.rom import ROOT, digest, require
from tools.screen_text_audit import ScreenTextAudit
from tools.verify_link_exchange import audit_ok


def run(source, output):
    mgba.log.silence()
    rom = (source/'torneko-2-english.gba').read_bytes()
    build = json.loads((source/'build.json').read_text())
    require(digest(rom) == build['output_sha256'], 'Stale NPC repair ROM')
    resource = build['npc_shop_scripts']
    decoded, _ = decompress(rom, resource['allocation'])
    fixture = service_ready(rom, output)
    cases = []
    for node, approach in ((27,'side'), (27,'front'), (26,'front'), (26,'visible-selector')):
        label = f'map-{node}-{approach}'
        print('NPC shop route:', label, flush=True)
        with Session(rom, output/label) as g:
            g.restore(fixture)
            m = g.core.memory
            controls, events, selections, ends, images = [], [], [], [], []
            phase = 'setup'
            audit = ScreenTextAudit(g)
            loaded = []
            expected_root = 0x575 if node == 26 else 0x5CE

            def callback(e):
                nonlocal phase
                a, r = e['address'], e['registers']
                if a == 0x0801DFAC and not controls:
                    controls.append(dict(pc_after=0x08049F9C, event=e,
                        reason='Enter complete town loop for controlled bank/map access.'))
                    require(g.core._core.writeRegister(g.core._core, b'pc',
                        ffi.new('uint32_t*', 0x08049F9C)), 'Town entry failed')
                elif a == 0x0804D6F8:
                    controls.append(dict(register=0, before=r[0], after=2,
                                         reason='Select original story bank 2.'))
                    g.core.cpu.gprs[0] = 2
                elif a == 0x0804A2A0:
                    controls.append(dict(address=0x0200FED9, before=m.u8[0x0200FED9], after=node,
                                         reason='Select target room before native initialization.'))
                    m.u8[0x0200FED9] = node
                    expected = bytearray(decoded)
                    for offset in range(0,20,4):
                        struct.pack_into('<I', expected, offset,
                            struct.unpack_from('<I', expected, offset)[0]+0x020129AC)
                    require(bytes(m[0x020129AC:0x020129AC+len(expected)]) == expected,
                            'Native decompression/header fixups differ')
                    loaded.append(dict(frame=e['frame'], decoded_ram_sha256=digest(expected)))
                elif a == 0x0804B33C and phase == 'service':
                    if approach == 'visible-selector':
                        require(r[0] == 6, 'Remi front contact changed')
                        controls.append(dict(register=0, before=r[0], after=5, event=e,
                            reason='Exercise visible Remi actor; ordinary contact through the counter is unproven.'))
                        g.core.cpu.gprs[0] = 5
                    else:
                        require(r[0] == (5 if approach == 'side' else 6), 'Unexpected native contacted actor')
                    events.append(e)
                elif a == 0x0804B3A6 and phase == 'service':
                    pointer = m.u32[0x02010138]
                    require(pointer == 0x020129AC+expected_root, 'NPC selected wrong service script')
                    selections.append(e | dict(pointer=pointer))
                elif a == 0x0804EFB4 and phase == 'service':
                    pointer = m.u32[0x02010138]
                    if pointer == 0x020129AC+expected_root+(2 if node == 26 else 3):
                        ends.append(e | dict(pointer=pointer))
                audit.callback(e)

            def capture(name):
                g.capture(name)
                images.append(dict(file=name+'.png', sha256=digest((g.output/(name+'.png')).read_bytes())))

            with Debugger(g, callback, max_events=160000) as d:
                for a in set(audit.ADDRESSES) | {0x0801DFAC,0x0804D6F8,0x0804A2A0,
                                               0x0804B33C,0x0804B3A6,0x0804EFB4}:
                    d.breakpoint(a)
                g.press('A', hold=1, wait=300)
                g.press('A', hold=1, wait=300)
                require(len(loaded) == 1 and m.u8[0x0200FED8] == node, 'Native room initialization incomplete')
                capture('room')
                if node == 27 and approach == 'front':
                    g.press('RIGHT', hold=24, wait=20)
                    g.press('UP', hold=110, wait=20)
                else:
                    g.press('UP', hold=110, wait=20)
                    if approach == 'side':
                        g.press('DOWN', hold=8, wait=20)
                        g.press('RIGHT', hold=8, wait=20)
                capture('approach')
                before_position = [m.u32[a] for a in (0x0200FF0C,0x0200FF10)]
                before_items = bytes(m[0x0200DF28:0x0200E888])
                before_gold = m.u32[m.u32[0x02001624]+0x60]
                phase = 'service'
                for cycle in range(3):
                    g.press('A', hold=1, wait=120)
                    capture(f'opened-{cycle}')
                    require(len(selections) == cycle+1, 'Native shop did not open/reopen')
                    for _ in range(16):
                        if len(ends) > cycle:
                            break
                        g.press('B', hold=1, wait=120)
                    require(len(ends) == cycle+1, 'Service did not return through native END')
                    capture(f'closed-{cycle}')
                    require([m.u32[a] for a in (0x0200FF0C,0x0200FF10)] == before_position,
                            'Service changed player position')
                require(bytes(m[0x0200DF28:0x0200E888]) == before_items and
                        m.u32[m.u32[0x02001624]+0x60] == before_gold and
                        g.snapshot().battery == fixture.battery, 'Cancelled service changed items, gold or battery')
            text = audit_ok(audit)
            require(any(('Remi:' if node == 26 else 'Blacksmith:') in r.get('text','') for r in text['reads']),
                    'Expected English shopkeeper text absent')
            cases.append(dict(case=label, controls=controls, inputs=g.inputs, loader=loaded,
                contacts=events, selections=selections, native_script_ends=ends,
                position=before_position, images=images, audit=text,
                items_gold_battery_preserved=True))
            (g.output/'report.json').write_text(json.dumps(cases[-1], indent=2)+'\n')
    report = dict(passed=True, rom_sha256=digest(rom), cases=cases,
        scope='Controlled bank/map access through full native town initialization. '
        'Exact native NPC resource decompression and header fixups. Blacksmith side and front contacts '
        'and Remi front contact use ordinary movement/A. Visible Remi actor uses one documented '
        'actor-argument override. Three native service opens/cancellations/END returns per case; '
        'unfiltered text/glyph/layout checks and unchanged items/gold/battery. Ordinary story eligibility excluded.')
    (output/'report.json').write_text(json.dumps(report, indent=2)+'\n')
    print('NPC shop routes:', len(cases), 'passed')
    return report


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path, default=ROOT/'build/english')
    p.add_argument('--output', type=Path, default=ROOT/'build/npc-shop-routes')
    args = p.parse_args()
    run(args.source, args.output)
