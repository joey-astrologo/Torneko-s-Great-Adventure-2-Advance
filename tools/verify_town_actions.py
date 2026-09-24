"""Town View/Trash/Info and discard confirmation through a controlled invocation."""
import argparse,json,struct
import mgba.log
from tools.rom import ROOT,digest,require
from tools.emulator import Session,Debugger,ffi
from tools.bakery_playtest import service_ready
from tools.town_item_text import add_town_actions
from tools.dialogue_checks import TextChecks
from tools.audit_menu_layouts import Observer,parent_image
from tools.verify_service_ui import materialize
from tools.compact_font import encode

OUT=ROOT/'build/town-actions-prototype'

def candidate():
    import tools.build_english as english
    prior=english.add_combat;resource=None
    def add(build):
        nonlocal resource
        result=prior(build);resource=add_town_actions(build);return result
    try:english.add_combat=add;rom,build=english.build_rom(include_story=False,include_extra_consumers=False)
    finally:english.add_combat=prior
    build['town_actions']=resource;build['reviewed_resource_counts']['town_actions']=6;build['total_reviewed_inserted_resources']+=6
    OUT.mkdir(parents=True,exist_ok=True);(OUT/'game.gba').write_bytes(rom)
    (OUT/'build.json').write_text(json.dumps(build,indent=2)+'\n');return rom,build

def run(cumulative=False):
    global OUT
    mgba.log.silence()
    if cumulative:
        OUT=ROOT/'build/english/town-action-validation';rom=(ROOT/'build/english/torneko-2-english.gba').read_bytes()
        build=json.loads((ROOT/'build/english/build.json').read_text());require(digest(rom)==build['output_sha256'],'Town action ROM differs')
    else:rom,build=candidate()
    fixture=service_ready(rom,OUT);resource=build['town_actions'];results=[]
    cases=[('empty',None,0),('cancel',1,0),('info',1,0),('trash-no',1,0),('trash-yes',1,0),
           ('pot-empty-no',154,0),('pot-empty-yes',154,0),('pot-filled-no',154,2),('pot-filled-yes',154,2),('view',154,2)]
    for name,ident,contained in cases:
        print('Town actions:',name,flush=True)
        with Session(rom,OUT/name) as game:
            game.restore(fixture);m=game.core.memory;slot=0x0200DF28;overrides=[];entries=[];returns=[];formats=[];pending=None
            choices=[];choice_active=False
            resources={r['offset']+0x08000000:r|{'layout':{'pages':[[r['english']]]}} for r in resource['entries']}
            choice=next(r for r in build['dialogue']['entries'] if r['id']=='rom.0006309c')
            resources[choice['rom_offset']+0x08000000]=choice
            checks=TextChecks(game,resources);observer=Observer(game);mapping=bytes(m[0x020013D0:0x020014D0])
            def write(address,data):
                overrides.append({'address':address,'before':bytes(m[address:address+len(data)]).hex(),'after':data.hex()})
                for i,b in enumerate(data):m.u8[address+i]=b
            def item(code,amount=1):
                row=bytearray(120);struct.pack_into('<I',row,0,0xC8000000);row[4]=amount;row[5]=1;row[8]=mapping.index(code);return row
            write(slot,bytes(20*120))
            if ident is not None:
                row=item(ident,7 if ident==154 else 1)
                for i in range(contained):row[24+12*i:36+12*i]=item(i+1)[:12]
                write(slot,row)
                for code in {ident,1,2}:
                    address=0x02003BAC+20*code;write(address,struct.pack('<I',m.u32[address]|0x40000000))
            before=bytes(m[slot:slot+20*120]);gold=m.u32[m.u32[0x02001624]+0x60]
            def callback(event):
                nonlocal pending,choice_active
                a,r=event['address'],event['registers']
                if a==0x0801DFAC:
                    require(not entries and r[0]==0x020141AC,'Town controlled caller differs')
                    entries.append(event|{'stack_guard':bytes(m[r[13]:r[13]+32]).hex(),'redirected_pc':0x0801E490})
                    require(game.core._core.writeRegister(game.core._core,b'pc',ffi.new('uint32_t*',0x0801E490)),'Town redirect failed')
                if a==0x08000FB8 and r[14] in (0x0801E53B,0x0801E589):
                    labels=['View','Trash','Info'] if r[14]==0x0801E53B else ['Trash','Info']
                    expected=b'\r'.join(encode(s)[:-1] for s in labels)+b'\0'
                    args=r[2:4]+[m.u32[r[13]]]
                    template=bytes(m[r[1]:r[1]+12]);template=template[:template.index(0)+1]
                    require(materialize(template,args,m)==expected and r[0]==r[13]+4,'Town menu argument roles/bytes differ')
                    pending=(r[14]&~1,r[0],expected,bytes(m[r[0]+256:r[0]+272]),r[4:12],r[13],labels)
                if pending and a==pending[0]:
                    _,dest,expected,guard,regs,sp,labels=pending
                    require(bytes(m[dest:dest+len(expected)])==expected and bytes(m[dest+256:dest+272])==guard
                            and r[4:12]==regs and r[13]==sp,'Town menu formatter damaged output/guard/ABI')
                    checks.resources[dest]={'id':'town-item-actions','encoded_hex':expected.hex(),'layout':{'pages':[labels]}}
                    formats.append({'hex':expected.hex(),'bytes':len(expected),'capacity':256,'labels':labels,'registers_and_guard_preserved':True});pending=None
                if a==0x08015CE8:choice_active=True
                if a==0x08015E28 and choice_active:choices.append(r[0]);choice_active=False
                if a==0x0801E75A:
                    initial=entries[0]['registers']
                    require(r[4:12]==initial[4:12] and r[13]==initial[13] and r[0]==initial[14]
                            and bytes(m[r[13]:r[13]+32]).hex()==entries[0]['stack_guard'],'Town consumer entry/return ABI differs')
                    returns.append(event)
                observer.callback(event);checks.callback(event)
            with Debugger(game,callback,max_events=180000) as debug:
                for address in set(checks.ADDRESSES+observer.ADDRESSES+(0x0801DFAC,0x0801E75A,0x08000FB8,0x0801E53A,0x0801E588,0x08015CE8,0x08015E28)):debug.breakpoint(address)
                game.press('A',wait=180);game.capture('inventory')
                if ident is not None:
                    parent=parent_image(game)
                    for cycle in range(3 if name=='cancel' else 1):
                        game.press('A',wait=120);game.capture(f'actions-{cycle}')
                        if name=='cancel':
                            for _ in range(2):game.press('DOWN',wait=20)
                            game.press('B',wait=120);require(parent_image(game)==parent,'Town cancellation changed parent')
                    if name=='info':
                        game.press('DOWN',wait=20);game.press('A',wait=120);game.capture('info');game.press('B',wait=120)
                    elif name=='view':
                        game.press('A',wait=120);game.capture('contents');game.press('B',wait=120)
                    elif name.endswith(('-yes','-no')):
                        if ident==154:game.press('DOWN',wait=20)
                        game.press('A',wait=120)
                        for _ in range(8):
                            if choice_active:break
                            game.press('A',wait=120)
                        require(choice_active,'Town discard confirmation absent');game.capture('confirmation')
                        game.press('A' if name.endswith('-yes') else 'B',wait=180);game.capture('result')
                    for _ in range(8):
                        if returns:break
                        game.press('A' if name.endswith('-yes') else 'B',wait=120)
                else:
                    for _ in range(8):
                        if returns:break
                        game.press('A',wait=120)
                game.capture('finished')
            require(len(entries)==len(returns)==1 and pending is None and checks.active is None,'Town action probe incomplete')
            read_ids={r['id'] for r in checks.reads};expected_message=109 if contained else 108
            if name.endswith(('-yes','-no')):
                require(next(r['id'] for r in resource['entries'] if r['index']==expected_message) in read_ids,'Wrong discard warning')
                require(choices==[1 if name.endswith('-yes') else 0],'Discard answer/result differs')
            if name=='empty' or name.endswith('-yes'):
                require(next(r['id'] for r in resource['entries'] if r['index']==59) in read_ids,'Empty inventory explanation absent')
            after=bytes(m[slot:slot+20*120])
            if name.endswith('-yes'):
                require(not m.u32[slot]&0x80000000 and not any(m.u32[slot+120*i]&0x80000000 for i in range(20)),'Discard did not remove the selected record')
            else:require(after==before,'Cancelled/non-destructive town action changed inventory')
            require(m.u32[m.u32[0x02001624]+0x60]==gold and game.snapshot().battery==fixture.battery,'Town action changed gold/battery')
            reads=[r for r in observer.reads if r['raw_hex'] in {f['hex'] for f in formats}]
            require(all(r['screen_x']==192 and r['window_width']==40 and r['initial_x']==6 for r in reads),'Town action geometry changed')
            results.append({'case':name,'controlled_overrides':overrides,'entries':entries,'returns':returns,'formats':formats,
                            'reads':checks.reads,'menu_reads':reads,'glyph_checks':checks.glyph_checks,'choices':choices,
                            'inventory_before':before.hex(),'inventory_after':after.hex(),'inputs':game.inputs})
    report={'passed':True,'rom_sha256':digest(rom),'cases':results,'scope':'Controlled bank invocation redirected to the native town inventory consumer. Explicit ordinary item, empty/filled Storage pot and empty inventory records; ordinary selection/cancel/View/Info and Trash confirmation inputs. Private source reads, original menu geometry, pixels, buffers/entry-return ABI, inventory outcomes and unchanged gold/battery. Ordinary town menu access, other consumers and custom item names remain separate.'}
    (OUT/'report.json').write_text(json.dumps(report,indent=2)+'\n');print('Town item actions:',len(results),'cases passed')

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--cumulative',action='store_true');run(parser.parse_args().cumulative)
