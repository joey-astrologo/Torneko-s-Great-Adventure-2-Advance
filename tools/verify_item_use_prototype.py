"""Native item-use consumer: conditional one-line joins and widest field fallbacks."""
import argparse,json,struct
import mgba.log
from tools.rom import ROOT,digest,require
from tools.emulator import Session,Debugger,ffi
from tools.item_use_text import add_item_use
from tools.compact_font import encode
from tools.dialogue_checks import player_layout_cases,rendered_codes
from tools.name_entry import HERO
from tools.verify_service_ui import materialize,cstring
from tools.verify_combat_prototype import CombatCheck

OUT=ROOT/'build/item-use-prototype'

def message_lines(raw):
    """Split opcode 0D, preserving parameters and complete two-byte glyphs."""
    lines=[bytearray()];i=0
    while i<len(raw):
        c=raw[i]
        length=2 if c==3 or 0x81<=c<=0x9F or c>=0xE0 else 1
        if c==13:lines.append(bytearray())
        else:lines[-1].extend(raw[i:i+length])
        i+=length
    return [bytes(line) for line in lines]

class ItemUseCheck(CombatCheck):
    def callback(self,event):
        a,r=event['address'],event['registers'];m=self.game.core.memory
        if a==0x080158CE and self.queue_abi and self.queued is None:
            require(m.u32[r[13]+12]==self.queue_return,'Item-use queue owner differs')
            # r1=1 may call the native clear routine; saved LR identifies the
            # caller. Colour parameters are not line-break opcodes.
            parts=message_lines(self.expected_payload)
            expected=b''.join(parts) if sum(self.width(p) for p in parts)<=216 else self.expected_payload
            raw=cstring(m,r[6]);require(raw==expected,'Item-use joined bytes/controls differ')
            require(len(raw)+1<=256 and bytes(m[r[6]+256:r[6]+272])==self.guard,'Item-use queue guard changed')
            parts=message_lines(raw);widths=[self.width(p) for p in parts]
            require(max(widths)<=216,'Item-use fallback width exceeds budget')
            self.queued={'hex':raw.hex(),'line_widths':widths,'one_line':len(parts)==1,'bytes':len(raw)+1}
            self.expected=rendered_codes(raw+b'\0');self.window=0x02000000
        super().callback(event)

def candidate():
    import tools.build_english as english
    prior=english.add_combat;use=None
    def add(build):
        nonlocal use
        result=prior(build);use=add_item_use(build);return result
    try:english.add_combat=add;rom,build=english.build_rom(include_story=False,include_extra_consumers=False)
    finally:english.add_combat=prior
    build['item_use']=use;build['reviewed_resource_counts']['item_use']=len(use['entries'])
    build['total_reviewed_inserted_resources']+=len(use['entries'])
    build['scope']='Separate item-use announcement prototype; no cumulative acceptance.'
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'game.gba').write_bytes(rom);(OUT/'build.json').write_text(json.dumps(build,indent=2)+'\n')
    return rom,build

def run(cumulative=False):
    global OUT
    import tools.verify_player_status_prototype as status
    mgba.log.silence()
    if cumulative:
        OUT=ROOT/'build/english/item-use-validation'
        rom=(ROOT/'build/english/torneko-2-english.gba').read_bytes()
        build=json.loads((ROOT/'build/english/build.json').read_text())
        require(digest(rom)==build['output_sha256'],'Cumulative item-use ROM differs')
    else:rom,build=candidate()
    prior=status.OUT
    try:status.OUT=OUT;fixture=status.ready(rom,build)
    finally:status.OUT=prior
    results=[];queue_return=build['item_use']['queue_return']
    for row in build['item_use']['entries']:
        for label,name in player_layout_cases():
            for item_label,item_text in [('native-name',None),('maximum-width','W'*27),('maximum-bytes','i'*31),
                                         ('colour-parameter-5',b'\x03\x05'+encode('Herb')[:-1]+b'\x05\0')]:
                case=row['id']+'-'+label+'-'+item_label;print('Item use',case,flush=True)
                with Session(rom,OUT/case) as game:
                    game.restore(fixture);m=game.core.memory
                    for i,v in enumerate(name.ljust(16,b'\0')):m.u8[HERO+i]=v
                    address=0x0200DF28;old=bytes(m[address:address+120]);item=bytearray(old)
                    struct.pack_into('<I',item,0,0xC8000000);item[8]=bytes(m[0x020013D0:0x020014D0]).index(176)
                    item[4]=item[5]=1;item[24:]=bytes(96)
                    for i,v in enumerate(item):m.u8[address+i]=v
                    type_address=0x02003BAC+176*20;type_before=m.u32[type_address]
                    m.u32[type_address]=type_before|0x40000000
                    overrides=[];formats=[];checks=[];pending=None
                    def callback(event):
                        nonlocal pending
                        a,r=event['address'],event['registers']
                        if a==0x08025834 and r[4] not in row['categories']:
                            category=row['categories'][0]
                            overrides.append({'pc':a,'register':'r4','before':r[4],'after':category})
                            require(game.core._core.writeRegister(game.core._core,b'r4',ffi.new('uint32_t*',category)),
                                    'Item-use category override failed')
                        if a==0x08000FB8 and r[14]==0x0802585B:
                            require(r[1]==row['offset']+0x08000000 and r[0]==r[13]
                                    and r[3]==r[13]+256,'Item-use format/name ownership differs')
                            if item_text is not None:
                                payload=item_text if isinstance(item_text,bytes) else encode(item_text)
                                require(len(payload)<=64,'Controlled item field exceeds bound')
                                before=bytes(m[r[3]:r[3]+64]);after=payload.ljust(64,b'\0')
                                for i,v in enumerate(after):m.u8[r[3]+i]=v
                                overrides.append({'address':r[3],'before':before.hex(),'after':after.hex(),'kind':item_label})
                            expected=materialize(bytes.fromhex(row['encoded_hex']),[r[2],r[3]],m)
                            require(len(expected)<=row['maximum_formatted_bytes']<=256,'Item-use expansion exceeds buffer')
                            pending=(r[0],expected,bytes(m[r[0]+256:r[0]+320]),r[4:12],r[13])
                            checks.append(ItemUseCheck(game,expected[:-1],queue_return,256,pending[2][:16]))
                        if a==0x0802585A:
                            require(pending is not None,'Item-use formatter entry missing')
                            dest,expected,guard,regs,sp=pending
                            require(bytes(m[dest:dest+len(expected)])==expected
                                    and bytes(m[dest+256:dest+320])==guard,'Item-use output/name guard differs')
                            require(r[4:12]==regs and r[13]==sp,'Item-use formatter ABI differs')
                            formats.append({'bytes':len(expected),'expected_hex':expected.hex(),
                                            'capacity':256,'name_buffer_bytes':64,'abi_and_guard_preserved':True})
                        for check in checks:check.callback(event)
                        if a==0x08025864 and pending:
                            dest,_,guard,_,_=pending
                            require(bytes(m[dest+256:dest+320])==guard,'Item-use join changed its item argument')
                            require(r[4:12]==pending[3] and r[13]==pending[4] and r[0]==1,
                                    'Item-use joining helper changed saved registers/SP')
                    with Debugger(game,callback,max_events=70000) as debug:
                        for a in (0x08025834,0x08000FB8,0x0802585A,0x08025864,queue_return&~1,0x0801588C,0x080158CE,
                                  0x08001BC4,0x08001C14,0x08001C68):debug.breakpoint(a)
                        game.press('B',hold=8,wait=30);game.press('A',wait=30);game.press('A',wait=30)
                        actions=[]
                        for i in range(7):
                            action=m.u16[0x0200CDD0+i*2]
                            if not action:break
                            actions.append(action)
                        require(13 in actions,'Native Drink action absent')
                        for _ in range(actions.index(13)):game.press('DOWN',wait=20)
                        game.press('A',wait=0)
                        for _ in range(180):
                            if checks and checks[0].complete and checks[0].returned:break
                            game.frames(1)
                        game.capture('announcement')
                    require(len(checks)==len(formats)==1 and checks[0].complete and checks[0].returned,
                            f'Item-use announcement did not finish: formats={len(formats)}, checks={len(checks)}, states={[(c.complete,c.returned,c.queued,len(c.draws)) for c in checks]}')
                    if item_label=='maximum-width':require(not checks[0].queued['one_line'],'Widest item should retain fallback')
                    require(game.snapshot().battery==fixture.battery,'Item-use probe wrote battery')
                    results.append({'case':case,'id':row['id'],'player_hex':name.hex(),'item_field':item_label,
                                    'controlled_item':{'address':address,'before':old.hex(),'after':item.hex()},
                                    'controlled_type':{'address':type_address,'before':type_before,'after':type_before|0x40000000},
                                    'controlled_fields':overrides,'formats':formats,'queue':checks[0].queued,
                                    'glyphs':len(checks[0].draws),'inputs':game.inputs})
    report={'passed':True,'rom_sha256':digest(rom),'cases':results,
            'scope':'Native Drink dispatch with controlled category selection for the four other announcement verbs. Three player names and native/162px/63-byte item fields per format. Exact output, separate item-buffer guards, queue ABI/pixels and conditional join/fallback checked. Synthetic field bounds are not custom-name or inscription acceptance. Other actions and ordinary acquisition remain separate.'}
    (OUT/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Item-use announcements:',len(results),'cases,',sum(c['queue']['one_line'] for c in results),'one line')

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--cumulative',action='store_true');run(parser.parse_args().cumulative)
