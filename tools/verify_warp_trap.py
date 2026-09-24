"""Complete native warp-trap announcement, failure and teleport return checks."""
import argparse
import json,struct
import mgba.log
from tools.rom import ROOT,digest,require
from tools.emulator import Session,Debugger,ffi
from tools.warp_trap_text import add_warp_trap
from tools.dialogue_checks import player_layout_cases
from tools.name_entry import HERO
from tools.verify_combat_prototype import CombatCheck
OUT=ROOT/'build/warp-trap-prototype'


def candidate():
    from tools.build_english import build_rom
    rom,build=build_rom(include_story=False)
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'game.gba').write_bytes(rom)
    (OUT/'build.json').write_text(json.dumps(build,indent=2)+'\n')
    return rom,build


def run(cumulative=False):
    global OUT
    from tools import verify_player_status_prototype as status
    mgba.log.silence()
    if cumulative:
        OUT=ROOT/'build/english/warp-trap-validation'
        rom=(ROOT/'build/english/torneko-2-english.gba').read_bytes()
        build=json.loads((ROOT/'build/english/build.json').read_text())
        require(digest(rom)==build['output_sha256'],'Stale cumulative warp-trap ROM')
    else:rom,build=candidate()
    prior=status.OUT
    try:status.OUT=OUT;fixture=status.ready(rom,build)
    finally:status.OUT=prior
    direct={r['offset']+0x08000000:r for r in build['warp_trap']['entries']};results=[]
    for refused in (0,1):
        for label,name in player_layout_cases():
            case=f'{refused}-{label}';print('Warp trap:',case,flush=True)
            with Session(rom,OUT/case) as game:
                game.restore(fixture);m=game.core.memory;hero=m.u32[0x02001624]
                name_before=bytes(m[HERO:HERO+16]);name_after=name.ljust(16,b'\0')
                for i,v in enumerate(name_after):m.u8[HERO+i]=v
                overrides=[{'address':HERO,'before':name_before.hex(),'after':name_after.hex()}]
                before_position=(m.u16[hero+0x66],m.u16[hero+0x68]);gold=m.u32[hero+0x60];hp=m.u16[hero+0x84];items=bytes(m[0x0200DF28:0x0200DF28+2400])
                initial=[];guard=[];returns=[];checks=[];slots=[];teleports=[];teleport_returns=[];images=[]
                expected=[0x2F0,0x2EC] if refused else [0x2F0]
                def cb(e):
                    a,r=e['address'],e['registers']
                    if a==0x08008F4C and not initial:
                        initial.append(r);guard.append(bytes(m[r[13]:r[13]+32]));overrides.append({'event':e,'pc_after':0x08027680,'r0_after':hero,'r1_after':refused})
                        game.core.cpu.gprs[0]=hero;game.core.cpu.gprs[1]=refused
                        require(game.core._core.writeRegister(game.core._core,b'pc',ffi.new('uint32_t*',0x08027680)),'Warp trap redirect failed')
                    if a==0x0801588C and initial and r[0] in direct:
                        require(not checks or checks[-1].complete and checks[-1].returned,'Warp messages overlap')
                        row=direct[r[0]];slots.append(row['table_offset']);require(slots==expected[:len(slots)],'Warp message order differs')
                        checks.append(CombatCheck(game,bytes.fromhex(row['encoded_hex'])[:-1],r[14],256,bytes(m[r[0]+256:r[0]+272])))
                    if a==0x08012220 and initial:
                        require(r[0]==hero and r[1]==0,'Warp actor/mode differs');teleports.append(e)
                    if a==0x080276E0 and initial:teleport_returns.append(e|{'position':[m.u16[hero+0x66],m.u16[hero+0x68]]})
                    if a==0x080276EC and initial:
                        before=initial[0];require(r[13]==before[13] and r[4:12]==before[4:12] and r[0]==before[14] and bytes(m[r[13]:r[13]+32])==guard[0],'Warp trap caller ABI/guard differs');returns.append(e)
                    for c in checks:
                        if not(c.complete and c.returned):c.callback(e)
                with Debugger(game,cb,max_events=150000) as d:
                    for a in (0x08008F4C,0x0801588C,0x080158CE,0x08001BC4,0x08001C14,0x08001C68,0x08027698,0x080276B0,0x08012220,0x080276E0,0x080276EC):d.breakpoint(a)
                    game.press('A',wait=0);captured=0
                    for _ in range(900):
                        game.frames(1)
                        if len(checks)>captured and checks[-1].complete:
                            name='message-'+str(captured);game.capture(name);images.append(name+'.png');captured=len(checks)
                        if returns and all(c.complete and c.returned for c in checks):break
                    game.capture('returned');images.append('returned.png')
                require(len(initial)==len(returns)==1 and slots==expected and all(c.complete and c.returned and c.queued['one_line'] for c in checks),'Warp trap messages/return incomplete')
                require(len(teleports)==len(teleport_returns)==(0 if refused else 1),'Warp native dispatch differs')
                after_position=(m.u16[hero+0x66],m.u16[hero+0x68])
                require((after_position==before_position)==bool(refused),'Warp native movement differs')
                require(m.u16[hero+0x84]==hp and m.u32[hero+0x60]==gold and bytes(m[0x0200DF28:0x0200DF28+2400])==items and game.snapshot().battery==fixture.battery,'Warp changed HP/items/gold/battery')
                results.append({'case':case,'overrides':overrides,'queue_slots':slots,'queues':[c.queued for c in checks],'draws':[c.draws for c in checks],'teleport_calls':teleports,'teleport_returns':teleport_returns,'position_before':before_position,'position_after':after_position,'inputs':game.inputs,'images':{p:digest((game.output/p).read_bytes()) for p in images}})
    (OUT/'report.json').write_text(json.dumps({'passed':True,'rom_sha256':digest(rom),'cases':results,'scope':'Controlled entry/activation/name fields; full original native warp handler and teleport routine. Announcement/failure, one-line pixels, complete caller/queue return ABI, actual movement or unchanged failed position, HP/items/gold/battery pass. Ordinary placement/discovery and other terrain/teleport constraints remain separate.'},indent=2)+'\n');print('Warp trap:',len(results),'cases passed',flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cumulative',action='store_true')
    run(parser.parse_args().cumulative)
