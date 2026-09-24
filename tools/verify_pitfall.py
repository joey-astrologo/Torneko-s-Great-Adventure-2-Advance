"""Native pitfall notice, avoided harm and separately owned delayed damage queue."""
import argparse
import json,struct
import mgba.log
from tools.rom import ROOT,digest,require
from tools.emulator import Session,Debugger,ffi
from tools.pitfall_text import add_pitfall
from tools.verify_combat_prototype import CombatCheck
OUT=ROOT/'build/pitfall-prototype'


def candidate():
    from tools import build_english as english
    rom,build=english.build_rom(include_story=False)
    OUT.mkdir(parents=True,exist_ok=True);(OUT/'game.gba').write_bytes(rom);(OUT/'build.json').write_text(json.dumps(build,indent=2)+'\n');return rom,build


def run(cumulative=False):
    global OUT
    from tools import verify_player_status_prototype as status
    mgba.log.silence()
    if cumulative:
        OUT=ROOT/'build/english/pitfall-validation'
        rom=(ROOT/'build/english/torneko-2-english.gba').read_bytes()
        build=json.loads((ROOT/'build/english/build.json').read_text())
        require(digest(rom)==build['output_sha256'],'Stale cumulative pitfall ROM')
    else:rom,build=candidate()
    prior=status.OUT
    try:status.OUT=OUT;fixture=status.ready(rom,build)
    finally:status.OUT=prior
    direct={r['offset']+0x08000000:r for r in build['pitfall']['entries']};results=[]
    for case in ('activated','refused','protected','special-floor'):
        print('Pitfall:',case,flush=True)
        with Session(rom,OUT/case) as game:
            game.restore(fixture);m=game.core.memory;hero=m.u32[0x02001624]
            initial=[];guard=[];returns=[];checks=[];slots=[];overrides=[];images=[];damage=[];transitions=[]
            gold=m.u32[hero+0x60];hp=m.u16[hero+0x84];items=bytes(m[0x0200DF28:0x0200DF28+2400])
            def write(a,data):
                overrides.append({'address':a,'before':bytes(m[a:a+len(data)]).hex(),'after':data.hex()})
                for i,v in enumerate(data):m.u8[a+i]=v
            expected=[0x334,0x338] if case=='activated' else [0x334,0x328]
            def cb(e):
                a,r=e['address'],e['registers']
                if a==0x08008F4C and not initial:
                    initial.append(r);guard.append(bytes(m[r[13]:r[13]+32]));overrides.append({'event':e,'pc_after':0x080283D4,'r0_after':hero,'r1_after':int(case=='refused')})
                    game.core.cpu.gprs[0]=hero;game.core.cpu.gprs[1]=int(case=='refused')
                    require(game.core._core.writeRegister(game.core._core,b'pc',ffi.new('uint32_t*',0x080283D4)),'Pitfall entry redirect failed')
                if a==0x080283F4 and initial and case=='special-floor':overrides.append({'event':e,'r0_after':1});game.core.cpu.gprs[0]=1
                if a==0x080283FC and initial:write(r[0]+4,struct.pack('<I',(m.u32[r[0]+4]&~0x1000)|(0x1000 if case=='protected' else 0)))
                if a==0x0801588C and initial and r[0] in direct:
                    require(not checks or checks[-1].complete and checks[-1].returned,'Pitfall messages overlap')
                    row=direct[r[0]];slots.append(row['table_offset']);require(slots==expected[:len(slots)],'Pitfall message order differs')
                    checks.append(CombatCheck(game,bytes.fromhex(row['encoded_hex'])[:-1],r[14],256,bytes(m[r[0]+256:r[0]+272])))
                if a==0x08006BF8 and initial:transitions.append(e)
                if a==0x080053B2 and initial and slots==[0x334,0x338]:damage.append(e|{'hp':m.u16[m.u32[0x02001624]+0x84]})
                if a==0x08028482 and initial:
                    old=initial[0];require(r[13]==old[13] and r[4:12]==old[4:12] and r[0]==old[14] and bytes(m[r[13]:r[13]+32])==guard[0],'Pitfall caller ABI/guard differs');returns.append(e)
                for c in checks:
                    if not(c.complete and c.returned):c.callback(e)
            with Debugger(game,cb,max_events=150000) as d:
                for a in (0x08008F4C,0x0801588C,0x080158CE,0x08001BC4,0x08001C14,0x08001C68,0x080283F4,0x080283FC,0x080283EA,0x0802842A,0x08005392,0x080053B2,0x08006BF8,0x08028482):d.breakpoint(a)
                game.press('A',wait=0);captured=0
                for _ in range(2400):
                    game.frames(1)
                    if len(checks)>captured and checks[-1].complete:
                        image='message-'+str(captured);game.capture(image);images.append(image+'.png');captured=len(checks)
                    if returns and slots==expected and all(c.complete and c.returned for c in checks) and (damage or case!='activated'):break
                game.capture('returned');images.append('returned.png')
            require(len(initial)==len(returns)==1 and slots==expected and all(c.complete and c.returned and c.queued['one_line'] for c in checks),'Pitfall chain incomplete: '+repr((case,slots,len(returns),len(damage))))
            require(len(transitions)==len(damage)==(1 if case=='activated' else 0),'Pitfall transition/delayed-damage dispatch differs')
            require(not damage or damage[0]['hp']==hp-5,'Pitfall delayed damage differs')
            require(case=='activated' or m.u16[hero+0x84]==hp,'Avoided pitfall changed HP')
            require(m.u32[m.u32[0x02001624]+0x60]==gold and bytes(m[0x0200DF28:0x0200DF28+2400])==items and game.snapshot().battery==fixture.battery,'Pitfall changed items/gold/battery')
            results.append({'case':case,'overrides':overrides,'queue_slots':slots,'queues':[c.queued for c in checks],'draws':[c.draws for c in checks],'transition_calls':transitions,'damage_checks':damage,'hp_before':hp,'inputs':game.inputs,'images':{p:digest((game.output/p).read_bytes()) for p in images}})
    (OUT/'report.json').write_text(json.dumps({'passed':True,'rom_sha256':digest(rom),'cases':results,'scope':'Controlled entry/activation, protection bit at its native read and special-floor getter return. Full pitfall and separately owned delayed damage messages, native five-HP reduction, one-line glyphs and queue/caller ABI. Items/gold/battery preserved. Checks stop after delayed damage, not final next-floor arrival. Ordinary trap discovery, protection acquisition, special-floor progression and death/revival remain separate.'},indent=2)+'\n');print('Pitfall:',len(results),'cases passed',flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cumulative',action='store_true')
    run(parser.parse_args().cumulative)
