"""Follow the conditional queue's sole direct producer through a complete turn.

Controlled current-tile bits select the ten-point terrain damage branch. The
queue-suppression byte is controlled at wrapper entry; native damage, formatting,
queue predicate and complete return run. This is not ordinary terrain acquisition.
"""
import argparse
import json
from pathlib import Path

import mgba.log
from tools.audit_dungeon_screens import AuditedSession
from tools.emulator import Debugger
from tools.name_entry_playtest import ACTORS, MAP
from tools.rom import ROOT, digest, require
from tools.screen_text_audit import ScreenTextAudit
from tools.verify_location_banner import fresh_fixture
from tools.verify_inventory_action_prototype import ActionCheck
from tools.verify_service_ui import materialize


def run(source, output):
    mgba.log.silence()
    rom = (source/'torneko-2-english.gba').read_bytes()
    build = json.loads((source/'build.json').read_text())
    require(digest(rom)==build['output_sha256'],'Terrain damage ROM differs')
    fixture = fresh_fixture(rom,output/'fixture')
    row = next(r for r in build['combat']['entries'] if r['id']=='combat.1c4')
    cases = []
    for suppressed in (0,1):
        with AuditedSession(rom,output/str(suppressed)) as g:
            g.restore(fixture);g.images=[];m=g.core.memory
            audit=ScreenTextAudit(g);g.audit=audit
            actor=m.u32[ACTORS];cell=MAP+(m.u16[actor+0x66]*32+m.u16[actor+0x68])*28+20
            writes,entries,returns,formats,wrappers,checks=[],[],[],[],[],[]
            pending=None
            inventory=bytes(m[0x0200DF28:0x0200E888])
            def write(at,raw,reason):
                writes.append(dict(address=at,before=bytes(m[at:at+len(raw)]).hex(),after=raw.hex(),reason=reason))
                for i,b in enumerate(raw):m.u8[at+i]=b
            def callback(event):
                nonlocal pending
                a,r=event['address'],event['registers']
                if a==0x08008F4C and not entries:
                    entries.append(event|dict(guard=bytes(m[r[13]:r[13]+32]).hex()))
                    write(cell,(m.u32[cell]&~0x6000).to_bytes(4,'little'),'Current tile lacks the two terrain bits examined at 09720/09760')
                    write(actor+0x84,b'\x14\0\x14\0','Positive HP and maximum 20, above the ten-point damage')
                if a==0x08015870:
                    wrappers.append(event)
                    write(0x0200C890,bytes([suppressed]),'Exercise the original conditional queue predicate')
                audit.callback(event)
                if a==0x08000FB8 and r[14]==0x0800979D:
                    require(r[1]==row['offset']+0x08000000 and r[0]==r[13]+0x150 and r[2]==10,
                            'Conditional damage source/argument/output differs')
                    expected=materialize(bytes.fromhex(row['encoded_hex']),[10],m)
                    pending=(r,expected,bytes(m[r[0]+256:r[0]+272]))
                    if not suppressed:checks.append(ActionCheck(g,expected[:-1],0x08015883,256,pending[2]))
                if a==0x0800979C and pending:
                    old,expected,guard=pending
                    require(bytes(m[old[0]:old[0]+len(expected)])==expected and
                            bytes(m[old[0]+256:old[0]+272])==guard and r[4:12]==old[4:12] and r[13]==old[13],
                            'Terrain format bytes, guard or ABI differ')
                    formats.append(dict(raw_hex=expected.hex(),source=old[1],guard_abi_preserved=True));pending=None
                for check in checks:
                    if not (check.complete and check.returned):check.callback(event)
                if a==0x08009830 and entries:
                    old=entries[0]
                    require(r[4:12]==old['registers'][4:12] and r[13]==old['registers'][13] and r[1]==old['registers'][14]
                            and bytes(m[r[13]:r[13]+32]).hex()==old['guard'],'Terrain turn return ABI differs')
                    returns.append(event|dict(hp=m.u16[actor+0x84]))
            with Debugger(g,callback,max_events=200000) as debug:
                for a in set(audit.ADDRESSES)|{0x08008F4C,0x08015870,0x08015882,0x0800979C,0x08009830,0x08001C68}:
                    debug.breakpoint(a)
                g.press('A',hold=1,wait=0)
                for _ in range(900):
                    g.frames(1)
                    if returns:break
                g.frames(5);g.capture('result')
            require(len(entries)==len(returns)==len(formats)==len(wrappers)==1 and not pending,
                    'Conditional terrain path did not complete once')
            require(returns[0]['hp']==10 and len(checks)==1-suppressed and
                    all(c.complete and c.returned for c in checks),'Damage or queue outcome differs')
            require(inventory==bytes(m[0x0200DF28:0x0200E888]) and g.snapshot().battery==fixture.battery,
                    'Terrain probe changed inventory or battery')
            result=dict(suppressed=suppressed,inputs=g.inputs,overrides=writes,entries=entries,returns=returns,
                        formats=formats,wrappers=wrappers,audit=audit.report(),images=g.images)
            result['passed']=not any(result['audit'][k] for k in ('unclassified_glyphs','unreadable_streams','layout_violations'))
            (g.output/'report.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
            cases.append(result)
            print('Conditional terrain damage:',suppressed,result['passed'],flush=True)
    report=dict(rom_sha256=digest(rom),tool_sha256=digest(Path(__file__).read_bytes()),cases=cases,
                passed=all(r['passed'] for r in cases),scope=__doc__)
    (output/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    require(report['passed'],'Conditional terrain damage findings')
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,default=ROOT/'build/english')
    parser.add_argument('--output',type=Path,default=ROOT/'build/english/terrain-damage-validation')
    args=parser.parse_args();run(args.source,args.output)
