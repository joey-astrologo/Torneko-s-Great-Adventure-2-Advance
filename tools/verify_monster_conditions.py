"""Native fullness drain, spell sealing and Kaclang with actual state outcomes."""
import argparse
import json
import struct
import mgba.log
from tools.compact_font import encode
from tools.dialogue_checks import player_layout_cases
from tools.emulator import Debugger, Session, ffi
from tools.monster_condition_text import add_monster_conditions
from tools.name_entry import HERO
from tools.rom import ROOT, digest, require
from tools.verify_inventory_action_prototype import ActionCheck
from tools.verify_service_ui import materialize
OUT = ROOT / 'build/monster-conditions-prototype'


def candidate():
    from tools.build_english import build_rom
    rom, build = build_rom(include_story=False)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT/'game.gba').write_bytes(rom)
    (OUT/'build.json').write_text(json.dumps(build, indent=2)+'\n')
    return rom, build


def run(cumulative=False):
    global OUT
    from tools import verify_player_status_prototype as status
    mgba.log.silence()
    if cumulative:
        OUT = ROOT/'build/english/monster-conditions-validation'
        rom = (ROOT/'build/english/torneko-2-english.gba').read_bytes()
        build = json.loads((ROOT/'build/english/build.json').read_text())
        require(digest(rom) == build['output_sha256'], 'Stale cumulative condition ROM')
    else:
        rom, build = candidate()
    prior = status.OUT
    try:
        status.OUT = OUT
        fixture = status.ready(rom, build)
    finally:
        status.OUT = prior
    direct = {r['offset']+0x08000000:r for r in build['monster_conditions']['entries']}
    wrapper = {r['offset']+0x08000000:r for r in build['player_messages']['entries']}
    notices = {r['source']['offset']+0x08000000:r for r in build['combat']['queue_notices']['entries']}
    actor_fields = {'maximum-width':encode('W'*31), 'maximum-bytes':encode('i'*31),
                    'coloured':b'\x03\x05'+encode('Monster')[:-1]+b'\x05\0'}
    configs = [('fullness-'+str(value), 'fullness', value, '')
               for value in (0, 20*256, 20*256+1, 21*256, 100*256, 200*256, 0x7FFFFFFF)]
    configs += [('fullness-'+kind+'-'+label, 'fullness', 100*256, kind+':'+label)
                for kind in ('protected', 'resistant') for label, _ in player_layout_cases()]
    configs += [('seal-'+kind+'-'+label, 'seal', value, label)
                for kind,value in [('fresh',0),('existing',7),('resistant',-1)]
                for label,_ in player_layout_cases()]
    configs += [('kaclang-'+label, 'kaclang', 0, label) for label in ['native']+list(actor_fields)]
    configs += [('kaclang-existing', 'kaclang', 7, 'native')]
    results = []
    for case, kind, value, field in configs:
        print('Monster condition:',case,flush=True)
        entry, end = {'fullness':(0x0802C14C,0x0802C1E4), 'seal':(0x0802CE0C,0x0802CE7A),
                      'kaclang':(0x0802CE88,0x0802CEBA)}[kind]
        slot = (0x190 if field.startswith('protected:') else 0x2C8 if field.startswith('resistant:')
                else 0x2C4) if kind=='fullness' else (0x380 if value<0 else 0x418) if kind=='seal' else 0x490
        with Session(rom,OUT/case) as game:
            game.restore(fixture);m=game.core.memory;hero=m.u32[0x02001624]
            initial=[];returns=[];checks=[];formats=[];overrides=[];images=[];pending=[];formatted={};actors=[]
            gold=m.u32[hero+0x60];hp=m.u16[hero+0x84];inventory=bytes(m[0x0200DF28:0x0200DF28+2400])
            def write(a,data):
                overrides.append({'address':a,'before':bytes(m[a:a+len(data)]).hex(),'after':data.hex()})
                for i,v in enumerate(data):m.u8[a+i]=v
            def callback(e):
                a,r=e['address'],e['registers']
                if a==0x08008F4C and not initial:
                    initial.append(e|{'guard':bytes(m[r[13]:r[13]+32]).hex()})
                    actor=next(m.u32[0x02001624+4*i] for i in range(1,56)
                               if 0x02000000<=m.u32[0x02001624+4*i]<0x0203FF00 and
                               m.u32[m.u32[0x02001624+4*i]+8]&0x80000000 and
                               m.u16[m.u32[0x02001624+4*i]+0x84]>0)
                    actors.append(actor)
                    if kind=='fullness':
                        write(hero+0x54,struct.pack('<I',value))
                        bits=(0x800 if field.startswith('protected:') else
                              0x10000000 if field.startswith('resistant:') else 0)
                        write(hero+8,struct.pack('<I',(m.u32[hero+8]&~0x10000800)|bits))
                    elif kind=='seal':write(hero+0x9E,bytes([max(value,0)]))
                    else:write(actor+0x9B,bytes([value]))
                    player=field.split(':')[-1]
                    if player in dict(player_layout_cases()):write(HERO,dict(player_layout_cases())[player].ljust(16,b'\0'))
                    overrides.append({'event':e,'pc_after':entry,'r0_after':actor})
                    game.core.cpu.gprs[0]=actor
                    require(game.core._core.writeRegister(game.core._core,b'pc',ffi.new('uint32_t*',entry)), 'Condition redirect failed')
                if initial and kind=='seal' and a==0x0802CE14:
                    overrides.append({'event':e,'r0_after':int(value<0)})
                    game.core.cpu.gprs[0]=int(value<0)
                if initial and kind=='kaclang' and a==0x0802CEA2 and field in actor_fields:
                    write(0x02008D08,actor_fields[field].ljust(64,b'\0'))
                    overrides.append({'event':e,'r0_after':0x02008D08});game.core.cpu.gprs[0]=0x02008D08
                if initial and a==0x08000FB8 and r[1] in direct|wrapper:
                    row=(direct|wrapper)[r[1]]
                    require(row['table_offset']==slot and r[0]==r[13], 'Condition formatter owner differs')
                    if kind=='fullness' and slot==0x2C4:
                        require(r[2]==(max(0,value-20*256)+255)//256, 'Fullness result/rounding differs')
                    payload=materialize(bytes.fromhex(row['encoded_hex']),[r[2]],m)
                    require(len(payload)<=row['maximum_bytes']<=256,'Condition output overflows')
                    pending.append((r,row,payload,bytes(m[r[0]+256:r[0]+272])))
                if pending and a==(pending[-1][0][14]&~1):
                    before,row,payload,guard=pending.pop()
                    require(r[4:12]==before[4:12] and r[13]==before[13] and
                            bytes(m[before[0]:before[0]+len(payload)])==payload and
                            bytes(m[before[0]+256:before[0]+272])==guard,'Condition formatter bytes/ABI/guard differ')
                    formatted[before[0]]=(row,payload,guard)
                    formats.append({'id':row['id'],'hex':payload.hex(),'capacity':256})
                if initial and a==0x0801588C:
                    require(not checks,'Unexpected additional condition message')
                    if r[0] in formatted:row,payload,guard=formatted.pop(r[0]);capacity=256
                    else:
                        require(r[0] in notices,'Untranslated condition queue')
                        row=notices[r[0]];payload=bytes.fromhex(row['encoded_hex']);guard=b'';capacity=None
                    require(row['table_offset']==slot,'Condition message differs')
                    checks.append(ActionCheck(game,payload[:-1],r[14],capacity,guard))
                if initial and a==end:
                    before=initial[0]['registers']
                    require(r[4:12]==before[4:12] and r[13]==before[13] and r[0]==before[14] and
                            bytes(m[r[13]:r[13]+32]).hex()==initial[0]['guard'],'Condition caller ABI differs')
                    actual=m.u32[hero+0x54] if kind=='fullness' else m.u8[hero+0x9E] if kind=='seal' else m.u8[actors[0]+0x9B]
                    expected=(value if slot!=0x2C4 else max(0,value-20*256)) if kind=='fullness' else (0 if value<0 else value or 20) if kind=='seal' else value or 15
                    require(actual==expected,'Condition native state differs: '+repr((case,actual,expected)))
                    returns.append(e|{'state_before':value,'state_after':actual})
                for c in checks:
                    if not(c.complete and c.returned):c.callback(e)
            with Debugger(game,callback,max_events=150000) as debug:
                for a in (0x08008F4C,0x0802CE14,0x0802CEA2,0x08000FB8,0x0802C1D6,0x0802CE68,0x0802CEAC,
                          0x08015860,0x0801588C,0x080158CE,0x08001BC4,0x08001C14,0x08001C68,
                          0x08015868,0x0802C196,0x0802C1DE,0x0802CE28,0x0802CE70,0x0802CEB4,end):debug.breakpoint(a)
                game.press('A',wait=0)
                for _ in range(1200):
                    game.frames(1)
                    if checks and checks[0].complete and not images:
                        game.capture('message');images.append('message.png')
                    if returns and checks and checks[0].complete and checks[0].returned:break
            require(len(initial)==len(returns)==len(checks)==1 and checks[0].complete and checks[0].returned
                    and not pending and not formatted,'Condition chain incomplete: '+case)
            require(checks[0].queued['one_line']==(case!='kaclang-maximum-width' and not field.startswith('protected:')),'Condition one-line choice differs')
            require(m.u16[hero+0x84]==hp and m.u32[hero+0x60]==gold and
                    bytes(m[0x0200DF28:0x0200DF28+2400])==inventory and game.snapshot().battery==fixture.battery,
                    'Condition changed HP/gold/items/save')
            results.append({'case':case,'queue_slots':[slot],'queues':[checks[0].queued],'draws':[checks[0].draws],
                            'formats':formats,'overrides':overrides,'return':returns[0],'inputs':game.inputs,
                            'images':{p:digest((game.output/p).read_bytes()) for p in images}})
    (OUT/'report.json').write_text(json.dumps({'passed':True,'rom_sha256':digest(rom),'cases':results,
        'scope':'Controlled monster-effect entry, initial fullness/status and resistance. Actual fixed-point20-unit '
        'fullness loss/clamp/ceiling, fresh/existing20-value spell seal and15-value Kaclang status, complete '
        'messages, fields,256-byte guards and ABI pass. Stored values are not asserted to be ordinary turn '
        'durations. Ordinary AI, resistance acquisition and recovery remain separate.'},indent=2)+'\n')
    print('Monster conditions:',len(results),'cases passed',flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cumulative',action='store_true')
    run(parser.parse_args().cumulative)
