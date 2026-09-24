"""Native mud trap messages, protection and equipment flags."""
import argparse
import json,struct
import mgba.log
from tools.rom import ROOT,digest,require
from tools.emulator import Session,Debugger,ffi
from tools.mud_trap_text import add_mud_trap
from tools.verify_combat_prototype import CombatCheck
OUT=ROOT/'build/mud-trap-prototype'


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
        OUT=ROOT/'build/english/mud-trap-validation'
        rom=(ROOT/'build/english/torneko-2-english.gba').read_bytes()
        build=json.loads((ROOT/'build/english/build.json').read_text())
        require(digest(rom)==build['output_sha256'],'Stale cumulative mud-trap ROM')
    else:rom,build=candidate()
    prior=status.OUT
    try:status.OUT=OUT;fixture=status.ready(rom,build)
    finally:status.OUT=prior
    direct={r['offset']+0x08000000:r for r in build['mud_trap']['entries']};results=[]
    for case,ident,refused in [(f'bread-{i}',i,0) for i in range(203,211)]+[('refused',204,1),('no-bread',212,0)]:
        print('Mud trap:',case,flush=True)
        with Session(rom,OUT/case) as game:
            game.restore(fixture);m=game.core.memory;hero=m.u32[0x02001624];overrides=[]
            def write(a,data):
                overrides.append({'address':a,'before':bytes(m[a:a+len(data)]).hex(),'after':data.hex()})
                for i,v in enumerate(data):m.u8[a+i]=v
            mapping=bytes(m[0x020013D0:0x020014D0])
            write(0x0200DF28+8,bytes([mapping.index(ident)]))
            gold=m.u32[hero+0x60];hp=m.u16[hero+0x84];items=bytes(m[0x0200DF28:0x0200DF28+2400]);type_address=0x02003BAC+205*20;type_before=m.u32[type_address]
            expected_items=bytearray(items);changed=[]
            for i in range(20):
                flags=struct.unpack_from('<I',items,i*120)[0];item_id=mapping[items[i*120+8]]
                if not refused and flags&0x80000000 and item_id in (203,204,206,207,208,210):
                    changed.append(i);expected_items[i*120+8]=mapping.index(205)
                    struct.pack_into('<I',expected_items,i*120,flags|0x08000000)
            initial=[];guard=[];returns=[];checks=[];slots=[];effect_calls=[];images=[]
            expected=[0x2F4,0x2EC] if refused else [0x2F4,0x320,0x324 if changed else 0x328]
            def cb(e):
                a,r=e['address'],e['registers']
                if a==0x08008F4C and not initial:
                    initial.append(r);guard.append(bytes(m[r[13]:r[13]+32]));overrides.append({'event':e,'pc_after':0x08027DCC,'r0_after':hero,'r1_after':refused})
                    game.core.cpu.gprs[0]=hero;game.core.cpu.gprs[1]=refused
                    require(game.core._core.writeRegister(game.core._core,b'pc',ffi.new('uint32_t*',0x08027DCC)),'Mud trap redirect failed')
                if a==0x0801588C and initial and r[0] in direct:
                    require(not checks or checks[-1].complete and checks[-1].returned,'Mud messages overlap')
                    row=direct[r[0]];slots.append(row['table_offset']);require(slots==expected[:len(slots)],'Mud message order differs: '+repr((case,slots,expected)))
                    checks.append(CombatCheck(game,bytes.fromhex(row['encoded_hex'])[:-1],r[14],256,bytes(m[r[0]+256:r[0]+272])))
                if a==0x08004B08 and initial:effect_calls.append(e)
                if a==0x08027EBE and initial:
                    before=initial[0];require(r[13]==before[13] and r[4:12]==before[4:12] and r[0]==before[14] and bytes(m[r[13]:r[13]+32])==guard[0],'Mud trap caller ABI/guard differs');returns.append(e)
                for c in checks:
                    if not(c.complete and c.returned):c.callback(e)
            with Debugger(game,cb,max_events=150000) as d:
                for a in (0x08008F4C,0x0801588C,0x080158CE,0x08001BC4,0x08001C14,0x08001C68,0x08027DE4,0x08027DFC,0x08027E16,0x08027E96,0x08027EB8,0x08004B08,0x08027EBE):d.breakpoint(a)
                game.press('A',wait=0);captured=0
                for _ in range(900):
                    game.frames(1)
                    if len(checks)>captured and checks[-1].complete:
                        name='message-'+str(captured);game.capture(name);images.append(name+'.png');captured=len(checks)
                    if returns and all(c.complete and c.returned for c in checks):break
                game.capture('returned');images.append('returned.png')
            require(len(initial)==len(returns)==1 and slots==expected and all(c.complete and c.returned and c.queued['one_line'] for c in checks),'Mud trap messages/return incomplete')
            require(len(effect_calls)==len(changed) and [e['registers'][0] for e in effect_calls]==[0x0200DF28+i*120 for i in changed] and all(e['registers'][1]==205 for e in effect_calls),'Mud native item transformation differs')
            require(m.u32[type_address]==(type_before|0x40000000 if changed else type_before),'Mud identification flag differs')
            require(m.u16[hero+0x84]==hp and m.u32[hero+0x60]==gold and bytes(m[0x0200DF28:0x0200DF28+2400])==expected_items and game.snapshot().battery==fixture.battery,'Mud changed HP/items/gold/battery')
            results.append({'case':case,'overrides':overrides,'queue_slots':slots,'queues':[c.queued for c in checks],'draws':[c.draws for c in checks],'item_transform_calls':effect_calls,'changed_slots':changed,'input_item_id':ident,'type_flags_before':type_before,'type_flags_after':m.u32[type_address],'inventory_before_hex':items.hex(),'inventory_after_hex':bytes(m[0x0200DF28:0x0200DF28+2400]).hex(),'inputs':game.inputs,'images':{p:digest((game.output/p).read_bytes()) for p in images}})
    (OUT/'report.json').write_text(json.dumps({'passed':True,'rom_sha256':digest(rom),'cases':results,'scope':'Controlled native mud-trap entry/activation and first-slot item ID. All eight bread IDs203..210, failed activation and no-bread cases use original selection/transformation/identification. Exact changed item IDs/flags, unchanged other inventory bytes, complete one-line messages, caller/queue ABI and HP/gold/battery pass. Ordinary trap discovery/acquisition and other inventory arrangements remain separate.'},indent=2)+'\n');print('Mud trap:',len(results),'cases passed',flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cumulative',action='store_true')
    run(parser.parse_args().cumulative)
