"""Native pickup paths: item/gold/arrow outcomes, refusal branches and field bounds."""
import argparse,json,struct
import mgba.log
from tools.rom import ROOT,digest,require
from tools.emulator import Session,Debugger,ffi
from tools.pickup_text import add_pickup
from tools.compact_font import encode
from tools.verify_service_ui import materialize
from tools.verify_inventory_action_prototype import ActionCheck

OUT=ROOT/'build/pickup-prototype'
QUEUES={0x24B34:0x24B3D,0x24B7C:0x24B85,0x24BD2:0x24BDB,0x24CAC:0x24CB5,
        0x24D18:0x24D21,0x24DA6:0x24DAF,0x24AA8:0x24AB1}

def candidate():
    import tools.build_english as english
    prior=english.add_combat;pickup=None
    def add(build):
        nonlocal pickup
        result=prior(build);pickup=add_pickup(build);return result
    try:english.add_combat=add;rom,build=english.build_rom(include_story=False,include_extra_consumers=False)
    finally:english.add_combat=prior
    build['pickup']=pickup;build['reviewed_resource_counts']['pickup']=len(pickup['entries'])
    build['total_reviewed_inserted_resources']+=len(pickup['entries'])
    build['scope']='Separate central pickup prototype; no cumulative acceptance.'
    OUT.mkdir(parents=True,exist_ok=True);(OUT/'game.gba').write_bytes(rom)
    (OUT/'build.json').write_text(json.dumps(build,indent=2)+'\n');return rom,build

def run(cumulative=False):
    global OUT
    import tools.verify_player_status_prototype as status
    mgba.log.silence()
    if cumulative:
        OUT=ROOT/'build/english/pickup-validation';rom=(ROOT/'build/english/torneko-2-english.gba').read_bytes()
        build=json.loads((ROOT/'build/english/build.json').read_text());require(digest(rom)==build['output_sha256'],'Pickup ROM differs')
    else:rom,build=candidate()
    prior=status.OUT
    try:status.OUT=OUT;fixture=status.ready(rom,build)
    finally:status.OUT=prior
    targets={r['offset']+0x08000000:r for r in build['pickup']['entries']};results=[]
    for kind,source in [('item',0x9C),('gold',0x9C),('arrows',0x9C),('full',0x98),('full-standing',0xA0),
                        ('cannot-pick-up',0x150),('stuck',0x1EC),('standing-special',0x37C),('walk-standing',0x37C)]:
        for field,payload in [('native',None),('maximum-width',encode('W'*27)),('maximum-bytes',encode('i'*31)),
                              ('coloured',b'\x03\x05'+encode('Item')[:-1]+b'\x05\0')]:
            case=kind+'-'+field;print('Pickup',case,flush=True)
            with Session(rom,OUT/case) as game:
                game.restore(fixture);m=game.core.memory;overrides=[];floor=[];entries=[];ends=[];formats=[];checks=[];pending=None
                def write(address,data):
                    overrides.append({'address':address,'before':bytes(m[address:address+len(data)]).hex(),'after':data.hex()})
                    for i,v in enumerate(data):m.u8[address+i]=v
                def reg(event,name,value):
                    index=15 if name=='pc' else int(name[1:])
                    overrides.append({'pc':event['address'],'register':name,'before':event['registers'][index],'after':value})
                    require(game.core._core.writeRegister(game.core._core,name.encode(),ffi.new('uint32_t*',value)),'Pickup override failed')
                p=0x0200DF28;item=bytearray(m[p:p+120]);struct.pack_into('<I',item,0,0xC8000000)
                item[4]=item[5]=1;mapping=bytes(m[0x020013D0:0x020014D0]);item[8]=mapping.index(1);item[24:]=bytes(96)
                write(p,item);actor=m.u32[0x02001624];before_count=None;gold_before=None;floor_pointer=None;slot_before=None
                count=lambda:sum(bool(m.u32[p+i*120]&0x80000000) for i in range(20))
                def callback(event):
                    nonlocal pending
                    a,r=event['address'],event['registers']
                    if a==0x08024F12:floor.append(m.u32[r[0]+16])
                    if a==0x08024AD8:
                        require(not entries,'Pickup called twice');entries.append(event)
                        if kind in ('full','full-standing'):reg(event,'r1',int(kind=='full-standing'))
                        if kind=='walk-standing':reg(event,'pc',0x080249DC)
                    if entries and a==0x08024B58 and kind=='standing-special':reg(event,'r0',220)
                    if a==0x08000FB8 and r[1] in targets:
                        row=targets[r[1]];ret=r[14]&~1
                        require(row['table_offset']==source and ret-0x08000000 in QUEUES and not formats,'Unowned pickup format')
                        capacity=256 if kind=='walk-standing' else 192
                        require(r[0]==r[13] and r[2]==r[13]+capacity,'Pickup message/item ownership differs')
                        if payload is not None:write(r[2],payload.ljust(64,b'\0'))
                        expected=materialize(bytes.fromhex(row['encoded_hex']),[r[2]],m)
                        require(len(expected)<=row['maximum_bytes']<=192,'Pickup expansion exceeds192-byte output')
                        pending=(ret,r[0],expected,bytes(m[r[0]+capacity:r[0]+capacity+64]),r[4:12],r[13],row,capacity)
                        checks.append(ActionCheck(game,expected[:-1],0x08000000+QUEUES[ret-0x08000000],capacity,pending[3][:16]))
                    if pending and a==pending[0]:
                        _,dest,expected,guard,regs,sp,row,capacity=pending
                        require(bytes(m[dest:dest+len(expected)])==expected and bytes(m[dest+capacity:dest+capacity+64])==guard,'Pickup output/name guard differs')
                        require(r[4:12]==regs and r[13]==sp,'Pickup formatter ABI differs')
                        formats.append({'id':row['id'],'table_offset':source,'hex':expected.hex(),'bytes':len(expected),'capacity':capacity});pending=None
                    if a==0x0801588C and r[0] in targets:
                        row=targets[r[0]];require(source==row['table_offset']==0x98 and r[14]==0x08024D35,'Unowned direct pickup')
                        checks.append(ActionCheck(game,bytes.fromhex(row['encoded_hex'])[:-1],r[14],0,b''))
                        formats.append({'id':row['id'],'table_offset':source,'immutable_rom_source':True})
                    if checks and not (checks[-1].complete and checks[-1].returned):checks[-1].callback(event)
                    if entries and a==(0x08024AD6 if kind=='walk-standing' else 0x08024E6A):
                        initial=entries[0]['registers'];require(r[4:12]==initial[4:12] and r[13]==initial[13]
                            and r[1]==initial[14] and r[0]==1,'Pickup consumer ABI/result differs')
                        require(count()==before_count+(kind=='item'),'Native pickup inventory count differs')
                        require(m.u32[actor+0x60]==gold_before+(123 if kind=='gold' else 0),'Native pickup gold differs')
                        if kind=='arrows':require(m.u8[p+4]==15,'Native arrow merge amount differs')
                        if kind not in ('item','gold','arrows'):
                            require(bytes(m[p:p+20*120])==slot_before,'Refused pickup changed inventory')
                        ends.append({'frame':event['frame'],'inventory_count_before':before_count,'inventory_count_after':count(),
                                     'gold_before':gold_before,'gold_after':m.u32[actor+0x60],
                                     'arrow_count_after':m.u8[p+4] if kind=='arrows' else None})
                addresses={0x08024F12,0x08024AD8,0x08024B58,0x08024E6A,0x08024AD6,0x08000FB8,0x0801588C,0x080158CE,
                           0x08001BC4,0x08001C14,0x08001C68,0x08024D34}
                addresses|={0x08000000+n for n in QUEUES}|{(0x08000000+n)&~1 for n in QUEUES.values()}
                def select(action):
                    actions=[]
                    for i in range(7):
                        n=m.u16[0x0200CDD0+2*i]
                        if not n:break
                        actions.append(n)
                    require(action in actions,f'Native pickup setup action{action} absent: {actions}')
                    for _ in range(actions.index(action)):game.press('DOWN',wait=20)
                with Debugger(game,callback,max_events=120000) as debug:
                    for a in addresses:debug.breakpoint(a)
                    game.press('B',hold=8,wait=30);game.press('A',wait=30);game.press('A',wait=30)
                    select(7);game.press('A',wait=180);require(len(floor)==1,'Native setup drop did not create floor item')
                    floor_pointer=floor[0]
                    game.press('B',hold=8,wait=60);game.press('DOWN',wait=30);game.press('A',wait=60);select(18)
                    data=bytearray(m[floor_pointer:floor_pointer+120])
                    if kind=='gold':data[8]=mapping.index(212);struct.pack_into('<h',data,4,123)
                    if kind=='arrows':
                        data[8]=mapping.index(78);data[4]=5
                        carried=bytearray(item);carried[8]=mapping.index(78);carried[4]=10;write(p,carried)
                    if kind in ('stuck','standing-special'):struct.pack_into('<I',data,0,struct.unpack_from('<I',data)[0]|0x10000000)
                    write(floor_pointer,data)
                    if kind.startswith('full'):
                        for i in range(20):write(p+i*120,item)
                    if kind=='cannot-pick-up':write(actor+8,struct.pack('<I',m.u32[actor+8]|0x1000000))
                    if kind=='walk-standing':
                        for offset in (0xBF,0xAA,0x9A,0x9C):write(actor+offset,b'\0')
                        write(0x02005664,struct.pack('<ii',-1,-1));write(0x0200567D,b'\1')
                    for ident in (1,78,212):
                        address=0x02003BAC+20*ident;write(address,struct.pack('<I',m.u32[address]|0x40000000))
                    before_count=count();gold_before=m.u32[actor+0x60];slot_before=bytes(m[p:p+20*120])
                    game.press('A',wait=0)
                    for _ in range(360):
                        if ends and checks and all(c.complete and c.returned for c in checks):break
                        game.frames(1)
                    game.capture('result')
                require(len(entries)==len(ends)==len(formats)==len(checks)==1 and pending is None
                        and checks[0].complete and checks[0].returned,'Pickup case incomplete')
                require(game.snapshot().battery==fixture.battery,'Pickup probe wrote battery')
                results.append({'case':case,'id':formats[0]['id'],'controlled_overrides':overrides,'formats':formats,
                                'queue':checks[0].queued,'glyphs':len(checks[0].draws),'consumer_result':ends[0],'inputs':game.inputs})
    report={'passed':True,'rom_sha256':digest(rom),'cases':results,
            'scope':'Native Drop establishes floor ownership; ordinary Floor/Take menu inputs reach central pickup. Controlled floor/inventory/type/actor/selector fields exercise six sources and gold/arrow/full/refusal branches, with192-byte messages and64-byte fields. Exact bytes/guards, native glyph pixels, consumer/queue ABI and item/gold/arrow outcomes pass. The automatic-walk standing branch is reached by explicit dispatch with recorded option/last-position/status fields and uses its native256-byte output. Ordinary walking progression, custom names/inscriptions, arbitrary special definitions and other shared consumers remain separate.'}
    (OUT/'report.json').write_text(json.dumps(report,indent=2)+'\n');print('Pickup:',len(results),'cases passed')

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--cumulative',action='store_true');run(parser.parse_args().cumulative)
