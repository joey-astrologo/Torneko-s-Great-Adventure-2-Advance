"""Controlled native player-effect branches, with exact buffers and one-line pixels."""
import argparse,json
import struct
import mgba.log
from tools.rom import ROOT, digest, require
from tools.emulator import Session, Debugger, ffi
from tools.player_effect_text import add_effects
from tools.dialogue_checks import player_layout_cases
from tools.name_entry import HERO
from tools.verify_service_ui import materialize
from tools.verify_combat_prototype import CombatCheck

OUT = ROOT/'build/player-effect-prototype'
# Source, native entry, final BX, queue return, gear word/mask, helper result.
CASES = [(0x200,0xB450,0xB4AE,0xB4A9,None,0),
         (0x7A8,0xB450,0xB4AE,0xB4A9,None,1),
         (0x490,0xB4B4,0xB536,0x15869,(0x020081D8,0),None),
         (0x7DC,0xB4B4,0xB536,0x15869,(0x020081D8,0x10),None),
         (0x498,0xB540,0xB5C6,0x15869,(0x020081D4,0),None),
         (0x7A0,0xB540,0xB5C6,0xB579,(0x020081D4,0x800000),None),
         (0x8F4,0xB5D0,0xB654,0x15869,(0x020081D8,0),None),
         (0x918,0xB5D0,0xB654,0x15869,(0x020081D8,0x20),None),
         (0xE0,0xB664,0xB6DA,0x15869,None,0),
         (0x110,0xB664,0xB6DA,0x15869,None,1),
         (0x118,0xB664,0xB6DA,0x15869,None,2),
         (0x7AC,0xB6E0,0xB75E,0xB759,(0x020081D4,0x400000),None),
         (0x3DC,0xB7DC,0xB818,0xB813,None,None)]

def candidate():
    import tools.build_english as english
    prior = english.add_combat; effects = None
    def add(build):
        nonlocal effects
        result = prior(build); effects = add_effects(build); return result
    try:
        english.add_combat = add; rom, build = english.build_rom(include_story=False,include_extra_consumers=False)
    finally: english.add_combat = prior
    build['player_effects'] = effects
    build['reviewed_resource_counts']['player_effects'] = len(effects['entries'])
    build['total_reviewed_inserted_resources'] += len(effects['entries'])
    build['scope'] = 'Separate player-effect research candidate; no cumulative acceptance.'
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT/'game.gba').write_bytes(rom)
    (OUT/'build.json').write_text(json.dumps(build,indent=2)+'\n')
    return rom,build

def run(cumulative=False):
    global OUT
    import tools.verify_player_status_prototype as status
    mgba.log.silence()
    if cumulative:
        OUT=ROOT/'build/english/player-effect-validation'
        rom=(ROOT/'build/english/torneko-2-english.gba').read_bytes()
        build=json.loads((ROOT/'build/english/build.json').read_text())
        require(digest(rom)==build['output_sha256'],'Cumulative effect ROM differs')
    else:rom,build=candidate()
    prior=status.OUT
    try: status.OUT=OUT; fixture=status.ready(rom,build)
    finally: status.OUT=prior
    rows={r['table_offset']:r for r in build['player_effects']['entries']}; results=[]
    for source,entry,returned,queue,gear,result in CASES:
        row=rows[source]
        for label,name in player_layout_cases():
            case=f'{source:03x}-{label}'; print('Player effect',case,flush=True)
            with Session(rom,OUT/case) as game:
                game.restore(fixture);m=game.core.memory
                for i,v in enumerate(name.ljust(16,b'\0')):m.u8[HERO+i]=v
                address=0x0200DF28;old=bytes(m[address:address+120]);item=bytearray(old)
                mapping=bytes(m[0x020013D0:0x020014D0]);struct.pack_into('<I',item,0,0xC8000000)
                item[8]=mapping.index(176);item[4]=item[5]=1;item[24:]=bytes(96)
                for i,v in enumerate(item):m.u8[address+i]=v
                type_address=0x02003BAC+176*20;type_before=m.u32[type_address]
                m.u32[type_address]=type_before|0x40000000
                overrides=[];entered=[];finished=[];formats=[];checks=[];pending=None
                def register(reg,value):
                    require(game.core._core.writeRegister(game.core._core,reg,ffi.new('uint32_t*',value)),
                            'Controlled effect register failed')
                def callback(event):
                    nonlocal pending
                    a,r=event['address'],event['registers']
                    if a==0x0800B6E0 and not entered:
                        entered.append(event);actor=m.u32[0x02001624]
                        if entry==0xB450:
                            overrides.append({'address':actor+0xAA,'before':m.u8[actor+0xAA],'after':0})
                            m.u8[actor+0xAA]=0
                        if gear:
                            ga,value=gear
                            overrides.append({'address':ga,'before':m.u32[ga],'after':value})
                            m.u32[ga]=value
                        if entry!=0xB6E0:register(b'pc',0x08000000+entry)
                    if entered and a in (0x0800B468,0x0800B67C) and result is not None:
                        overrides.append({'pc':a,'register':'r0','before':r[0],'after':result})
                        register(b'r0',result)
                    if a in (0x08000FB8,0x0805CF54) and r[1]==row['offset']+0x08000000:
                        require(r[0]==r[13], 'Effect destination is not native stack buffer')
                        expected=materialize(bytes.fromhex(row['encoded_hex']),[r[2]],m)
                        require(len(expected)<=row['maximum_bytes']<=256,'Effect buffer bound differs')
                        pending=(r[14]&~1,r[0],expected,bytes(m[r[0]+256:r[0]+272]),r[4:12],r[13])
                        checks.append(CombatCheck(game,expected[:-1],0x08000000+queue,256,pending[3]))
                    if pending and a==pending[0]:
                        _,dest,expected,guard,regs,sp=pending
                        require(bytes(m[dest:dest+len(expected)])==expected,'Effect output differs')
                        require(bytes(m[dest+256:dest+272])==guard and r[4:12]==regs and r[13]==sp,
                                'Effect formatter ABI/guard differs')
                        formats.append({'id':row['id'],'bytes':len(expected),'hex':expected.hex(),
                                        'capacity':256,'abi_and_guard_preserved':True});pending=None
                    if a==0x0801588C and r[14]==0x08000000+queue and not checks:
                        require(source==0x7A0 and r[0]==row['offset']+0x08000000,
                                'Unexpected direct effect queue')
                        checks.append(CombatCheck(game,bytes.fromhex(row['encoded_hex'])[:-1],
                                      r[14],256,bytes(m[r[0]+256:r[0]+272])))
                    for check in checks:check.callback(event)
                    if entered and a==0x08000000+returned:
                        require(r[4:12]==entered[0]['registers'][4:12]
                                and r[13]==entered[0]['registers'][13]
                                and r[0]==entered[0]['registers'][14], 'Effect consumer return ABI differs')
                        finished.append(event['frame'])
                addresses={0x0800B6E0,0x0800B468,0x0800B67C,0x08000FB8,0x0805CF54,
                           0x0800B486,0x0800B4A0,0x08015860,0x0800B718,0x0800B80A,
                           0x0801588C,0x080158CE,0x08001BC4,0x08001C14,0x08001C68,
                           0x08000000+queue-1,0x08000000+returned}
                with Debugger(game,callback,max_events=70000) as debug:
                    for a in addresses:debug.breakpoint(a)
                    game.press('B',hold=8,wait=30);game.press('A',wait=30);game.press('A',wait=30)
                    actions=[]
                    for i in range(7):
                        action=m.u16[0x0200CDD0+i*2]
                        if not action:break
                        actions.append(action)
                    require(13 in actions,'Native Drink action absent')
                    for _ in range(actions.index(13)):game.press('DOWN',wait=20)
                    game.press('A',wait=0)
                    for _ in range(240):
                        if finished and checks and checks[0].complete and checks[0].returned:break
                        game.frames(1)
                    game.capture('effect')
                require(len(entered)==len(finished)==len(checks)==1 and pending is None
                        and len(formats)==(0 if source==0x7A0 else 1)
                        and checks[0].complete and checks[0].returned and checks[0].queued['one_line'],
                        f'Effect not complete: {case}, entry={len(entered)}, end={len(finished)}, formats={len(formats)}, checks={len(checks)}')
                require(game.snapshot().battery==fixture.battery,'Effect probe wrote save')
                results.append({'case':case,'id':row['id'],'player_hex':name.hex(),'native_consumer':entry,
                                'controlled_dispatch':{'from':0x0800B6E0,'to':0x08000000+entry},
                                'controlled_item':{'address':address,'before':old.hex(),'after':item.hex()},
                                'controlled_type':{'address':type_address,'before':type_before,'after':type_before|0x40000000},
                                'controlled_branches':overrides,'formats':formats,'queue':checks[0].queued,
                                'glyphs':len(checks[0].draws),'consumer_abi_preserved':True,'inputs':game.inputs})
    report={'passed':True,'rom_sha256':digest(rom),'cases':results,
            'scope':'Thirteen audited player-only source reads, three maximum-name cases each. Native Drink supplies an authentic call stack; explicitly controlled function dispatch, gear words and helper results select native effect branches. Checks exact 256-byte output guards, formatter/consumer ABI, native queue and one-line pixels. Direct immutable no-format text is separately identified. Does not prove ordinary acquisition, natural resistance or gameplay outcome equivalence.'}
    (OUT/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Player effects:',len(results),'one-line controlled native cases passed')

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--cumulative',action='store_true');run(parser.parse_args().cumulative)
