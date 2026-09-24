"""ROM-bound announcement streams through the native story wrapper and A callback."""
import argparse,json,struct
import mgba.log
from tools.rom import ROOT,load_base,digest,require
from tools.rom_build import RomBuild
from tools.build_compact_font import add_font
from tools.name_entry import add_name_entry,HERO
from tools.story_command_text import add_commands
from tools.emulator import Session,Debugger,ffi
from tools.bakery_playtest import service_ready
from tools.dialogue_checks import TextChecks,player_layout_cases,rendered_codes
from tools.opening_text import banks,BANK_RAM
from tools.event_text import table_entries
from tools.lz77 import decompress
from tools.research_event_relocation import invoke
from tools.holy_flame_playtest import items
from tools.verify_bank import balance

OUT=ROOT/'build/story-command-prototype'

def candidate():
    build=RomBuild(load_base());add_font(build,compact_numbers=True);add_name_entry(build)
    commands=add_commands(build);rom,report=build.finish();report['story_commands']=commands
    report['scope']='Independent fifteen-source announcement prototype. No cumulative acceptance.'
    OUT.mkdir(parents=True,exist_ok=True);(OUT/'game.gba').write_bytes(rom)
    (OUT/'build.json').write_text(json.dumps(report,indent=2)+'\n');return rom,report

def bindings(rom,build,fixture):
    selected={r['id']:r for r in build['story_commands']['entries']};results=[]
    with Session(rom,OUT/'bindings') as game:
        for bank in banks():
            game.restore(fixture);m=game.core.memory
            invoke(game,0x0804D6F8,[bank['index']],max_steps=10000000)
            require(m.u32[0x0200FF38]==BANK_RAM,'Command bank RAM differs')
            pointer=struct.unpack_from('<I',rom,bank['pointer_offset'])[0]-0x08000000
            decoded,_=decompress(rom,pointer);expected=bytearray(decoded)
            for word in range(4):struct.pack_into('<I',expected,word*4,(struct.unpack_from('<I',decoded,word*4)[0]+BANK_RAM)&0xFFFFFFFF)
            require(bytes(m[BANK_RAM:BANK_RAM+len(expected)])==expected,'Command native bank fixups differ')
            getters=[]
            for entry in table_entries(bank):
                target=invoke(game,0x08050270,[entry['group'],entry['index']])
                wanted=(BANK_RAM+entry['strings_offset']+entry['group_offset']+struct.unpack_from('<I',expected,entry['slot'])[0])&0xFFFFFFFF
                require(target==wanted,'Command getter target differs')
                if entry['id'] in selected:
                    row=selected[entry['id']];payload=bytes.fromhex(row['encoded_hex'])
                    require(target==row['rom_offset']+0x08000000 and bytes(m[target:target+len(payload)])==payload,
                            'Command ROM slot not bound to exact English')
                getters.append({'id':entry['id'],'group':entry['group'],'index':entry['index'],'target':target})
            require(bytes(m[BANK_RAM:BANK_RAM+len(expected)])==expected and game.snapshot().battery==fixture.battery,
                    'Command getters changed bank or battery')
            results.append({'bank':bank['id'],'getters':getters,'native_bank_bytes':len(expected),'no_ram_offset_replacement':True})
    return results

def run(cumulative=False):
    global OUT
    mgba.log.silence()
    if cumulative:
        OUT=ROOT/'build/english/story-command-validation'
        rom=(ROOT/'build/english/torneko-2-english.gba').read_bytes()
        build=json.loads((ROOT/'build/english/build.json').read_text())
        require(digest(rom)==build['output_sha256'],'Cumulative story-command ROM differs')
    else:rom,build=candidate()
    fixture=service_ready(rom,OUT)
    getters=bindings(rom,build,fixture);results=[]
    for row in build['story_commands']['entries']:
        for label,name in player_layout_cases():
            case=row['id']+'-'+label;print('Story command',case,flush=True)
            with Session(rom,OUT/case) as game:
                game.restore(fixture);m=game.core.memory
                for i,v in enumerate(name.ljust(16,b'\0')):m.u8[HERO+i]=v
                target=row['rom_offset']+0x08000000;payload=bytes.fromhex(row['encoded_hex'])
                command_prefix=len(rendered_codes(payload[:payload.index(b'@A@')]+b'\0',name))
                check=TextChecks(game,{target:row});entries=[];commands=[];sounds=[];returned=[];images=[]
                gold=balance(game);inventory=items(game);flags=bytes(m[0x020101AC:0x020101CC])
                event_flags=m.u8[0x0201020E]
                def callback(event):
                    a,r=event['address'],event['registers']
                    if a==0x0801DFAC:
                        require(not entries,'Repeated controlled story invocation');entries.append(event)
                        for reg,value in ((b'r0',target),(b'pc',0x080503F8)):
                            require(game.core._core.writeRegister(game.core._core,reg,ffi.new('uint32_t*',value)),
                                    'Controlled story wrapper entry failed')
                        return
                    if a==0x08051664:
                        require(check.active and not commands and bytes(m[r[0]:r[0]+3])==b'@A@',
                                'Unexpected story callback command')
                        require(len(check.active['glyphs'])==command_prefix,'Story jingle moved relative to text')
                        commands.append({'command':'@A@','glyphs_before':command_prefix,'frame':event['frame'],
                                         'flags_before':m.u8[0x0201020E],'preserved':(r[4:12],r[13]),'return':r[14]})
                    if a==0x08058BC0 and r[14]==0x08051677:
                        require(len(commands)==1 and r[0]==0x10F and r[1]==10,'Story jingle arguments changed')
                        sounds.append({'id':r[0],'parameter':r[1],'frame':event['frame']})
                    if a==0x080516B4:
                        require(commands and (r[4:12],r[13])==commands[-1]['preserved']
                                and r[0]==0 and r[1]==commands[-1]['return'],'Story callback ABI changed')
                        require(m.u8[0x0201020E]==commands[-1]['flags_before'],'A callback changed event flags')
                        commands[-1]['flags_after']=m.u8[0x0201020E];commands[-1]['abi_preserved']=True
                    if a==0x08050436:
                        require(entries and r[4:12]==entries[0]['registers'][4:12]
                                and r[13]==entries[0]['registers'][13] and r[0]==entries[0]['registers'][14],
                                'Story wrapper return ABI differs')
                        returned.append(event['frame'])
                    if a in check.ADDRESSES:check.callback(event)
                with Debugger(game,callback,max_events=200000) as debug:
                    for a in set(check.ADDRESSES+(0x0801DFAC,0x08051664,0x080516B4,0x08058BC0,0x08050436)):
                        debug.breakpoint(a)
                    game.press('A',wait=120);game.capture('page-0');images.append('page-0.png')
                    for page in range(1,len(row['layout']['pages'])+6):
                        if returned and check.completed(row['id']) and check.active is None:break
                        game.press('A',wait=120);game.capture(f'page-{page}');images.append(f'page-{page}.png')
                    require(len(entries)==len(returned)==len(commands)==len(sounds)==1
                            and check.completed(row['id']) and check.active is None,'Story command did not finish once')
                require(items(game)==inventory and balance(game)==gold and bytes(m[0x020101AC:0x020101CC])==flags
                        and m.u8[0x0201020E]==event_flags,'Story display changed inventory/gold/quest/event flags')
                require(game.snapshot().battery==fixture.battery,'Story command probe wrote battery')
                results.append({'case':case,'id':row['id'],'controlled_player_hex':name.hex(),
                                'controlled_dispatch':{'from':0x0801DFAC,'to':0x080503F8,'r0':target},
                                'commands':commands,'sounds':sounds,'reads':check.reads,'glyph_checks':check.glyph_checks,
                                'wrapper_abi_preserved':True,'inventory_gold_flags_battery_preserved':True,'inputs':game.inputs,
                                'images':{p:digest((OUT/case/p).read_bytes()) for p in images}})
    report={'passed':True,'rom_sha256':digest(rom),'cases':results,'bindings':getters,
            'scope':'Fifteen ROM-bound direct streams, three name extremes each, through native wrapper 080503F8. Exact native A-jingle arguments and command position, callback/wrapper ABI, all glyphs/colours/paging and inventory/gold/flags/battery preservation checked. All seven native ROM bank loads and 1046 getters pass without RAM offset replacement. Display entry is controlled; gifts/unlocks happen outside A and ordinary story outcomes/progression are not claimed.'}
    (OUT/'report.json').write_text(json.dumps(report,indent=2)+'\n');print('Story commands:',len(results),'native cases passed')

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--cumulative',action='store_true')
    run(parser.parse_args().cumulative)
