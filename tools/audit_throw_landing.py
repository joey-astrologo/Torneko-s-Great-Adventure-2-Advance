"""Observe the actual Throw miss/landing branch after controlled state setup.

The ordinary inventory Throw command owns the complete handler. An existing
monster is placed in its trajectory and the native RNG result is set to the
allowed miss outcome. Text pointers, readers, and program counters are untouched.
"""
import argparse
import json
from pathlib import Path
import struct

import mgba.log
from tools.audit_dungeon_screens import AuditedSession
from tools.emulator import Debugger
from tools.name_entry_playtest import ACTORS, MAP
from tools.rom import ROOT, digest, require
from tools.screen_text_audit import ScreenTextAudit
from tools.verify_service_ui import materialize
from tools import verify_player_status_prototype as status


def run(source, output):
    mgba.log.silence()
    rom = (source/'torneko-2-english.gba').read_bytes()
    build = json.loads((source/'build.json').read_text())
    require(digest(rom) == build['output_sha256'], 'Throw audit ROM differs')
    previous = status.OUT
    try:
        status.OUT = output
        fixture = status.ready(rom, build)
    finally:
        status.OUT = previous
    row = next(r for r in build['projectiles']['entries'] if r['table_offset'] == 0x1D4)
    with AuditedSession(rom, output/'native-miss') as game:
        game.restore(fixture)
        game.images = []
        game.audit = audit = ScreenTextAudit(game)
        m = game.core.memory
        writes, starts, returns, formats, random, pending = [], [], [], [], [], {}

        def write(at, data, why):
            writes.append(dict(address=at, before=bytes(m[at:at+len(data)]).hex(),
                               after=data.hex(), reason=why))
            for i,b in enumerate(data):
                m.u8[at+i] = b

        player = m.u32[ACTORS]
        monster = next(m.u32[ACTORS+4*i] for i in range(1,56)
                       if m.u32[m.u32[ACTORS+4*i]+8] & 0x80000000 and
                       m.u16[m.u32[ACTORS+4*i]+0x84] > 0)
        x,y = m.u16[player+0x66], m.u16[player+0x68]
        for off,size,value in ((0x66,2,x+1),(0x68,2,y),(0x10,4,(x+1)*32),(0x14,4,y*32)):
            write(monster+off,value.to_bytes(size,'little'),'Existing actor in the Throw trajectory')
        write(player+0x42,b'\x02','Face right toward the existing actor')
        for tx in range(x,min(x+4,56)):
            at = MAP+(tx*32+y)*28+20
            write(at,struct.pack('<I',m.u32[at]|0x4000),'Walkable trajectory and landing tiles')
        item = bytearray(120)
        struct.pack_into('<I',item,0,0xC8000000)
        item[4:6] = b'\x01\x01'
        item[8] = bytes(m[0x020013D0:0x020014D0]).index(203)
        write(0x0200DF28,item,'Controlled ordinary Bread, no curse/equipped/inscription flags')
        at = 0x02003BAC+203*20
        write(at,struct.pack('<I',m.u32[at]|0x40000000),'Known Bread definition')

        def callback(event):
            a,r = event['address'],event['registers']
            audit.callback(event)
            if a == 0x080259FC:
                starts.append(event | dict(guard=bytes(m[r[13]:r[13]+32]).hex()))
            if a == 0x08026018:
                random.append(dict(address=a,before=r[0],after=99,reason='Allowed native RNG miss outcome'))
                game.core.cpu.gprs[0] = 99
            if a == 0x08000FB8 and r[14] == 0x080261C1:
                require(r[1] == row['offset']+0x08000000 and r[0] == r[13]+0x10,
                        'Throw landing did not select the private English format')
                expected = materialize(bytes.fromhex(row['encoded_hex']),[r[2]],m)
                pending.update(address=r[0],expected=expected,guard=bytes(m[r[0]+256:r[0]+272]),registers=r)
            if a == 0x080261C0 and pending:
                p,expected = pending['address'],pending['expected']
                require(bytes(m[p:p+len(expected)]) == expected and
                        bytes(m[p+256:p+272]) == pending['guard'] and
                        r[4:12] == pending['registers'][4:12] and r[13] == pending['registers'][13],
                        'Throw landing output, buffer guard or formatter ABI differs')
                formats.append(dict(source=row['offset']+0x08000000,raw_hex=expected.hex(),guard_abi_match=True))
                pending.clear()
            if a == 0x080263EC and starts:
                old = starts[0]['registers']
                require(r[4:12] == old[4:12] and r[13] == old[13] and r[0] == old[14] and
                        bytes(m[r[13]:r[13]+32]).hex() == starts[0]['guard'], 'Throw full handler ABI differs')
                returns.append(event)

        with Debugger(game,callback,max_events=200000) as debug:
            for a in set(audit.ADDRESSES)|(set((0x080259FC,0x08026018,0x080261C0,0x080263EC))):
                debug.breakpoint(a)
            game.press('B',hold=8,wait=30)
            game.press('A',wait=30)
            game.press('A',wait=30)
            actions = []
            for i in range(7):
                value = m.u16[0x0200CDD0+2*i]
                if not value: break
                actions.append(value)
            require(9 in actions,'Native Throw action absent')
            for _ in range(actions.index(9)): game.press('DOWN',wait=20)
            game.press('A',wait=0)
            for _ in range(900):
                game.frames(1)
                if returns: break
            game.frames(60)
            game.capture('landing')
        report = dict(rom_sha256=digest(rom),fixture_state_sha256=digest(fixture.state),
            tool_sha256=digest(Path(__file__).read_bytes()),inputs=game.inputs,
            controlled_overrides=writes,random_controls=random,formats=formats,
            handler_entries=len(starts),handler_returns=len(returns),audit=audit.report(),scope=__doc__)
        report['passed'] = (len(starts)==len(returns)==len(formats)==1 and bool(random) and not pending and
            not any((audit.unclassified,audit.unreadable,audit.layout_violations)) and
            game.snapshot().battery == fixture.battery)
        (output/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
        require(report['passed'],'Native Throw landing audit failed: '+str(output/'report.json'))
    print('Native Throw miss/landing: passed',flush=True)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,default=ROOT/'build/english')
    parser.add_argument('--output',type=Path,default=ROOT/'build/english/throw-landing-validation')
    args = parser.parse_args()
    run(args.source,args.output)
