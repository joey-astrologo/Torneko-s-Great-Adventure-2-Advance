"""Exercise computed wind stages through the original turn loop and player wrapper."""
import argparse
import json
from pathlib import Path

import mgba.log

from tools.dialogue_checks import player_layout_cases
from tools.emulator import Session, Debugger
from tools.name_entry import HERO
from tools.rom import ROOT, digest, require
from tools.screen_text_audit import ScreenTextAudit
from tools.service_fixtures import dungeon
from tools.verify_inventory_action_prototype import ActionCheck
from tools.verify_result_ui import native_format


def run(source):
    mgba.log.silence()
    rom = (source/'torneko-2-english.gba').read_bytes()
    build = json.loads((source/'build.json').read_text())
    require(digest(rom)==build['output_sha256'], 'Wind ROM differs')
    out = source/'wind-validation'
    fixture = dungeon(rom,build)
    final = build['wind']['entries'][0]
    notices = {r['table_offset']:r for r in build['combat']['queue_notices']['entries']}
    configurations = [(2,'native',None),(3,'native',None),(4,'native',None)]
    configurations += [(4,label,name) for label,name in player_layout_cases()]
    cases = []
    for stage,label,name in configurations:
        case = f'stage-{stage}-{label}'
        print('Wind:',case,flush=True)
        with Session(rom,out/case) as g:
            g.restore(fixture)
            m = g.core.memory
            audit = ScreenTextAudit(g)
            controls, wrappers, returns, formats, outcomes, checks = [],[],[],[],[],[]
            pending = []
            injected = False

            def write(at,raw):
                controls.append(dict(address=at,before=bytes(m[at:at+len(raw)]).hex(),after=raw.hex()))
                for i,v in enumerate(raw):m.u8[at+i]=v

            if name is not None:
                write(HERO,name.ljust(16,b'\0'))
            selected = bytes(m[HERO:HERO+16]).split(b'\0')[0]
            row = final if stage==4 else notices[stage*4+0x448]
            expected = bytes.fromhex(row['encoded_hex']).replace(b'%s',selected)

            def callback(event):
                nonlocal injected
                a,r = event['address'],event['registers']
                if a==0x08005150 and not injected:
                    for at,value in ((0x02003B34,stage-1),(0x02003B38,stage)):
                        write(at,value.to_bytes(4,'little'))
                    injected=True
                if a==0x08015848 and r[14]==0x080051F5:
                    wrappers.append(event|dict(guard=bytes(m[r[13]:r[13]+32]).hex()))
                    require(r[0] == (final['offset']+0x08000000 if stage==4 else row['source']['offset']+0x08000000),
                            'Computed wind source differs')
                if wrappers and not returns and a==0x08000FB8 and r[14]==0x08015861:
                    template = bytes(m[r[1]:r[1]+256]).split(b'\0')[0]+b'\0'
                    raw = native_format(template,[r[2]],m)
                    require(len(raw)<=256,'Wind formatter exceeds original buffer')
                    pending.append(dict(regs=r,raw=raw,guard=bytes(m[r[0]+256:r[0]+272])))
                    checks.append(ActionCheck(g,expected[:-1],0x08015869,None,b''))
                if a==0x08015860 and pending:
                    p = pending.pop();old=p['regs'];dest=old[0]
                    require(bytes(m[dest:dest+len(p['raw'])])==p['raw']
                            and bytes(m[dest+256:dest+272])==p['guard']
                            and r[4:12]==old[4:12] and r[13]==old[13], 'Wind format/guard/ABI differs')
                    formats.append(dict(raw_hex=p['raw'].hex(),bytes=len(p['raw']),guard_preserved=True))
                if checks and not(checks[0].complete and checks[0].returned):
                    checks[0].callback(event)
                audit.callback(event)
                if a==0x080051F4 and wrappers:
                    old=wrappers[0]['registers']
                    require(r[4:12]==old[4:12] and r[13]==old[13]
                            and bytes(m[r[13]:r[13]+32]).hex()==wrappers[0]['guard'], 'Wind wrapper ABI differs')
                    returns.append(event)
                if a==0x0800527A:
                    outcomes.append(dict(frame=event['frame'],next_return_reason=5))

            with Debugger(g,callback,max_events=1000000) as d:
                addresses = set(audit.ADDRESSES+(0x08005150,0x08015848,0x080051F4,
                    0x08015860,0x0800527A,0x08015868,0x08001C68))
                for address in addresses:d.breakpoint(address)
                g.press('A',wait=0)
                captured=False
                for frame in range(1600):
                    g.frames(1)
                    if checks and checks[0].complete and not captured:
                        g.capture('message');captured=True
                    if returns and (stage!=4 or outcomes):break
                require(injected and len(wrappers)==len(returns)==len(formats)==len(checks)==1
                        and captured and checks[0].complete and checks[0].returned and not pending,
                        'Wind route incomplete')
                require(stage!=4 or outcomes,'Native wind-expulsion animation/outcome not reached')
            screen = audit.report()
            (g.output/'screen.json').write_text(json.dumps(screen,ensure_ascii=False,indent=2)+'\n')
            require(not audit.unclassified and not audit.unreadable and not audit.layout_violations,
                    'Wind screen contains Japanese text or layout failures')
            require(checks[0].queued['one_line'],'Wind notice should occupy one line')
            cases.append(dict(case=case,stage=stage,player_hex=selected.hex(),inputs=g.inputs,
                controls=controls,formats=formats,wrapper_abi_preserved=True,queue=checks[0].queued,
                outcome=outcomes,audit=screen,images={p.name:digest(p.read_bytes()) for p in g.output.glob('*.png')}))
    report = dict(passed=True,rom_sha256=digest(rom),tool_sha256=digest(Path(__file__).read_bytes()),
                  audit_tool_sha256=digest((ROOT/'tools/screen_text_audit.py').read_bytes()),
                  fixture_sha256=digest(fixture.state),cases=cases,
                  scope='Controlled current/previous wind stages and saved names; ordinary A input executes the native turn loop, animation, computed selector, player formatter and queue. Stages2/3 and stage4 with original, required-English and widest English/Japanese saved names. No PC/register/source overrides. Original256-byte bounds, complete visible glyphs and caller ABI checked. Stage4 reaches its original expulsion outcome; subsequent results/story progression is separate.')
    (out/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print('Wind:',len(cases),'passed',flush=True)
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,default=ROOT/'build/english')
    run(parser.parse_args().source)
