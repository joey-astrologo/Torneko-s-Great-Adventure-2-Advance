"""Native pot transfer helpers, bounded bulk selections and two-field withdrawals."""
import argparse,json,struct
from collections import Counter
import mgba.log
from tools.rom import ROOT,digest,require
from tools.emulator import Session,Debugger,ffi
from tools.container_text import add_containers
from tools.compact_font import encode
from tools.verify_service_ui import materialize
from tools.verify_inventory_action_prototype import ActionCheck

OUT=ROOT/'build/container-prototype'
QUEUES={0x25188:0x2524F,0x2521E:0x2524F,0x25242:0x2524F,0x2526E:0x25277,0x252D6:0x253B7,0x253AE:0x253B7,
        0x25356:0x2535F,0x25444:0x2544D,0x25522:0x25551,0x25548:0x25551,0x25570:0x25579,
        0x255D8:0x255E1,0x25630:0x25639}
POOL=[1,2,3,4,5,6,7,8,9,10,11,12,14,15,16,17,18,19,20]

def candidate():
    import tools.build_english as english
    prior=english.add_combat;containers=None
    def add(build):
        nonlocal containers
        result=prior(build);containers=add_containers(build);return result
    try:english.add_combat=add;rom,build=english.build_rom(include_story=False,include_extra_consumers=False)
    finally:english.add_combat=prior
    build['containers']=containers;count=len(containers['entries'])+len(containers['labels'])
    build['reviewed_resource_counts']['containers']=count;build['total_reviewed_inserted_resources']+=count
    build['scope']='Separate pot-transfer prototype with single/bulk success and floor prefix.'
    OUT.mkdir(parents=True,exist_ok=True);(OUT/'game.gba').write_bytes(rom)
    (OUT/'build.json').write_text(json.dumps(build,indent=2)+'\n');return rom,build

def run(cumulative=False):
    global OUT
    import tools.verify_player_status_prototype as status
    mgba.log.silence()
    if cumulative:
        OUT=ROOT/'build/english/container-validation';rom=(ROOT/'build/english/torneko-2-english.gba').read_bytes()
        build=json.loads((ROOT/'build/english/build.json').read_text());require(digest(rom)==build['output_sha256'],'Container ROM differs')
    else:rom,build=candidate()
    prior=status.OUT
    try:status.OUT=OUT;fixture=status.ready(rom,build)
    finally:status.OUT=prior
    targets={r['offset']+0x08000000:r for r in build['containers']['entries']}
    labels={r['offset']+0x08000000:r for r in build['containers']['labels']}
    configs=[{'name':'put-one','mode':'put','source':0xB4,'inside':0,'inventory':2,'success':1},
             {'name':'put-floor-one','mode':'put','source':0xB4,'inside':0,'inventory':2,'success':1},{'name':'take-one','mode':'take','source':0xC0,'inside':1,'inventory':2,'success':1},
             {'name':'take-full','mode':'take','source':0xBC,'inside':1,'inventory':20,'success':0},
             {'name':'take-bulk-two','mode':'take','source':0xA2C,'inside':2,'inventory':2,'success':2,'select':[0,1]},
             {'name':'take-bulk-seven','mode':'take','source':0xA2C,'inside':7,'inventory':2,'success':7,'select':list(range(7))},
             {'name':'take-bulk-partial','mode':'take','source':0xA30,'inside':7,'inventory':17,'success':3,'select':list(range(7))},
             {'name':'take-bulk-full','mode':'take','source':0xBC,'inside':2,'inventory':20,'success':0,'select':[0,1]},
             {'name':'put-bulk-two','mode':'put','source':0xA24,'inside':0,'inventory':3,'success':2,'select':[1,2]},
             {'name':'put-bulk-seven','mode':'put','source':0xA24,'inside':0,'inventory':8,'success':7,'select':list(range(1,8))},
             {'name':'put-bulk-partial','mode':'put','source':0xA28,'inside':0,'inventory':20,'success':7,'select':list(range(1,20))+[99]},
             {'name':'put-bulk-none','mode':'put','source':0xB0,'inside':7,'inventory':3,'success':0,'select':[1,2]},
             {'name':'put-nested','mode':'put','source':0xB8,'inside':0,'inventory':2,'success':0},
             {'name':'put-cursed','mode':'put','source':0x80,'inside':0,'inventory':2,'success':0},
             {'name':'put-full','mode':'put','source':0xB0,'inside':7,'inventory':2,'success':0},
             {'name':'put-rejected','mode':'put','source':0xB8,'inside':0,'inventory':2,'success':0},
             {'name':'put-floor-denied','mode':'put','source':0x150,'inside':0,'inventory':2,'success':0},
             {'name':'put-floor-stuck','mode':'put','source':0x1EC,'inside':0,'inventory':2,'success':0}]
    results=[]
    for config in configs:
        source=config['source'];bulk=source in (0xA24,0xA28,0xA2C,0xA30)
        fields=([('pot-kind',None,1),('jewel-box-kind',None,0)] if bulk else [('native',None,None)] if source==0xBC else
                [('native',None,None),('maximum-width',(encode('W'*27),encode('M'*27)),None),
                 ('maximum-bytes',(encode('i'*31),encode('l'*31)),None),
                 ('coloured',(b'\x03\x05'+encode('Pot')[:-1]+b'\x05\0',b'\x03\x05'+encode('Item')[:-1]+b'\x05\0'),None)])
        for field,payloads,kind_index in fields:
            case=config['name']+'-'+field;print('Container',case,flush=True)
            with Session(rom,OUT/case) as game:
                game.restore(fixture);m=game.core.memory;overrides=[];floor=[];floor_cells=[];entries=[];ends=[];formats=[];checks=[];pending=None
                p=0x0200DF28;mapping=bytes(m[0x020013D0:0x020014D0]);actor=m.u32[0x02001624];floor_pointer=None
                iterator=[];before_inventory=None;before_contents=None;before_floor=None;kind_reads=[]
                entry=0x08025108 if config['mode']=='put' else 0x08025474
                end=0x08025286 if config['mode']=='put' else 0x08025582
                def write(address,data):
                    overrides.append({'address':address,'before':bytes(m[address:address+len(data)]).hex(),'after':data.hex()})
                    for i,v in enumerate(data):m.u8[address+i]=v
                def reg(event,name,value):
                    index=15 if name=='pc' else int(name[1:]);value&=0xFFFFFFFF
                    overrides.append({'pc':event['address'],'register':name,'before':event['registers'][index],'after':value})
                    require(game.core._core.writeRegister(game.core._core,name.encode(),ffi.new('uint32_t*',value)),'Container override failed')
                def item(ident,amount=1):
                    value=bytearray(120);struct.pack_into('<I',value,0,0xC8000000);value[4]=amount;value[5]=1;value[8]=mapping.index(ident);return value
                def inventory():return Counter(m.u8[p+i*120+8] for i in range(20) if m.u32[p+i*120]&0x80000000)
                def contents():return Counter(m.u8[p+24+i*12+8] for i in range(7) if m.u32[p+24+i*12]&0x80000000)
                write(p,item(1))
                def callback(event):
                    nonlocal pending,before_inventory,before_contents,before_floor
                    a,r=event['address'],event['registers']
                    if a==0x08024F12:floor.append(m.u32[r[0]+16]);floor_cells.append(r[0])
                    if a==entry:
                        require(not entries,'Container entered twice');entries.append(event)
                        if config['name'].startswith('put-floor'):
                            write(r[0]+4,b'\x63')
                            if config['name'].endswith('denied'):write(actor+8,struct.pack('<I',m.u32[actor+8]|0x1000000))
                            elif config['name'].endswith('stuck'):write(floor_pointer,struct.pack('<I',m.u32[floor_pointer]|0x10000000))
                        before_inventory=inventory();before_contents=contents();before_floor=bytes(m[floor_pointer:floor_pointer+120])
                    if entries and 'select' in config:
                        if a==(0x08025116 if config['mode']=='put' else 0x08025482):reg(event,'r0',len(config['select']))
                        if a==(0x080251BE if config['mode']=='put' else 0x080254D6):
                            index=len(iterator);value=config['select'][index] if index<len(config['select']) else -1
                            require(index<=len(config['select']),'Container iterator failed to stop');iterator.append(value);reg(event,'r0',value)
                    if entries and a==0x08025428 and config['name']=='put-rejected':
                        reg(event,'r0',0);reg(event,'pc',0x0802542C)
                    if entries and a==0x080250EE and kind_index is not None:reg(event,'r0',167 if kind_index==0 else 154)
                    if entries and a==0x08025102:
                        require(r[0] in labels and labels[r[0]]['index']==kind_index,'Container generic-kind helper differs')
                        kind_reads.append({'pointer':r[0],'index':kind_index,'frame':event['frame']})
                    if a==0x08000FB8 and r[1] in targets:
                        row=targets[r[1]];ret=r[14]&~1
                        require(row['table_offset']==source and ret-0x08000000 in QUEUES and not formats,
                                f'Unowned container format: got{row["id"]} at{ret:x}, expected{source:x}')
                        expected_dest=r[13]+(4 if ret-0x08000000 in (0x25188,0x2521E,0x25242,0x2526E,0x25522,0x25548,0x25570) else 0)
                        require(r[0]==expected_dest,'Container output frame differs')
                        arguments=[r[2],r[3],m.u32[r[13]]]
                        roles=row['field_roles'];native_arguments=[]
                        for role,value in zip(roles,arguments):
                            if role in ('total','count'):
                                wanted=len(config.get('select',[])) if role=='total' else config['success']
                                require(value==wanted and 1<=value<=20,'Container native numeric result differs')
                            elif role=='floor':
                                expected_prefix=next(x for x in build['containers']['entries'] if x['table_offset']==0x38)
                                require(value==(expected_prefix['offset']+0x08000000 if config['name']=='put-floor-one' else 0x0806B9AC),
                                        'Container floor-prefix selection differs')
                            elif role=='kind':require(value in labels and labels[value]['index']==kind_index,'Container summary kind differs')
                            else:
                                require(r[0]+192<=value<=r[0]+256,'Container item-field ownership differs')
                                native_arguments.append({'role':role,'address':value,'before_hex':bytes(m[value:value+64]).hex()})
                                if payloads is not None:write(value,payloads[0 if role=='pot' else 1].ljust(64,b'\0'))
                                native_arguments[-1]['expected_after_hex']=bytes(m[value:value+64]).hex()
                        expected=materialize(bytes.fromhex(row['encoded_hex']),arguments,m)
                        require(len(expected)<=row['maximum_bytes']<=192,'Container expansion exceeds192-byte output')
                        pending=(ret,r[0],expected,bytes(m[r[0]+192:r[0]+208]),r[4:12],r[13],row,native_arguments,arguments)
                        checks.append(ActionCheck(game,expected[:-1],0x08000000+QUEUES[ret-0x08000000],192,pending[3]))
                    if pending and a==pending[0]:
                        _,dest,expected,guard,regs,sp,row,native_arguments,arguments=pending
                        require(bytes(m[dest:dest+len(expected)])==expected and bytes(m[dest+192:dest+208])==guard,'Container output/guard differs')
                        require(r[4:12]==regs and r[13]==sp,'Container formatter ABI differs')
                        require(all(bytes(m[f['address']:f['address']+64]).hex()==f['expected_after_hex'] for f in native_arguments),
                                'Container formatter changed a separate64-byte name field')
                        formats.append({'id':row['id'],'table_offset':source,'hex':expected.hex(),'bytes':len(expected),'capacity':192,
                                        'native_arguments':native_arguments,'printf_arguments':arguments});pending=None
                    if checks and not (checks[-1].complete and checks[-1].returned):checks[-1].callback(event)
                    if entries and a==end:
                        initial=entries[0]['registers'];require(r[4:12]==initial[4:12] and r[13]==initial[13] and r[0]==initial[14],
                                                              'Container consumer ABI differs')
                        require(sum(inventory().values())==sum(before_inventory.values())+(config['success'] if config['mode']=='take' else 0 if config['name']=='put-floor-one' else -config['success']),
                                'Container carried count differs')
                        require(sum(contents().values())==config['inside']+(-config['success'] if config['mode']=='take' else config['success']),
                                'Container contents count differs')
                        floor_extra=Counter({before_floor[8]:1}) if config['name']=='put-floor-one' else Counter()
                        require(inventory()+contents()==before_inventory+before_contents+floor_extra,'Container transfer lost/duplicated an item identity')
                        if config['name']=='put-floor-one':require(m.u32[floor_cells[0]+16]==0,'Put did not remove the floor allocation')
                        else:require(bytes(m[floor_pointer:floor_pointer+120])==before_floor,'Container floor refusal changed item')
                        ends.append({'frame':event['frame'],'inventory_before':dict(before_inventory),'inventory_after':dict(inventory()),
                                     'contents_before':dict(before_contents),'contents_after':dict(contents())})
                addresses={0x08024F12,entry,end,0x08025116,0x08025482,0x080251BE,0x080254D6,0x08025428,
                           0x080250EE,0x08025102,0x08000FB8,0x0801588C,0x080158CE,0x08001BC4,0x08001C14,0x08001C68}
                addresses|={0x08000000+n for n in QUEUES}|{(0x08000000+n)&~1 for n in QUEUES.values()}
                def select(action):
                    actions=[]
                    for i in range(7):
                        n=m.u16[0x0200CDD0+2*i]
                        if not n:break
                        actions.append(n)
                    require(action in actions,f'Container setup action{action} absent: {actions}')
                    for _ in range(actions.index(action)):game.press('DOWN',wait=20)
                with Debugger(game,callback,max_events=180000) as debug:
                    for a in addresses:debug.breakpoint(a)
                    game.press('B',hold=8,wait=30);game.press('A',wait=30);game.press('A',wait=30);select(7)
                    game.press('A',wait=180);require(len(floor)==1,'Container setup drop failed');floor_pointer=floor[0]
                    for i in range(20):write(p+i*120,bytes(120))
                    pot=item(154,7)
                    for i in range(config['inside']):pot[24+i*12:36+i*12]=item(POOL[i])[:12]
                    write(p,pot)
                    for i in range(1,config['inventory']):write(p+i*120,item(POOL[i-1]))
                    if config['name']=='put-nested':write(p+120,item(154,3))
                    if config['name']=='put-cursed':write(p+120,struct.pack('<I',0xCC800000))
                    for ident in POOL+[154,167]:
                        address=0x02003BAC+20*ident;write(address,struct.pack('<I',m.u32[address]|0x40000000))
                    game.press('B',hold=8,wait=60);game.press('A',wait=60);game.press('A',wait=60)
                    if config['mode']=='put':
                        select(15);game.press('A',wait=60);game.press('DOWN',wait=30)
                        game.capture('selection');game.press('A',wait=0)
                    else:
                        select(42);game.press('A',wait=60);game.press('A',wait=60);select(16)
                        game.capture('selection');game.press('A',wait=0)
                    for _ in range(900):
                        if ends and checks and all(c.complete and c.returned for c in checks):break
                        game.frames(1)
                    game.capture('result')
                require(len(entries)==len(ends)==len(formats)==len(checks)==1 and pending is None
                        and checks[0].complete and checks[0].returned,
                        f'Container incomplete: entries={len(entries)} ends={len(ends)} formats={formats}')
                if 'select' in config:require(iterator==config['select']+[-1],'Container iteration differs')
                if bulk:require(len(kind_reads)==1 and checks[0].queued['one_line'],'Bulk summary not one bounded line')
                require(game.snapshot().battery==fixture.battery,'Container probe wrote battery')
                results.append({'case':case,'id':formats[0]['id'],'configuration':config,'controlled_overrides':overrides,'formats':formats,
                                'kind_reads':kind_reads,'queue':checks[0].queued,'glyphs':len(checks[0].draws),
                                'consumer_result':ends[0],'inputs':game.inputs})
    report={'passed':True,'rom_sha256':digest(rom),'cases':results,
            'scope':'Native Drop establishes floor ownership, then ordinary pot View/Take or Put in selection reaches native transfer consumers. Explicit contained/carried/floor/state fields and bulk selector returns exercise bounded transfers; generic-kind selection is controlled independently. Exact192-byte outputs,64-byte name fields, numbers/kinds, glyphs/ABI, conserved item identities/counts and battery checked. Ordinary bulk selection and special jewel-box mechanics, custom names/inscriptions and other shared consumers remain separate.'}
    (OUT/'report.json').write_text(json.dumps(report,indent=2)+'\n');print('Containers:',len(results),'cases passed')

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--cumulative',action='store_true');run(parser.parse_args().cumulative)
