"""Player-only sleep/immobility/poison branches and native strength-loss bounds."""
import argparse,json,struct
import mgba.log
from tools.rom import ROOT,digest,require
from tools.emulator import Session,Debugger,ffi
from tools.player_condition_text import add_conditions
from tools.dialogue_checks import player_layout_cases
from tools.name_entry import HERO
from tools.verify_service_ui import materialize
from tools.verify_combat_prototype import CombatCheck

OUT=ROOT/'build/player-condition-prototype'

def candidate():
    import tools.build_english as english
    prior=english.add_combat;conditions=None
    def add(build):
        nonlocal conditions
        result=prior(build);conditions=add_conditions(build);return result
    try:english.add_combat=add;rom,build=english.build_rom(include_story=False,include_extra_consumers=False)
    finally:english.add_combat=prior
    build['player_conditions']=conditions;build['reviewed_resource_counts']['player_conditions']=len(conditions['entries'])
    build['total_reviewed_inserted_resources']+=len(conditions['entries'])
    build['scope']='Separate player-condition prototype on the current early-text baseline; no cumulative acceptance.'
    OUT.mkdir(parents=True,exist_ok=True);(OUT/'game.gba').write_bytes(rom)
    (OUT/'build.json').write_text(json.dumps(build,indent=2)+'\n');return rom,build

def run(cumulative=False):
    global OUT
    import tools.verify_player_status_prototype as status
    mgba.log.silence()
    if cumulative:
        OUT=ROOT/'build/english/player-condition-validation'
        rom=(ROOT/'build/english/torneko-2-english.gba').read_bytes()
        build=json.loads((ROOT/'build/english/build.json').read_text())
        require(digest(rom)==build['output_sha256'],'Cumulative player-condition ROM differs')
    else:rom,build=candidate()
    prior=status.OUT
    try:status.OUT=OUT;fixture=status.ready(rom,build)
    finally:status.OUT=prior
    targets={r['offset']+0x08000000:r for r in build['player_conditions']['entries']}
    cases=[{'name':'sleep','entry':0xB374,'end':0xB3BC,'sources':[0xF0],'sleep':0},
           {'name':'sleep-refusal','entry':0xB374,'end':0xB3BC,'sources':[0x11C],'sleep':1},
           {'name':'wide-awake','entry':0xB3C4,'end':0xB3EE,'sources':[0x4A8]},
           {'name':'immobile','entry':0xB3F8,'end':0xB44E,'sources':[0x1F0],'resistant':0},
           {'name':'immediate-recovery','entry':0xB3F8,'end':0xB44E,'sources':[0x1F0,0x88C],'resistant':1}]
    for strength,severity in [(1,1),(32767,1),(1,2),(2,2),(3,2),(32767,2),(3,3)]:
        cases.append({'name':f'poison-{strength}-{severity}','entry':0xB240,'end':0xB368,
                      'sources':[0xDC],'strength':strength,'severity':severity,'mode':'loss'})
    for mode,source in [('floor',0x204),('actor-immunity',0x2FC),('gear',0x298)]:
        cases.append({'name':'poison-'+mode,'entry':0xB240,'end':0xB368,'sources':[source],
                      'strength':32767,'severity':1,'mode':mode})
    results=[]
    for config in cases:
        for label,name in player_layout_cases():
            case=config['name']+'-'+label;print('Player condition',case,flush=True)
            with Session(rom,OUT/case) as game:
                game.restore(fixture);m=game.core.memory
                for i,v in enumerate(name.ljust(16,b'\0')):m.u8[HERO+i]=v
                address=0x0200DF28;old=bytes(m[address:address+120]);item=bytearray(old)
                struct.pack_into('<I',item,0,0xC8000000);item[8]=bytes(m[0x020013D0:0x020014D0]).index(176)
                item[4]=item[5]=1;item[24:]=bytes(96)
                for i,v in enumerate(item):m.u8[address+i]=v
                type_address=0x02003BAC+176*20;type_before=m.u32[type_address];m.u32[type_address]=type_before|0x40000000
                entries=[];ends=[];overrides=[];formats=[];checks=[];pending=None
                def register(reg,value):
                    require(game.core._core.writeRegister(game.core._core,reg,ffi.new('uint32_t*',value)),
                            'Condition register override failed')
                def memory(address,value,size):
                    view={1:m.u8,2:m.u16,4:m.u32}[size]
                    overrides.append({'address':address,'bytes':size,'before':view[address],'after':value});view[address]=value
                def callback(event):
                    nonlocal pending
                    a,r=event['address'],event['registers']
                    if a==0x0800B6E0 and not entries:
                        entries.append(event);actor=m.u32[0x02001624]
                        if 'resistant' in config:memory(actor+0xB2,config['resistant'],1)
                        if config['entry']==0xB240:
                            flags=m.u32[actor+8]&~0x40000000
                            if config['mode']=='actor-immunity':flags|=0x40000000
                            memory(actor+8,flags,4);memory(actor+0x76,config['strength'],2)
                            memory(0x020081D4,0x200 if config['mode']=='gear' else 0,4)
                            for reg,value in ((b'r0',actor),(b'r1',config['severity']),(b'r2',int(config['mode']=='gear'))):register(reg,value)
                        register(b'pc',0x08000000+config['entry'])
                    if entries and a==0x0800B386 and 'sleep' in config:
                        overrides.append({'pc':a,'register':'r0','before':r[0],'after':config['sleep']});register(b'r0',config['sleep'])
                    if entries and a==0x0800B256 and config['entry']==0xB240:
                        value=101 if config['mode']=='floor' else 0
                        overrides.append({'pc':a,'register':'r0','before':r[0],'after':value});register(b'r0',value)
                    if a==0x08000FB8 and r[1] in targets:
                        row=targets[r[1]];index=len(formats)
                        require(pending is None and index<len(config['sources']) and row['table_offset']==config['sources'][index],
                                'Unexpected condition message/sequence')
                        require(r[0]==r[13] and r[14] in (0x08015861,0x0800B2D9,0x0800B35B),'Unowned condition formatter')
                        if row['numeric_bound']:
                            expected_loss=min(config['strength'],1 if config['severity']<=1 else 3)
                            require(r[3]==expected_loss and 1<=r[3]<=3,'Native poison amount differs')
                        expected=materialize(bytes.fromhex(row['encoded_hex']),[r[2],r[3]],m)
                        require(len(expected)<=row['maximum_bytes']<=256,'Condition expansion exceeds bound')
                        pending=(r[14]&~1,r[0],expected,bytes(m[r[0]+256:r[0]+272]),r[4:12],r[13],row)
                        queue=0x08015869 if r[14]==0x08015861 else 0x0800B2E1 if r[14]==0x0800B2D9 else 0x0800B363
                        require(not checks or checks[-1].complete and checks[-1].returned,'Previous condition queue unfinished')
                        checks.append(CombatCheck(game,expected[:-1],queue,256,pending[3]))
                    if pending and a==pending[0]:
                        _,dest,expected,guard,regs,sp,row=pending
                        require(bytes(m[dest:dest+len(expected)])==expected and bytes(m[dest+256:dest+272])==guard,
                                'Condition formatter output/guard differs')
                        require(r[4:12]==regs and r[13]==sp,'Condition formatter ABI differs')
                        formats.append({'id':row['id'],'table_offset':row['table_offset'],'bytes':len(expected),
                                        'hex':expected.hex(),'capacity':256,'abi_and_guard_preserved':True});pending=None
                    if checks and not (checks[-1].complete and checks[-1].returned):checks[-1].callback(event)
                    if entries and a==0x08000000+config['end']:
                        require(r[4:12]==entries[0]['registers'][4:12] and r[13]==entries[0]['registers'][13]
                                and r[0]==entries[0]['registers'][14],'Condition consumer ABI differs')
                        actor=m.u32[0x02001624]
                        if config['entry']==0xB240:
                            wanted=max(0,config['strength']-(1 if config['severity']<=1 else 3)) if config['mode']=='loss' else config['strength']
                            require(m.u16[actor+0x76]==wanted,'Native strength result differs')
                        if config['entry']==0xB3C4:require(m.u8[actor+0xA4]==99,'Native wakefulness timer differs')
                        ends.append({'frame':event['frame'],'strength':m.u16[actor+0x76],'wakefulness':m.u8[actor+0xA4]})
                addresses={0x0800B6E0,0x0800B386,0x0800B256,0x08000FB8,0x08015860,0x0800B2D8,0x0800B35A,
                           0x0801588C,0x080158CE,0x08001BC4,0x08001C14,0x08001C68,
                           0x08015868,0x0800B2E0,0x0800B362,0x08000000+config['end']}
                with Debugger(game,callback,max_events=100000) as debug:
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
                    for _ in range(300):
                        if ends and checks and all(c.complete and c.returned for c in checks):break
                        game.frames(1)
                    game.capture('condition')
                require(len(entries)==len(ends)==1 and pending is None
                        and len(formats)==len(checks)==len(config['sources'])
                        and all(c.complete and c.returned and c.queued['one_line'] for c in checks),'Condition did not finish on one line')
                require(game.snapshot().battery==fixture.battery,'Condition probe wrote battery')
                results.append({'case':case,'configuration':config,'player_hex':name.hex(),
                                'controlled_dispatch':{'from':0x0800B6E0,'to':0x08000000+config['entry']},
                                'controlled_item':{'address':address,'before':old.hex(),'after':item.hex()},
                                'controlled_type':{'address':type_address,'before':type_before,'after':type_before|0x40000000},
                                'controlled_branches':overrides,'formats':formats,'queues':[c.queued for c in checks],
                                'glyphs':sum(len(c.draws) for c in checks),'consumer_result':ends[0],'inputs':game.inputs})
    report={'passed':True,'rom_sha256':digest(rom),'cases':results,
            'scope':'Nine private player conditions through 45 controlled native cases. Native Drink call stack, explicit effect dispatch/branch/status/strength inputs. Three player names; strength1/2/3/32767 and severity1/2/3 prove one-digit 1..3 loss with native zero clamp; immunity preserves strength. Exact bytes/256-byte guards, formatter/consumer/queue ABI and one-line pixels pass. Native outcome fields checked only for these explicit inputs. Ordinary acquisition and other shared consumers remain separate.'}
    (OUT/'report.json').write_text(json.dumps(report,indent=2)+'\n');print('Player conditions:',len(results),'native cases passed')

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--cumulative',action='store_true')
    run(parser.parse_args().cumulative)
