"""Native summon trap, both spawn modes, activation failure and zero-count branch."""
import argparse
import json,struct
import mgba.log
from tools.rom import ROOT,digest,require
from tools.emulator import Session,Debugger,ffi
from tools.summon_trap_text import add_summon_trap
from tools.verify_combat_prototype import CombatCheck
OUT=ROOT/'build/summon-trap-prototype'


def candidate():
    from tools import build_english as english
    rom,build=english.build_rom(include_story=False)
    OUT.mkdir(parents=True,exist_ok=True);(OUT/'game.gba').write_bytes(rom);(OUT/'build.json').write_text(json.dumps(build,indent=2)+'\n');return rom,build


def run(cumulative=False):
    global OUT
    from tools import verify_player_status_prototype as status
    mgba.log.silence()
    if cumulative:
        OUT=ROOT/'build/english/summon-trap-validation'
        rom=(ROOT/'build/english/torneko-2-english.gba').read_bytes()
        build=json.loads((ROOT/'build/english/build.json').read_text())
        require(digest(rom)==build['output_sha256'],'Stale cumulative summon_trap ROM')
    else:rom,build=candidate()
    prior=status.OUT
    try:status.OUT=OUT;fixture=status.ready(rom,build)
    finally:status.OUT=prior
    direct={r['offset']+0x08000000:r for r in build['summon_trap']['entries']};results=[]
    for case in ('activated','refused','other-spawn-mode','zero-spawn-count'):
        print('Summon trap:',case,flush=True)
        with Session(rom,OUT/case) as game:
            game.restore(fixture);m=game.core.memory;hero=m.u32[0x02001624];failed=int(case=='refused')
            initial=[];guard=[];returns=[];checks=[];slots=[];spawns=[];spawn_returns=[];overrides=[];images=[]
            def actors():
                rows=[]
                for i in range(56):
                    a=m.u32[0x02001624+4*i]
                    require(0x02000000<=a<0x02040000,'Actor pointer outside EWRAM')
                    if m.u32[a+8]&0x80000000 and m.u16[a+0x84]>0:rows.append({'slot':i,'address':a,'hp':m.u16[a+0x84],'position':[m.u16[a+0x66],m.u16[a+0x68]]})
                return rows
            fixture_actors=actors();before=[];hp=m.u16[hero+0x84];gold=m.u32[hero+0x60];items=bytes(m[0x0200DF28:0x0200DF28+2400])
            expected=[0x2F4,0x2EC] if failed else [0x2F4,0x31C]+([0x3D4] if case=='zero-spawn-count' else [])
            def cb(e):
                a,r=e['address'],e['registers']
                if a==0x08008F4C and not initial:
                    before.extend(actors());initial.append(r);guard.append(bytes(m[r[13]:r[13]+32]));overrides.append({'event':e,'pc_after':0x08027CE0,'r0_after':hero,'r1_after':failed})
                    game.core.cpu.gprs[0]=hero;game.core.cpu.gprs[1]=failed
                    require(game.core._core.writeRegister(game.core._core,b'pc',ffi.new('uint32_t*',0x08027CE0)),'Summon entry redirect failed')
                if a==0x08027D40 and initial and case=='other-spawn-mode':
                    overrides.append({'event':e,'r0_after':1});game.core.cpu.gprs[0]=1
                if a==0x080131BC and initial:
                    require(r[0]==4 and r[1:3]==[m.u16[hero+0x66],m.u16[hero+0x68]] and r[3]==0xFFFFFFFF,'Native spawn arguments differ')
                    stack=[m.u32[r[13]+4*i] for i in range(7)]
                    require(stack==[0,0xFFFFFFFF,0,r[1],r[2],1,int(case=='other-spawn-mode')],'Native spawn stack arguments differ')
                    spawns.append(e|{'stack_arguments':stack})
                    if case=='zero-spawn-count':overrides.append({'event':e,'r0_after':0});game.core.cpu.gprs[0]=0
                if a==0x08027DAC and initial:spawn_returns.append(e)
                if a==0x0801588C and initial and r[0] in direct:
                    require(not checks or checks[-1].complete and checks[-1].returned,'Summon messages overlap')
                    row=direct[r[0]];slots.append(row['table_offset']);require(slots==expected[:len(slots)],'Summon message order differs')
                    checks.append(CombatCheck(game,bytes.fromhex(row['encoded_hex'])[:-1],r[14],256,bytes(m[r[0]+256:r[0]+272])))
                if a==0x08027DC6 and initial:
                    old=initial[0];require(r[13]==old[13] and r[4:12]==old[4:12] and r[0]==old[14] and bytes(m[r[13]:r[13]+32])==guard[0],'Summon caller ABI/guard differs');returns.append(e|{'actors':actors()})
                for c in checks:
                    if not(c.complete and c.returned):c.callback(e)
            with Debugger(game,cb,max_events=150000) as d:
                for a in (0x08008F4C,0x0801588C,0x080158CE,0x08001BC4,0x08001C14,0x08001C68,0x08027CF8,0x08027D10,0x08027D2A,0x08027DC0,0x08027D40,0x080131BC,0x08027DAC,0x08027DC6):d.breakpoint(a)
                game.press('A',wait=0);captured=0
                for _ in range(1200):
                    game.frames(1)
                    if len(checks)>captured and checks[-1].complete:
                        image='message-'+str(captured);game.capture(image);images.append(image+'.png');captured=len(checks)
                    if returns and all(c.complete and c.returned for c in checks):break
                game.capture('returned');images.append('returned.png')
            require(len(initial)==len(returns)==1 and slots==expected and all(c.complete and c.returned and c.queued['one_line'] for c in checks),'Summon chain incomplete')
            require(len(spawns)==len(spawn_returns)==(0 if failed else 1),'Summon dispatch differs')
            spawned=case in ('activated','other-spawn-mode');after=returns[0]['actors']
            require(len(after)==len(before)+(4 if spawned else 0),'Native spawned actor count differs')
            require(all(row in after for row in before),'Summon changed existing live actors: '+repr((before,after)))
            require(not spawn_returns or spawn_returns[0]['registers'][0]==int(spawned),'Native spawn result differs')
            require(m.u16[hero+0x84]==hp and m.u32[hero+0x60]==gold and bytes(m[0x0200DF28:0x0200DF28+2400])==items and game.snapshot().battery==fixture.battery,'Summon changed HP/items/gold/battery')
            results.append({'case':case,'overrides':overrides,'queue_slots':slots,'queues':[c.queued for c in checks],'draws':[c.draws for c in checks],'spawn_calls':spawns,'spawn_returns':spawn_returns,'fixture_actors':fixture_actors,'actors_at_handler_entry':before,'actors_after':after,'inputs':game.inputs,'images':{p:digest((game.output/p).read_bytes()) for p in images}})
    (OUT/'report.json').write_text(json.dumps({'passed':True,'rom_sha256':digest(rom),'cases':results,'scope':'Controlled entry/activation; actual native four-monster spawning in both mode branches. Alternate mode is selected by a recorded getter-return override. Failure message uses the original spawner with its count controlled to zero; ordinary spawn exhaustion/terrain rejection remains unclaimed. Complete one-line chains, caller/queue ABI, existing actors from handler entry to return and HP/items/gold/save pass. The ordinary triggering turn may move actors before handler entry. Ordinary trap discovery remains separate.'},indent=2)+'\n');print('Summon trap:',len(results),'cases passed',flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cumulative',action='store_true')
    run(parser.parse_args().cumulative)
