"""Native NPC selector and complete tutorial opcode routes after controlled setup.

The host dispatches original opcode handlers and skips asynchronous WAIT. Map,
actor and bank setup are controlled; ordinary story activation is not claimed.
"""
import argparse
import json
from pathlib import Path
import struct
import mgba.log

from tools.bakery_playtest import service_ready
from tools.dialogue_checks import TextChecks
from tools.emulator import Debugger, Session, ffi
from tools.opening_text import BANK_RAM, banks
from tools.rom import ROOT, digest, load_base, require
from tools.screen_text_audit import ScreenTextAudit


def run(source):
    mgba.log.silence()
    out=source/'tutorial-script-validation'
    rom=(source/'torneko-2-english.gba').read_bytes()
    build=json.loads((source/'build.json').read_text())
    require(digest(rom)==build['output_sha256'], 'Tutorial script ROM differs')
    original=load_base()
    fixture=service_ready(rom,out)
    rows={r['rom_offset']+0x08000000:r for r in build['dialogue']['entries']}
    rows.update({r['offset']+0x08000000:r for r in build['tutorial_help']['entries']})
    repairs={r['configuration']:r for r in build['tutorial_help']['repairs']}
    cases=[]
    for bank,node,selector,root,config,intro,outro in (
            (4,11,1,0x6B6,12,'event-bank-4.3696','event-bank-4.3744'),
            (4,11,2,0x6CA,12,'event-bank-4.3696','event-bank-4.3744'),
            (5,4,1,0x3A4,14,'event-bank-5.3469','event-bank-5.34d5')):
        label=f'bank-{bank}-map-{node}-npc-{selector}'
        print('Tutorial script:',label,flush=True)
        with Session(rom,out/label) as game:
            game.restore(fixture);m=game.core.memory
            checks=TextChecks(game,rows);audit=ScreenTextAudit(game)
            state=dict(phase='initial',menu=False,topic_returned=False,cancelled=False)
            bank_end=BANK_RAM+banks()[bank]['decoded_bytes']
            initial=[];controls=[];steps=[];menus=[]
            inventory=bytes(m[0x0200DF28:0x0200E888])

            def register(index,value):
                controls.append(dict(register=index,before=int(game.core.cpu.gprs[index]),after=value))
                game.core.cpu.gprs[index]=value

            def jump(value):
                controls.append(dict(pc_after=value))
                require(game.core._core.writeRegister(game.core._core,b'pc',ffi.new('uint32_t*',value)), 'Script redirect failed')

            def write(address,value,size):
                raw=value.to_bytes(size,'little')
                controls.append(dict(address=address,before_hex=bytes(m[address:address+size]).hex(),after_hex=raw.hex()))
                for i,byte in enumerate(raw):m.u8[address+i]=byte

            def callback(event):
                a,r=event['address'],event['registers']
                if state['phase']=='dispatch':
                    audit.callback(event);checks.callback(event)
                if a==0x0801DFAC:
                    if state['phase']=='initial':
                        initial.append(event|dict(guard=bytes(m[r[13]:r[13]+32]).hex()))
                        state['phase']='load'
                        register(0,bank);register(14,0x0804B33D);jump(0x0804D6F8)
                    elif state['phase']=='dispatch':
                        old=initial[0]
                        require(r[4:12]==old['registers'][4:12] and r[13]==old['registers'][13]
                                and bytes(m[r[13]:r[13]+32]).hex()==old['guard'], 'Script handler ABI/guard differs')
                        pointer=m.u32[0x02010138];opcode=m.u8[pointer]
                        if opcode==20:
                            steps.append(dict(offset=pointer-0x020129AC,opcode=20,host_skipped_wait=True))
                            pointer+=1;write(0x02010138,pointer,4);opcode=m.u8[pointer]
                        if opcode==21:
                            state['phase']='done';jump(old['registers'][14]&~1);return
                        require(opcode==8,'Unexpected tutorial script opcode')
                        raw=bytes(m[pointer:pointer+6])
                        require(raw[4] in (0,2) and (raw[4]!=2 or raw[5]==config),'Tutorial script mode/configuration differs')
                        steps.append(dict(offset=pointer-0x020129AC,opcode=opcode,raw_hex=raw.hex()))
                        write(0x02010138,pointer+1,4)
                        register(14,0x0801DFAD)
                        jump(struct.unpack_from('<I',original,0x14CE30+(opcode-1)*4)[0]&~1)
                elif a==0x0804B33C and state['phase']=='load':
                    require(m.u32[0x02010144]==0x020129AC,'NPC resource differs')
                    write(0x0200FED8,node,1);write(0x02010A78+0x25,selector,1);write(0x02010A78+0x1F,5,1)
                    state['bank_bytes']=bytes(m[BANK_RAM:bank_end]).hex()
                    register(0,0);register(14,0x0801DFAD);state['phase']='dispatch'
                elif a==0x0804B3A6 and state['phase']=='dispatch':
                    require(m.u32[0x02010138]==0x020129AC+root,'Native NPC selected a different script')
                elif a==0x08050DD0 and state['phase']=='dispatch':
                    require(r[:2]==[0,repairs[config]['menu']],'Native script did not select repaired menu')
                    menus.append(event);state['menu']=True
                elif a==0x08050E6E and state['phase']=='dispatch':
                    state['topic_returned']=True

            with Debugger(game,callback,max_events=500000) as debug:
                for address in set(checks.ADDRESSES+audit.ADDRESSES+(0x0801DFAC,0x0804B33C,0x0804B3A6,0x08050DD0,0x08050E6E)):
                    debug.breakpoint(address)
                game.press('A',hold=1,wait=120)
                for page in range(80):
                    if state['phase']=='done':break
                    game.capture(f'page-{page}')
                    if state['topic_returned'] and not state['cancelled']:
                        state['cancelled']=True;game.press('B',hold=1,wait=120)
                    else:
                        game.press('A',hold=1,wait=120)
                require(state['phase']=='done' and state['topic_returned'] and len(menus)==1,'Tutorial script did not finish')
            prose=[r['id'] for r in checks.reads if r['id'].startswith('event-')]
            require(prose==[intro,repairs[config]['prose_ids'][0],outro] and checks.active is None,'Tutorial script prose order differs')
            require(bytes(m[BANK_RAM:bank_end]).hex()==state['bank_bytes'],'Tutorial changed the active dialogue bank')
            require(bytes(m[0x0200DF28:0x0200E888])==inventory and game.snapshot().battery==fixture.battery,'Tutorial changed inventory/save')
            result=audit.report()
            require(not audit.unclassified and not audit.unreadable and not audit.layout_violations,'Tutorial script text audit failed')
            cases.append(dict(case=label,bank=bank,map=node,selector=selector,configuration=config,
                steps=steps,menus=menus,reads=checks.reads,inputs=game.inputs,controls=controls,audit=result,
                caller_guard_abi_preserved=True,active_bank_preserved=True,bank_range=[BANK_RAM,bank_end],inventory_battery_preserved=True,
                images={p.name:digest(p.read_bytes()) for p in game.output.glob('*.png')}))
            (out/'partial.json').write_text(json.dumps(cases,indent=2)+'\n')
    report=dict(passed=True,rom_sha256=digest(rom),source_sha256=digest(original),cases=cases,
                tool_sha256=digest(Path(__file__).read_bytes()),fixture_sha256=digest(fixture.state),scope=__doc__)
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Tutorial script routes:',len(cases),'passed')
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,default=ROOT/'build/english')
    run(parser.parse_args().source)
