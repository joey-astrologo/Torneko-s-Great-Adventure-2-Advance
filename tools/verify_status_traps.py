"""Native sleep, illusion and confusion trap handlers with complete message chains."""
import argparse
import json,struct
import mgba.log
from tools.rom import ROOT,digest,require
from tools.emulator import Session,Debugger,ffi
from tools.status_trap_text import add_status_traps
from tools.dialogue_checks import player_layout_cases
from tools.name_entry import HERO
from tools.verify_service_ui import materialize
from tools.verify_combat_prototype import CombatCheck

OUT=ROOT/'build/status-traps-prototype'


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
        OUT=ROOT/'build/english/status-traps-validation'
        rom=(ROOT/'build/english/torneko-2-english.gba').read_bytes()
        build=json.loads((ROOT/'build/english/build.json').read_text())
        require(digest(rom)==build['output_sha256'],'Stale cumulative status-traps ROM')
    else:rom,build=candidate()
    prior=status.OUT
    try:status.OUT=OUT;fixture=status.ready(rom,build)
    finally:status.OUT=prior
    direct={r['offset']+0x08000000:r for r in build['status_traps']['entries']}
    effect_rows={r['table_offset']:r for family in ('player_conditions','player_effects','player_status') for r in build[family]['entries']}
    results=[]
    for kind,entry,end,notice,effect in [('sleep',0x08027A10,0x08027A86,0x308,0xF0),('hallucination',0x08027A8C,0x08027B02,0x314,0xE4),('confusion',0x08027B08,0x08027B7E,0x310,0xE0)]:
        for refused in (0,1):
            for label,name in player_layout_cases():
                case=f'{kind}-{refused}-{label}';print('Status trap:',case,flush=True)
                with Session(rom,OUT/case) as game:
                    game.restore(fixture);m=game.core.memory;hero=m.u32[0x02001624];overrides=[]
                    def write(a,data):
                        overrides.append({'address':a,'before':bytes(m[a:a+len(data)]).hex(),'after':data.hex()})
                        for i,v in enumerate(data):m.u8[a+i]=v
                    write(HERO,name.ljust(16,b'\0'))
                    for offset in (0x95,0x96,0x97,0xA4,0xB2):write(hero+offset,b'\0')
                    write(hero+8,struct.pack('<I',m.u32[hero+8]&~0x20000000))
                    write(0x020081D4,struct.pack('<I',m.u32[0x020081D4]&~0x500000))
                    initial=[];guard=[];returned=[];checks=[];queue_ids=[];formats=[];formatted={};effect_called=[];images=[]
                    gold=m.u32[hero+0x60];inventory=bytes(m[0x0200DF28:0x0200DF28+2400]);hp=m.u16[hero+0x84]
                    targets=direct|{effect_rows[effect]['offset']+0x08000000:effect_rows[effect]}
                    expected_slots=[0x2F4,0x2EC] if refused else [0x2F4,notice,effect]
                    def cb(e):
                        a,r=e['address'],e['registers']
                        if a==0x08008F4C and not initial:
                            initial.append(r);guard.append(bytes(m[r[13]:r[13]+32]))
                            overrides.append({'event':e,'pc_after':entry,'r0_after':hero,'r1_after':refused})
                            game.core.cpu.gprs[0]=hero;game.core.cpu.gprs[1]=refused
                            require(game.core._core.writeRegister(game.core._core,b'pc',ffi.new('uint32_t*',entry)),'Trap entry redirect failed')
                        if a in (0x0800B374,0x0800B6E0,0x0800B664) and initial:effect_called.append(a)
                        if a==0x08000FB8 and initial and r[1] in targets:
                            row=targets[r[1]];expected=materialize(bytes.fromhex(row['encoded_hex']),[HERO],m)
                            require(r[0]==r[13] and (b'%s' not in bytes.fromhex(row['encoded_hex']) or r[2]==HERO) and len(expected)<=256,'Status trap formatted fields/capacity differ')
                            formatted[r[0]]=(row,expected,bytes(m[r[0]+256:r[0]+272]))
                            formats.append({'id':row['id'],'expected_hex':expected.hex(),'bytes':len(expected),'capacity':256})
                        if a==0x0801588C and initial and (r[0] in direct or r[0] in formatted):
                            require(not checks or checks[-1].complete and checks[-1].returned,'Trap queued over incomplete message')
                            if r[0] in direct:row=direct[r[0]];expected=bytes.fromhex(row['encoded_hex']);g=bytes(m[r[0]+256:r[0]+272])
                            else:
                                row,expected,g=formatted.pop(r[0]);require(bytes(m[r[0]:r[0]+len(expected)])==expected,'Trap formatted stream differs')
                            queue_ids.append(row['table_offset']);require(queue_ids==expected_slots[:len(queue_ids)],'Trap message order differs: '+repr(queue_ids))
                            checks.append(CombatCheck(game,expected[:-1],r[14],256,g))
                        if a==end and initial:
                            before=initial[0];require(r[13]==before[13] and r[4:12]==before[4:12] and r[0]==before[14] and bytes(m[r[13]:r[13]+32])==guard[0],'Trap consumer ABI/guard differs');returned.append(e)
                        for c in checks:
                            if not(c.complete and c.returned):c.callback(e)
                    with Debugger(game,cb,max_events=250000) as d:
                        addresses={0x08008F4C,0x08000FB8,0x0801588C,0x080158CE,0x08001BC4,0x08001C14,0x08001C68,end,0x0800B374,0x0800B6E0,0x0800B664,
                                   0x08027A28,0x08027A40,0x08027AA4,0x08027ABC,0x08027AF8,0x08027B1E,0x08027B30,0x08027B76,0x08015868,0x0800B758}
                        for a in addresses:d.breakpoint(a)
                        game.press('A',wait=0);captured=0
                        for _ in range(900):
                            game.frames(1)
                            if len(checks)>captured and checks[-1].complete:
                                image=f'message-{captured}';game.capture(image);images.append(image+'.png');captured=len(checks)
                            if returned and all(c.complete and c.returned for c in checks):break
                    require(len(initial)==len(returned)==1 and queue_ids==expected_slots and len(checks)==len(expected_slots) and all(c.complete and c.returned and c.queued['one_line'] for c in checks),'Status trap chain incomplete: '+repr((case,queue_ids,len(returned),[(c.complete,c.returned) for c in checks])))
                    require(len(effect_called)==(0 if refused else 1),'Status trap effect dispatch differs')
                    timer_offset={'sleep':0x97,'hallucination':0x96,'confusion':0x95}[kind]
                    require((m.u8[hero+timer_offset]>0)==(not refused),'Status trap native timer differs')
                    if kind=='hallucination' and not refused:require(m.u8[hero+timer_offset]==50,'Hallucination duration differs')
                    require(m.u32[hero+0x60]==gold and m.u16[hero+0x84]==hp and bytes(m[0x0200DF28:0x0200DF28+2400])==inventory and game.snapshot().battery==fixture.battery,'Status trap changed HP/items/gold/save')
                    results.append({'case':case,'overrides':overrides,'queue_slots':queue_ids,'queues':[c.queued for c in checks],'draws':[c.draws for c in checks],'formats':formats,'effect_calls':effect_called,'native_timers':{'sleep':m.u8[hero+0x97],'hallucination':m.u8[hero+0x96],'confusion':m.u8[hero+0x95]},'inputs':game.inputs,'images':{p:digest((game.output/p).read_bytes()) for p in images}})
    (OUT/'report.json').write_text(json.dumps({'passed':True,'rom_sha256':digest(rom),'cases':results,'scope':'Controlled native handler entry and activation/refusal arguments, cleared resistance/status fields and three English/Japanese player-name bounds. Complete notice/effect message chains, one-line glyphs, native status dispatch/timers, queue/caller ABI and unchanged HP/items/gold/save. Ordinary trap placement/discovery and other resistance/handler branches remain separate.'},indent=2)+'\n');print('Status traps:',len(results),'cases passed',flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cumulative',action='store_true')
    run(parser.parse_args().cumulative)

