"""Native acid and equipment-rust branches, item fields and enhancement bounds."""
import argparse
import json,struct
import mgba.log
from tools.rom import ROOT,digest,require,load_base
from tools.emulator import Session,Debugger,ffi
from tools.rust_text import add_rust
from tools.compact_font import encode
from tools.verify_service_ui import materialize
from tools.verify_inventory_action_prototype import ActionCheck
OUT=ROOT/'build/rust-prototype'


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
        OUT=ROOT/'build/english/rust-validation'
        rom=(ROOT/'build/english/torneko-2-english.gba').read_bytes()
        build=json.loads((ROOT/'build/english/build.json').read_text())
        require(digest(rom)==build['output_sha256'],'Stale cumulative rust ROM')
    else:rom,build=candidate()
    prior=status.OUT
    try:status.OUT=OUT;fixture=status.ready(rom,build)
    finally:status.OUT=prior
    direct={r['offset']+0x08000000:r for r in build['rust']['entries']};results=[];base=load_base()
    # mode1 shield,2 weapon,3 native available-equipment choice.
    cases=[('acid-leather',1,30,3,0x43C),('acid-rust',1,31,3,0x280),('acid-refused',1,31,3,0x2EC),
           ('shield-none',1,None,3,0x8E4),('weapon-none',2,None,3,0x8E8),('both-none',3,None,3,0x288),
           ('shield-leather',1,30,3,0x43C),('shield-silver',1,33,3,0x43C),
           ('shield-rust',1,31,3,0x280),('weapon-rust',2,1,3,0x284),
           ('shield-minimum',1,31,-99,None),('weapon-minimum',2,1,-99,None),
           ('shield-ring',1,31,3,0x27C),('weapon-ring',2,1,3,0x27C),
           ('shield-protected',1,31,3,0x304),('weapon-protected',2,1,3,0x304),
           ('named-maximum-width',1,30,3,0x43C),('named-maximum-bytes',1,30,3,0x43C),('named-coloured',1,30,3,0x43C)]
    fields={'named-maximum-width':encode('W'*27),'named-maximum-bytes':b'1'+encode('i'*31),'named-coloured':b'\x03\x05'+encode('Shield')[:-1]+b'\x05\0'}
    for case,mode,ident,enhancement,slot in cases:
        print('Rust:',case,flush=True);acid=case.startswith('acid-');entry=0x08027990 if acid else 0x08010EE4;end=0x08027A08 if acid else 0x08010F96
        with Session(rom,OUT/case) as game:
            game.restore(fixture);m=game.core.memory;hero=m.u32[0x02001624];overrides=[]
            def write(a,data):
                overrides.append({'address':a,'before':bytes(m[a:a+len(data)]).hex(),'after':data.hex()})
                for i,v in enumerate(data):m.u8[a+i]=v
            mapping=bytes(m[0x020013D0:0x020014D0]);inventory=bytearray(2400)
            if ident is not None:
                properties=struct.unpack_from('<I',base,0x141B9C+ident*24+4)[0]
                struct.pack_into('<I',inventory,0,0xC8800000|properties);inventory[4]=enhancement&255;inventory[5]=1;inventory[8]=mapping.index(ident)
                type_address=0x02003BAC+ident*20;write(type_address,struct.pack('<I',m.u32[type_address]|0x40000000))
            write(0x0200DF28,inventory);expected_inventory=bytearray(inventory)
            if slot in (0x280,0x284):expected_inventory[4]=(enhancement-1)&255
            gold=m.u32[hero+0x60];hp=m.u16[hero+0x84];initial=[];guard=[];returns=[];checks=[];slots=[];formats=[];pending=[];formatted={};images=[];branches=[]
            expected=([0x2F4]+([] if case=='acid-refused' else [0x300]) if acid else [])+([] if slot is None else [slot])
            def cb(e):
                a,r=e['address'],e['registers']
                if a==0x08008F4C and not initial:
                    initial.append(r);guard.append(bytes(m[r[13]:r[13]+32]));args=[hero,int(case=='acid-refused')] if acid else [mode,r[1]]
                    overrides.append({'entry_event':e,'pc_after':entry,'r0_after':args[0],'r1_after':args[1]});game.core.cpu.gprs[0]=args[0];game.core.cpu.gprs[1]=args[1]
                    require(game.core._core.writeRegister(game.core._core,b'pc',ffi.new('uint32_t*',entry)),'Rust redirect failed')
                if a in (0x08010FBC,0x08011090) and case.endswith('-protected') and initial:
                    branches.append({'event':e,'r0_after':1});game.core.cpu.gprs[0]=1
                if a in (0x08011020,0x080110B0) and case.endswith('-ring') and initial:
                    branches.append({'event':e,'r0_after':90});game.core.cpu.gprs[0]=90
                if a==0x08010FE4 and case in fields and initial:write(r[13],fields[case].ljust(64,b'\0'))
                if a==0x08000FB8 and initial and r[1] in direct:
                    row=direct[r[1]];require(row['table_offset']==0x43C and r[0]==r[13]+64 and r[2]==r[13] and r[14]==0x08010FF7,'Rust native formatter owner/fields differ')
                    payload=materialize(bytes.fromhex(row['encoded_hex']),[r[2]],m);require(len(payload)<=row['maximum_bytes']<=192,'Rust format exceeds conservative byte reserve')
                    pending.append((r,row,payload,bytes(m[r[0]+256:r[0]+272])))
                if a==0x08010FF6 and pending:
                    before,row,payload,g=pending.pop();require(r[13]==before[13] and r[4:12]==before[4:12] and bytes(m[before[0]:before[0]+len(payload)])==payload and bytes(m[before[0]+256:before[0]+272])==g,'Rust formatter bytes/guard/ABI differ')
                    formatted[before[0]]=(row,payload,g);formats.append({'id':row['id'],'hex':payload.hex(),'bytes':len(payload),'capacity':256,'item_capacity':64})
                if a==0x0801588C and initial and (r[0] in direct or r[0] in formatted):
                    require(not checks or checks[-1].complete and checks[-1].returned,'Rust messages overlap')
                    if r[0] in direct:row=direct[r[0]];payload=bytes.fromhex(row['encoded_hex']);g=b'';capacity=None
                    else:row,payload,g=formatted.pop(r[0]);capacity=256
                    slots.append(row['table_offset']);require(slots==expected[:len(slots)],'Rust source order differs: '+repr((case,slots,expected)))
                    checks.append(ActionCheck(game,payload[:-1],r[14],capacity,g))
                if a==end and initial:
                    before=initial[0];require(r[13]==before[13] and r[4:12]==before[4:12] and r[0 if acid else 1]==before[14] and bytes(m[r[13]:r[13]+32])==guard[0],'Rust caller ABI/guard differs')
                    if not acid:require(r[0]==int(slot in (0x280,0x284)),'Rust native return flag differs')
                    returns.append(e)
                for check in checks:
                    if not(check.complete and check.returned):check.callback(e)
            with Debugger(game,cb,max_events=150000) as d:
                for a in (0x08008F4C,0x08010FBC,0x08011090,0x08011020,0x080110B0,0x08010FE4,0x08000FB8,0x08010FF6,0x0801588C,0x080158CE,0x08001BC4,0x08001C14,0x08001C68,0x080279A8,0x080279C0,0x080279FC,0x08010F64,0x08011014,0x08011034,0x0801105E,0x080110A4,0x080110C4,0x080110EE,end):d.breakpoint(a)
                game.press('A',wait=0);captured=0
                for _ in range(900):
                    game.frames(1)
                    if len(checks)>captured and checks[-1].complete:
                        name='message-'+str(captured);game.capture(name);images.append(name+'.png');captured=len(checks)
                    if returns and all(c.complete and c.returned for c in checks):break
                game.capture('returned');images.append('returned.png')
            require(len(initial)==len(returns)==1 and slots==expected and all(c.complete and c.returned for c in checks) and not pending and not formatted,'Rust messages/return incomplete: '+case)
            require(all(c.queued['one_line']==(case!='named-maximum-width') for c in checks),'Rust conditional line decision differs')
            require(bytes(m[0x0200DF28:0x0200DF28+2400])==expected_inventory and m.u32[hero+0x60]==gold and m.u16[hero+0x84]==hp and game.snapshot().battery==fixture.battery,'Rust changed unexpected item/HP/gold/save state')
            results.append({'case':case,'mode':mode,'item_id':ident,'overrides':overrides,'controlled_resistance_returns':branches,'queue_slots':slots,'queues':[c.queued for c in checks],'draws':[c.draws for c in checks],'formats':formats,'inventory_before_hex':bytes(inventory).hex(),'inventory_after_hex':bytes(expected_inventory).hex(),'inputs':game.inputs,'images':{p:digest((game.output/p).read_bytes()) for p in images}})
    (OUT/'report.json').write_text(json.dumps({'passed':True,'rom_sha256':digest(rom),'cases':results,'scope':'Controlled acid/rust entry, native weapon/shield mode and inventory records; explicit resistance/ring getter overrides. Actual one-point enhancement changes, -99 quiet bound, no-equipment and named material resistance, formatted64/256-byte guards, queue/caller ABI and unchanged HP/gold/battery. Three item-field stress cases include native conditional one/two-line choice. Ordinary trap/protection acquisition and other modes/inventory arrangements remain separate.'},indent=2)+'\n');print('Rust:',len(results),'cases passed',flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cumulative',action='store_true')
    run(parser.parse_args().cumulative)
