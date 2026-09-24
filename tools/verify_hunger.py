"""Native hunger thresholds/counter and one-line warnings after ordinary actions."""
import argparse
import json,struct
import mgba.log
from tools.rom import ROOT,digest,require
from tools.emulator import Session,Debugger
from tools.hunger_text import add_hunger
from tools.verify_combat_prototype import CombatCheck

OUT=ROOT/'build/hunger-prototype'


def candidate():
    from tools import build_english as english
    prior=english.add_combat;resource=None
    def add(build):
        nonlocal resource
        result=prior(build);resource=add_hunger(build);return result
    try:english.add_combat=add;rom,build=english.build_rom(include_story=False,include_extra_consumers=False)
    finally:english.add_combat=prior
    build['hunger']=resource;build['reviewed_resource_counts']['hunger']=5;build['total_reviewed_inserted_resources']+=5
    OUT.mkdir(parents=True,exist_ok=True);(OUT/'game.gba').write_bytes(rom);(OUT/'build.json').write_text(json.dumps(build,indent=2)+'\n');return rom,build


def run(cumulative=False):
    global OUT
    from tools import verify_player_status_prototype as status
    mgba.log.silence()
    if cumulative:
        OUT=ROOT/'build/english/hunger-validation'
        rom=(ROOT/'build/english/torneko-2-english.gba').read_bytes()
        build=json.loads((ROOT/'build/english/build.json').read_text())
        require(digest(rom)==build['output_sha256'],'Stale cumulative hunger ROM')
    else:rom,build=candidate()
    prior=status.OUT
    try:status.OUT=OUT;fixture=status.ready(rom,build)
    finally:status.OUT=prior
    targets={r['offset']+0x08000000:r for r in build['hunger']['entries']};results=[]
    for label,fullness,counter,slot in [('twenty',0x1400,0,0x23C),('ten',0xA00,0,0x240),('empty-first',0,0,0x244),('empty-second',0,1,0x248),('empty-third',0,2,0x24C),('above-twenty',0x1500,0,None),('empty-later',0,3,None)]:
        print('Hunger:',label,flush=True)
        with Session(rom,OUT/label) as game:
            game.restore(fixture);m=game.core.memory;hero=m.u32[0x02001624];overrides=[]
            def write(a,data):
                overrides.append({'address':a,'before':bytes(m[a:a+len(data)]).hex(),'after':data.hex()})
                for i,v in enumerate(data):m.u8[a+i]=v
            write(hero+0x54,struct.pack('<I',fullness));write(0x02003B9C,struct.pack('<I',counter))
            write(hero+0x84,struct.pack('<HH',100,100))
            gold=m.u32[hero+0x60];inventory=bytes(m[0x0200DF28:0x0200DF28+2400]);checks=[];transitions=[];turns=[];decrements=[]
            def cb(e):
                a,r=e['address'],e['registers']
                if a==0x08008F4C:turns.append(e)
                if a==0x08009040:decrements.append({'before':m.u32[hero+0x54],'native_cost':r[4],'modifier_flags':r[7]})
                if a==0x08009104:
                    require(r[0] in targets,'Hunger did not use owned private text');row=targets[r[0]]
                    require(row['table_offset']==slot,'Wrong native hunger stage')
                    transitions.append({'source':r[0],'slot':slot,'fullness_after':m.u32[hero+0x54],'counter_after':m.u32[0x02003B9C],'hp_after':m.u16[hero+0x84]})
                    checks.append(CombatCheck(game,bytes.fromhex(row['encoded_hex'])[:-1],0x08009109,256,bytes(m[r[0]+256:r[0]+272])))
                for c in checks:
                    if not(c.complete and c.returned):c.callback(e)
            with Debugger(game,cb,max_events=100000) as d:
                for a in (0x08008F4C,0x08009040,0x08009104,0x0801588C,0x080158CE,0x08001BC4,0x08001C14,0x08001C68,0x08009108):d.breakpoint(a)
                game.press('A',wait=0)
                for _ in range(240):
                    game.frames(1)
                    if checks and checks[0].complete and checks[0].returned:break
                game.capture('warning')
            require(len(turns)==1,'Hunger probe did not perform one native turn: '+str(len(turns)))
            require((len(checks)==1 and checks[0].complete and checks[0].returned and checks[0].queued['one_line']) if slot else not checks,'Hunger warning rendering/quiet branch differs')
            require(len(decrements)==1 and decrements[0]['native_cost']==12 and m.u32[hero+0x54]==max(0,fullness-12) and m.u32[0x02003B9C]==(0 if fullness else counter+1),'Native hunger decrement/counter differs: '+repr((label,fullness,m.u32[hero+0x54],counter,m.u32[0x02003B9C],transitions)))
            if not fullness:require(m.u16[hero+0x84]==99,'Native starvation damage differs')
            require(m.u32[hero+0x60]==gold and bytes(m[0x0200DF28:0x0200DF28+2400])==inventory and game.snapshot().battery==fixture.battery,'Hunger changed inventory/gold/save')
            results.append({'case':label,'overrides':overrides,'turns':turns,'transitions':transitions,'native_decrements':decrements,'queue':checks[0].queued if checks else None,'draws':checks[0].draws if checks else [],'fullness_after':m.u32[hero+0x54],'counter_after':m.u32[0x02003B9C],'hp_after':m.u16[hero+0x84],'inputs':game.inputs,'images':{'warning.png':digest((game.output/'warning.png').read_bytes())}})
    (OUT/'report.json').write_text(json.dumps({'passed':True,'rom_sha256':digest(rom),'cases':results,'scope':'Controlled fullness/starvation counter and healthy HP; ordinary attack input invokes native per-turn logic. Five warning stages and two quiet branches, thresholds/native12-unit decrement in this fixture/starvation damage, one-line glyph pixels/queue ABI and unchanged items/gold/save. No source pointer or PC redirection. Full gameplay progression and other per-turn effects remain separate.'},indent=2)+'\n');print('Hunger:',len(results),'cases passed',flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cumulative',action='store_true')
    run(parser.parse_args().cumulative)

