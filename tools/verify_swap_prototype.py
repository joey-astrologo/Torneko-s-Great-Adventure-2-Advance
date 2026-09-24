"""Native Floor/Swap: field roles, refusal paths and exchanged item identities."""
import argparse,json,struct
from collections import Counter
import mgba.log
from tools.rom import ROOT,digest,require
from tools.emulator import Session,Debugger
from tools.swap_text import add_swap
from tools.compact_font import encode
from tools.verify_service_ui import materialize
from tools.verify_inventory_action_prototype import ActionCheck

OUT=ROOT/'build/swap-prototype'
QUEUES={0x256E8:0x256F1,0x25718:0x25721,0x25766:0x2576F}

def candidate():
    import tools.build_english as english
    prior=english.add_combat;swap=None
    def add(build):
        nonlocal swap
        result=prior(build);swap=add_swap(build);return result
    try:english.add_combat=add;rom,build=english.build_rom(include_story=False,include_extra_consumers=False)
    finally:english.add_combat=prior
    build['swap']=swap;build['reviewed_resource_counts']['swap']=len(swap['entries'])
    build['total_reviewed_inserted_resources']+=len(swap['entries']);build['scope']='Separate Floor/Swap prototype; no cumulative acceptance.'
    OUT.mkdir(parents=True,exist_ok=True);(OUT/'game.gba').write_bytes(rom)
    (OUT/'build.json').write_text(json.dumps(build,indent=2)+'\n');return rom,build

def run(cumulative=False):
    global OUT
    import tools.verify_player_status_prototype as status
    mgba.log.silence()
    if cumulative:
        OUT=ROOT/'build/english/swap-validation';rom=(ROOT/'build/english/torneko-2-english.gba').read_bytes()
        build=json.loads((ROOT/'build/english/build.json').read_text());require(digest(rom)==build['output_sha256'],'Swap ROM differs')
    else:rom,build=candidate()
    prior=status.OUT
    try:status.OUT=OUT;fixture=status.ready(rom,build)
    finally:status.OUT=prior
    targets={r['offset']+0x08000000:r for r in build['swap']['entries']};results=[]
    for kind,source in [('swap',0xC4),('empty',0x8F0),('cannot-swap',0x154),('stuck',0x1EC),('cursed',0x80)]:
        for field,payloads in [('native',None),('maximum-width',(encode('W'*27),encode('M'*27))),
                               ('maximum-bytes',(encode('i'*31),encode('l'*31))),
                               ('coloured',(b'\x03\x05'+encode('Floor')[:-1]+b'\x05\0',b'\x03\x05'+encode('Pack')[:-1]+b'\x05\0'))]:
            case=kind+'-'+field;print('Swap',case,flush=True)
            with Session(rom,OUT/case) as game:
                game.restore(fixture);m=game.core.memory;overrides=[];floor=[];entries=[];ends=[];formats=[];checks=[];pending=None
                p=0x0200DF28;mapping=bytes(m[0x020013D0:0x020014D0]);actor=m.u32[0x02001624]
                floor_pointer=None;before_items=None;before_floor=None
                def write(address,data):
                    overrides.append({'address':address,'before':bytes(m[address:address+len(data)]).hex(),'after':data.hex()})
                    for i,v in enumerate(data):m.u8[address+i]=v
                def inventory():return Counter(m.u8[p+i*120+8] for i in range(20) if m.u32[p+i*120]&0x80000000)
                item=bytearray(m[p:p+120]);struct.pack_into('<I',item,0,0xC8000000)
                item[4]=item[5]=1;item[8]=mapping.index(1);item[24:]=bytes(96);write(p,item)
                def callback(event):
                    nonlocal pending,before_items,before_floor
                    a,r=event['address'],event['registers']
                    if a==0x08024F12:floor.append(m.u32[r[0]+16])
                    if a==0x08025648:
                        require(not entries,'Swap entered twice');entries.append(event)
                        if kind=='empty':
                            for i in range(20):write(p+i*120,bytes(120))
                        if kind=='cannot-swap':write(actor+8,struct.pack('<I',m.u32[actor+8]|0x1000000))
                        if kind=='stuck':write(floor_pointer,struct.pack('<I',m.u32[floor_pointer]|0x10000000))
                        if kind=='cursed':write(p,struct.pack('<I',m.u32[p]|0x4800000))
                        before_items=inventory();before_floor=bytes(m[floor_pointer:floor_pointer+120])
                    if a==0x08000FB8 and r[1] in targets:
                        row=targets[r[1]];ret=r[14]&~1
                        require(row['table_offset']==source and ret-0x08000000 in QUEUES and not formats,'Unowned swap format')
                        expected_name=r[13]+(0x178 if source==0x80 else 0x138)
                        require(r[0]==r[13]+0x78 and r[2]==expected_name,'Swap message/first field role differs')
                        if source==0xC4:require(r[3]==r[13]+0x178,'Swap second field role differs')
                        original_fields=[bytes(m[r[2]:r[2]+64])]
                        if source==0xC4:original_fields.append(bytes(m[r[3]:r[3]+64]))
                        if payloads is not None:
                            payload=payloads[1 if source==0x80 else 0];write(r[2],payload.ljust(64,b'\0'))
                            if source==0xC4:write(r[3],payloads[1].ljust(64,b'\0'))
                        expected=materialize(bytes.fromhex(row['encoded_hex']),[r[2],r[3]],m)
                        require(len(expected)<=row['maximum_bytes']<=192,'Swap exceeds192-byte output')
                        pending=(ret,r[0],expected,bytes(m[r[0]+192:r[0]+320]),r[4:12],r[13],row,original_fields)
                        checks.append(ActionCheck(game,expected[:-1],0x08000000+QUEUES[ret-0x08000000],192,pending[3][:16]))
                    if pending and a==pending[0]:
                        _,dest,expected,guard,regs,sp,row,original_fields=pending
                        require(bytes(m[dest:dest+len(expected)])==expected and bytes(m[dest+192:dest+320])==guard,'Swap output/two-name guard differs')
                        require(r[4:12]==regs and r[13]==sp,'Swap formatter ABI differs')
                        formats.append({'id':row['id'],'table_offset':source,'hex':expected.hex(),'bytes':len(expected),'capacity':192,
                                        'original_fields_hex':[f.hex() for f in original_fields]});pending=None
                    if a==0x0801588C and r[0] in targets:
                        row=targets[r[0]];require(row['table_offset']==source and source in (0x8F0,0x154)
                            and r[14]==0x080256B9,'Unowned direct swap queue')
                        checks.append(ActionCheck(game,bytes.fromhex(row['encoded_hex'])[:-1],r[14],0,b''))
                        formats.append({'id':row['id'],'table_offset':source,'immutable_rom_source':True})
                    if checks and not (checks[-1].complete and checks[-1].returned):checks[-1].callback(event)
                    if entries and a==0x080257EA:
                        initial=entries[0]['registers'];require(r[4:12]==initial[4:12] and r[13]==initial[13] and r[0]==initial[14],
                                                              'Swap consumer ABI differs')
                        wanted=before_items.copy()
                        if kind=='swap':
                            wanted[mapping.index(2)]-=1;wanted[mapping.index(1)]+=1
                            require(m.u8[floor_pointer+8]==mapping.index(2),'Wrong item left on floor')
                        else:require(bytes(m[floor_pointer:floor_pointer+120])==before_floor,'Refused swap changed floor item')
                        require(+inventory()==+wanted,'Native swapped inventory identities differ')
                        ends.append({'frame':event['frame'],'inventory_before':dict(before_items),'inventory_after':dict(inventory()),
                                     'floor_before':before_floor.hex(),'floor_after':bytes(m[floor_pointer:floor_pointer+120]).hex()})
                addresses={0x08024F12,0x08025648,0x080257EA,0x08000FB8,0x0801588C,0x080158CE,
                           0x08001BC4,0x08001C14,0x08001C68,0x080256B8}
                addresses|={0x08000000+n for n in QUEUES}|{(0x08000000+n)&~1 for n in QUEUES.values()}
                def select(action):
                    actions=[]
                    for i in range(7):
                        n=m.u16[0x0200CDD0+2*i]
                        if not n:break
                        actions.append(n)
                    require(action in actions,f'Swap setup action{action} absent: {actions}')
                    for _ in range(actions.index(action)):game.press('DOWN',wait=20)
                with Debugger(game,callback,max_events=120000) as debug:
                    for a in addresses:debug.breakpoint(a)
                    game.press('B',hold=8,wait=30);game.press('A',wait=30);game.press('A',wait=30)
                    select(7);game.press('A',wait=180);require(len(floor)==1,'Swap setup floor allocation absent');floor_pointer=floor[0]
                    carried=bytearray(item);carried[8]=mapping.index(2);write(p,carried)
                    for ident in (1,2):
                        address=0x02003BAC+20*ident;write(address,struct.pack('<I',m.u32[address]|0x40000000))
                    game.press('B',hold=8,wait=60);game.press('DOWN',wait=30);game.press('A',wait=60);select(8)
                    game.press('A',wait=120);game.capture('selection');game.press('A',wait=0)
                    for _ in range(360):
                        if ends and checks and all(c.complete and c.returned for c in checks):break
                        game.frames(1)
                    game.capture('result')
                require(len(entries)==len(ends)==len(formats)==len(checks)==1 and pending is None
                        and checks[0].complete and checks[0].returned,'Swap case incomplete')
                require(game.snapshot().battery==fixture.battery,'Swap probe wrote battery')
                results.append({'case':case,'id':formats[0]['id'],'controlled_overrides':overrides,'formats':formats,
                                'queue':checks[0].queued,'glyphs':len(checks[0].draws),'consumer_result':ends[0],'inputs':game.inputs})
    report={'passed':True,'rom_sha256':digest(rom),'cases':results,
            'scope':'Ordinary Drop/Floor/Swap/selection inputs in a disposable native checkpoint with explicit item/state/type controls. Five private sources, normal/162px/63-byte/coloured fields. First-floor and second-inventory argument roles,192-byte output/two64-byte guards, native pixels/ABI and exchanged item identities checked. Empty inventory is controlled at function entry after ordinary selection, not an ordinary empty-menu route. Other shared consumers, arbitrary states, custom names and inscriptions remain separate.'}
    (OUT/'report.json').write_text(json.dumps(report,indent=2)+'\n');print('Swap:',len(results),'cases passed')

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--cumulative',action='store_true');run(parser.parse_args().cumulative)
