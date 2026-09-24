"""Native equipment-removal trap messages, protection and equipment flags."""
import argparse
import json,struct
import mgba.log
from tools.rom import ROOT,digest,require
from tools.emulator import Session,Debugger,ffi
from tools.unequip_trap_text import add_unequip_trap
from tools.verify_combat_prototype import CombatCheck
OUT=ROOT/'build/unequip-trap-prototype'


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
        OUT=ROOT/'build/english/unequip-trap-validation'
        rom=(ROOT/'build/english/torneko-2-english.gba').read_bytes()
        build=json.loads((ROOT/'build/english/build.json').read_text())
        require(digest(rom)==build['output_sha256'],'Stale cumulative unequip-trap ROM')
    else:rom,build=candidate()
    prior=status.OUT
    try:status.OUT=OUT;fixture=status.ready(rom,build)
    finally:status.OUT=prior
    direct={r['offset']+0x08000000:r for r in build['unequip_trap']['entries']};results=[]
    for case in ('activated','refused','nothing-equipped','protected'):
        print('Unequip trap:',case,flush=True)
        with Session(rom,OUT/case) as game:
            game.restore(fixture);m=game.core.memory;hero=m.u32[0x02001624];overrides=[]
            def write(a,data):
                overrides.append({'address':a,'before':bytes(m[a:a+len(data)]).hex(),'after':data.hex()})
                for i,v in enumerate(data):m.u8[a+i]=v
            if case=='nothing-equipped':
                for i in range(20):
                    a=0x0200DF28+i*120;write(a,struct.pack('<I',m.u32[a]&~0x800000))
            refused=int(case=='refused');gold=m.u32[hero+0x60];hp=m.u16[hero+0x84];items=bytes(m[0x0200DF28:0x0200DF28+2400])
            expected_items=bytearray(items)
            equipped=[]
            for i in range(20):
                flags=struct.unpack_from('<I',items,i*120)[0]
                if flags&0x80000000 and flags&0x800000:
                    equipped.append(i)
                    if case=='activated':struct.pack_into('<I',expected_items,i*120,flags&~0x800000)
            require(bool(equipped)==(case!='nothing-equipped'),'Unequip fixture equipment differs')
            initial=[];guard=[];returns=[];checks=[];slots=[];effect_calls=[];images=[]
            expected=[0x2F4,0x2EC if case in ('refused','protected') else 0x438 if case=='nothing-equipped' else 0x318]
            def cb(e):
                a,r=e['address'],e['registers']
                if a==0x08008F4C and not initial:
                    initial.append(r);guard.append(bytes(m[r[13]:r[13]+32]));overrides.append({'event':e,'pc_after':0x08027B84,'r0_after':hero,'r1_after':refused})
                    game.core.cpu.gprs[0]=hero;game.core.cpu.gprs[1]=refused
                    require(game.core._core.writeRegister(game.core._core,b'pc',ffi.new('uint32_t*',0x08027B84)),'Unequip trap redirect failed')
                if a==0x08027BA6 and initial:
                    overrides.append({'protection_read_event':e})
                    write(0x020081D8,struct.pack('<I',(m.u32[0x020081D8]&~4)|(4 if case=='protected' else 0)))
                if a==0x0801588C and initial and r[0] in direct:
                    require(not checks or checks[-1].complete and checks[-1].returned,'Unequip messages overlap')
                    row=direct[r[0]];slots.append(row['table_offset']);require(slots==expected[:len(slots)],'Unequip message order differs: '+repr((case,slots,expected)))
                    checks.append(CombatCheck(game,bytes.fromhex(row['encoded_hex'])[:-1],r[14],256,bytes(m[r[0]+256:r[0]+272])))
                if a==0x0800BA70 and initial:effect_calls.append(e)
                if a==0x08027CDA and initial:
                    before=initial[0];require(r[13]==before[13] and r[4:12]==before[4:12] and r[0]==before[14] and bytes(m[r[13]:r[13]+32])==guard[0],'Unequip trap caller ABI/guard differs');returns.append(e)
                for c in checks:
                    if not(c.complete and c.returned):c.callback(e)
            with Debugger(game,cb,max_events=150000) as d:
                for a in (0x08008F4C,0x0801588C,0x080158CE,0x08001BC4,0x08001C14,0x08001C68,0x08027BA0,0x08027BA6,0x08027BD4,0x08027C9A,0x08027CD0,0x0800BA70,0x08027CDA):d.breakpoint(a)
                game.press('A',wait=0);captured=0
                for _ in range(900):
                    game.frames(1)
                    if len(checks)>captured and checks[-1].complete:
                        name='message-'+str(captured);game.capture(name);images.append(name+'.png');captured=len(checks)
                    if returns and all(c.complete and c.returned for c in checks):break
                game.capture('returned');images.append('returned.png')
            require(len(initial)==len(returns)==1 and slots==expected and all(c.complete and c.returned and c.queued['one_line'] for c in checks),'Unequip trap messages/return incomplete')
            require(len(effect_calls)==(1 if case=='activated' else 0),'Unequip native equipment update differs')
            require(m.u16[hero+0x84]==hp and m.u32[hero+0x60]==gold and bytes(m[0x0200DF28:0x0200DF28+2400])==expected_items and game.snapshot().battery==fixture.battery,'Unequip changed HP/items/gold/battery')
            results.append({'case':case,'overrides':overrides,'queue_slots':slots,'queues':[c.queued for c in checks],'draws':[c.draws for c in checks],'equipment_update_calls':effect_calls,'equipped_before':equipped,'inventory_before_hex':items.hex(),'inventory_after_hex':bytes(m[0x0200DF28:0x0200DF28+2400]).hex(),'inputs':game.inputs,'images':{p:digest((game.output/p).read_bytes()) for p in images}})
    (OUT/'report.json').write_text(json.dumps({'passed':True,'rom_sha256':digest(rom),'cases':results,'scope':'Controlled native equipment-removal trap entry, activation and protection fields. Existing naturally equipped shield is removed by the original handler; failed activation, no-equipment and protection branches preserve items. Complete messages, one-line pixels, caller/queue ABI, exact inventory flags and HP/gold/battery pass. Ordinary trap discovery and protection acquisition remain separate.'},indent=2)+'\n');print('Unequip trap:',len(results),'cases passed',flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cumulative',action='store_true')
    run(parser.parse_args().cumulative)
