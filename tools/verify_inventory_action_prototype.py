"""Controlled native equipment/removal/drop consumers, fields, outcomes and pixels."""
import argparse,json,struct
import mgba.log
from tools.rom import ROOT,digest,require
from tools.emulator import Session,Debugger,ffi
from tools.inventory_action_text import add_actions,CONTROL
from tools.compact_font import encode
from tools.dialogue_checks import rendered_codes
from tools.verify_service_ui import materialize,cstring
from tools.verify_combat_prototype import CombatCheck

OUT=ROOT/'build/inventory-action-prototype'
FORMAT_QUEUES={0x24762:0x2476B,0x247A8:0x247B1,0x24832:0x2483B,0x24864:0x2486D,
               0x24988:0x249CF,0x249C6:0x249CF,0x24EA4:0x24EAD,0x24EE4:0x24F5B,0x24F52:0x24F5B}

class ActionCheck(CombatCheck):
    def callback(self,event):
        a,r=event['address'],event['registers'];m=self.game.core.memory
        if a==0x080158CE and self.queue_abi and self.queued is None:
            require(m.u32[r[13]+12]==self.queue_return,'Inventory queue owner differs')
            raw=cstring(m,r[6]);require(raw==self.expected_payload,'Inventory queued bytes differ')
            if self.capacity:
                require(len(raw)+1<=self.capacity and bytes(m[r[6]+self.capacity:r[6]+self.capacity+16])==self.guard,
                        'Inventory192-byte guard differs')
            if CONTROL in raw:
                parts=raw.split(CONTROL);require(len(parts)==2,'Unowned conditional break count')
                widths=[self.width(p) for p in parts]
                if sum(widths)<=215:widths=[sum(widths)]
            else:widths=[self.width(p) for p in raw.split(b'\r')]
            require(max(widths)<=216,'Inventory message exceeds safe width')
            self.queued={'hex':raw.hex(),'line_widths':widths,'one_line':len(widths)==1,'bytes':len(raw)+1}
            self.expected=rendered_codes(raw.replace(CONTROL,b'')+b'\0');self.window=0x02000000
        super().callback(event)
        if self.draws:require(self.draws[-1]['x']+self.draws[-1]['advance']<=216,'Inventory glyph exceeds216px')

def candidate():
    import tools.build_english as english
    prior=english.add_combat;actions=None
    def add(build):
        nonlocal actions
        result=prior(build);actions=add_actions(build);return result
    try:english.add_combat=add;rom,build=english.build_rom(include_story=False,include_extra_consumers=False)
    finally:english.add_combat=prior
    build['inventory_actions']=actions;build['reviewed_resource_counts']['inventory_actions']=len(actions['entries'])
    build['total_reviewed_inserted_resources']+=len(actions['entries'])
    build['scope']='Separate equipment/removal/drop prototype; no cumulative acceptance.'
    OUT.mkdir(parents=True,exist_ok=True);(OUT/'game.gba').write_bytes(rom)
    (OUT/'build.json').write_text(json.dumps(build,indent=2)+'\n');return rom,build

def run(cumulative=False):
    global OUT
    import tools.verify_player_status_prototype as status
    mgba.log.silence()
    if cumulative:
        OUT=ROOT/'build/english/inventory-action-validation'
        rom=(ROOT/'build/english/torneko-2-english.gba').read_bytes()
        build=json.loads((ROOT/'build/english/build.json').read_text())
        require(digest(rom)==build['output_sha256'],'Cumulative inventory-action ROM differs')
    else:rom,build=candidate()
    prior=status.OUT
    try:status.OUT=OUT;fixture=status.ready(rom,build)
    finally:status.OUT=prior
    targets={r['offset']+0x08000000:r for r in build['inventory_actions']['entries']}
    configs=[('equip',5,[0x88]),('equip-cursed',5,[0x88,0x84]),('equip-blocked',5,[0x80]),
             ('equip-invalid',5,[0x7C]),('equip-ground',5,[0x78]),('remove',6,[0x94]),
             ('remove-cursed',6,[0x80]),('drop',7,[0xAC]),('drop-cursed',7,[0x80]),
             ('drop-no-floor',7,[0xA8]),('drop-force',7,[0xA14])]
    results=[]
    for kind,action,sources in configs:
        for field,payload in [('native',None),('maximum-width',encode('W'*27)),('maximum-bytes',encode('i'*31)),
                              ('coloured',b'\x03\x05'+encode('Sword')[:-1]+b'\x05\0')]:
            case=kind+'-'+field;print('Inventory action',case,flush=True)
            with Session(rom,OUT/case) as game:
                game.restore(fixture);m=game.core.memory;overrides=[]
                def write(address,data):
                    overrides.append({'address':address,'before':bytes(m[address:address+len(data)]).hex(),'after':data.hex()})
                    for i,v in enumerate(data):m.u8[address+i]=v
                def reg(event,name,value):
                    index=15 if name=='pc' else int(name[1:]);overrides.append({'pc':event['address'],'register':name,'before':event['registers'][index],'after':value})
                    require(game.core._core.writeRegister(game.core._core,name.encode(),ffi.new('uint32_t*',value)),
                            'Inventory controlled register failed')
                for i in range(20):
                    p=0x0200DF28+i*120
                    if m.u32[p]&0x800000:write(p,struct.pack('<I',m.u32[p]&~0x800000))
                p=0x0200DF28;item=bytearray(m[p:p+120]);flags=0xC8000000
                if action==6 or kind=='drop-cursed':flags|=0x800000
                if kind in ('equip-cursed','remove-cursed','drop-cursed'):flags|=0x4000000
                struct.pack_into('<I',item,0,flags);item[4]=item[5]=1;item[8]=bytes(m[0x020013D0:0x020014D0]).index(1);item[24:]=bytes(96)
                write(p,item);type_address=0x02003BAC+20;write(type_address,struct.pack('<I',m.u32[type_address]|0x40000000))
                if kind=='equip-blocked':
                    second=bytearray(item);struct.pack_into('<I',second,0,0xCC800000);write(p+120,second)
                entry=0x080246FC if action==5 else 0x08024918 if action==6 else 0x08024E70
                end=0x08024906 if action==5 else 0x080249D4 if action==6 else 0x08024F7C
                entries=[];ends=[];formats=[];checks=[];pending=None;floor=[]
                inventory_count=lambda:sum(bool(m.u32[0x0200DF28+i*120]&0x80000000) for i in range(20))
                original_count=inventory_count()
                def callback(event):
                    nonlocal pending
                    a,r=event['address'],event['registers']
                    if a==entry:entries.append(event)
                    if entries and a==0x08024710 and kind=='equip-ground':reg(event,'r0',50)
                    if entries and a==0x08024746 and kind=='equip-invalid':reg(event,'r5',0)
                    if entries and a==0x08024ED4 and kind=='drop-no-floor':reg(event,'r0',0)
                    if entries and a==0x08024EFE and kind=='drop-force':
                        # Skip allocation entirely: overriding its result after success would
                        # leave a controlled duplicate on the floor and obscure the refusal.
                        reg(event,'r0',0);reg(event,'pc',0x08024F02)
                    if entries and a==0x08024F12:
                        pointer=m.u32[r[0]+16];floor.append({'address':pointer,'item_hex':bytes(m[pointer:pointer+120]).hex()})
                    if a==0x08000FB8 and r[1] in targets:
                        row=targets[r[1]];ret=r[14]&~1;require(ret-0x08000000 in FORMAT_QUEUES,'Unowned inventory formatter')
                        require(pending is None and row['table_offset']==sources[len(formats)],'Unexpected inventory message sequence')
                        if payload is not None and b'%s' in bytes.fromhex(row['encoded_hex']):
                            require(len(payload)<=64 and r[0]+192<=r[2]<r[0]+320,'Inventory item field ownership differs')
                            write(r[2],payload.ljust(64,b'\0'))
                        expected=materialize(bytes.fromhex(row['encoded_hex']),[r[2]],m)
                        require(len(expected)<=row['maximum_bytes']<=192,'Inventory expansion exceeds192-byte bound')
                        pending=(ret,r[0],expected,bytes(m[r[0]+192:r[0]+208]),r[4:12],r[13],row)
                        require(not checks or checks[-1].complete and checks[-1].returned,'Previous inventory message unfinished')
                        checks.append(ActionCheck(game,expected[:-1],0x08000000+FORMAT_QUEUES[ret-0x08000000],192,pending[3]))
                    if pending and a==pending[0]:
                        _,dest,expected,guard,regs,sp,row=pending
                        require(bytes(m[dest:dest+len(expected)])==expected and bytes(m[dest+192:dest+208])==guard,
                                'Inventory formatter output/guard differs')
                        require(r[4:12]==regs and r[13]==sp,'Inventory formatter ABI differs')
                        formats.append({'id':row['id'],'table_offset':row['table_offset'],'hex':expected.hex(),'bytes':len(expected),
                                        'capacity':192,'guard_and_abi_preserved':True});pending=None
                    if a==0x0801588C and r[0] in targets:
                        row=targets[r[0]];require(row['table_offset']==sources[len(formats)],'Unexpected direct inventory source')
                        require(r[14] in (0x0802476B,0x08024F73),'Unowned direct inventory queue')
                        checks.append(ActionCheck(game,bytes.fromhex(row['encoded_hex'])[:-1],r[14],0,b''))
                        formats.append({'id':row['id'],'table_offset':row['table_offset'],'immutable_rom_source':True})
                    if checks and not (checks[-1].complete and checks[-1].returned):checks[-1].callback(event)
                    if entries and a==end:
                        start=entries[0]['registers'];require(r[4:12]==start[4:12] and r[13]==start[13]
                            and r[1 if action==5 else 0]==start[14],'Inventory consumer ABI differs')
                        if kind.startswith('equip'):
                            require(bool(m.u32[p]&0x800000)==(kind in ('equip','equip-cursed')),'Native equip result differs')
                        if action==6:require(bool(m.u32[p]&0x800000)==(kind=='remove-cursed'),'Native remove result differs')
                        if action==7:
                            require(inventory_count()==original_count-(kind=='drop'),'Native drop inventory count differs')
                            if kind=='drop':
                                require(len(floor)==1 and m.u8[floor[0]['address']+8]==item[8],'Native floor item differs')
                        ends.append({'frame':event['frame'],'first_slot_flags':m.u32[p],
                                     'inventory_count_before':original_count,'inventory_count_after':inventory_count(),'floor':floor})
                addresses={entry,end,0x08024710,0x08024746,0x08024ED4,0x08024EFE,0x08024F12,0x08000FB8,
                           0x0801588C,0x080158CE,0x08001BC4,0x08001C14,0x08001C68}
                addresses|={0x08000000+n for n in FORMAT_QUEUES}|{(0x08000000+n)&~1 for n in FORMAT_QUEUES.values()}|{0x08024F72}
                with Debugger(game,callback,max_events=100000) as debug:
                    for a in addresses:debug.breakpoint(a)
                    game.press('B',hold=8,wait=30);game.press('A',wait=30);game.press('A',wait=30)
                    actions=[]
                    for i in range(7):
                        value=m.u16[0x0200CDD0+i*2]
                        if not value:break
                        actions.append(value)
                    require(action in actions,f'Native action{action} absent: {actions}')
                    for _ in range(actions.index(action)):game.press('DOWN',wait=20)
                    game.press('A',wait=0)
                    for _ in range(360):
                        if ends and checks and all(c.complete and c.returned for c in checks):break
                        game.frames(1)
                    game.capture('result')
                require(len(entries)==len(ends)==1 and pending is None and len(formats)==len(checks)==len(sources)
                        and all(c.complete and c.returned for c in checks),
                        f'Inventory consumer incomplete: {len(entries)}/{len(ends)}, {formats}, {[(c.complete,c.returned) for c in checks]}')
                require(game.snapshot().battery==fixture.battery,'Inventory probe wrote battery')
                results.append({'case':case,'sources':sources,'controlled_overrides':overrides,'formats':formats,
                                'queues':[c.queued for c in checks],'glyphs':sum(len(c.draws) for c in checks),
                                'consumer_result':ends[0],'inputs':game.inputs})
    report={'passed':True,'rom_sha256':digest(rom),'cases':results,
            'scope':'Controlled item/state/branch/field inputs with ordinary native action-menu selection. Nine sources,192-byte outputs,64-byte fields,native queue/glyph pixels and consumer ABI; equip/remove flags checked. Ground-removal fragment090 remains original. Custom names/inscriptions and other shared consumers are excluded.'}
    (OUT/'report.json').write_text(json.dumps(report,indent=2)+'\n');print('Inventory actions:',len(results),'cases passed')

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--cumulative',action='store_true')
    run(parser.parse_args().cumulative)
