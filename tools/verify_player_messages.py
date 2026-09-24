"""Native player-name wrapper mapping, maximum names, queue flags and fallback pointers."""
import argparse,json,struct
import mgba.log
from tools.rom import ROOT,digest,require,load_base
from tools.emulator import Session,Debugger,ffi
from tools.player_message_text import add_player_messages
from tools.dialogue_checks import player_layout_cases
from tools.name_entry import HERO
from tools.verify_service_ui import materialize,cstring
from tools.verify_inventory_action_prototype import ActionCheck
from tools.extract_shared_text import extract

OUT=ROOT/'build/player-messages-prototype'

def candidate():
    import tools.build_english as english
    prior=english.add_combat;resource=None
    def add(build):
        nonlocal resource
        result=prior(build);resource=add_player_messages(build);return result
    try:english.add_combat=add;rom,build=english.build_rom(include_story=False,include_extra_consumers=False)
    finally:english.add_combat=prior
    build['player_messages']=resource;build['reviewed_resource_counts']['player_messages']=len(resource['entries'])
    build['total_reviewed_inserted_resources']+=len(resource['entries'])
    OUT.mkdir(parents=True,exist_ok=True);(OUT/'game.gba').write_bytes(rom)
    (OUT/'build.json').write_text(json.dumps(build,indent=2)+'\n');return rom,build

def run(cumulative=False):
    global OUT
    import tools.verify_player_status_prototype as status
    mgba.log.silence()
    if cumulative:
        OUT=ROOT/'build/english/player-message-validation';rom=(ROOT/'build/english/torneko-2-english.gba').read_bytes()
        build=json.loads((ROOT/'build/english/build.json').read_text());require(digest(rom)==build['output_sha256'],'Player message ROM differs')
    else:rom,build=candidate()
    prior=status.OUT
    try:status.OUT=OUT;fixture=status.ready(rom,build)
    finally:status.OUT=prior
    configs=[{'id':r['id'],'input':r['source']['offset']+0x08000000,'output':r['offset']+0x08000000,
              'payload':bytes.fromhex(r['encoded_hex']),'maximum':r['maximum_bytes'],'mapped':True}
             for r in build['player_messages']['entries']]
    english=build['player_status']['entries'][0]
    japanese=next(r['source'] for r in extract()['entries'] if r['table_offset']==0x414)
    configs.extend([{'id':'fallback-english','input':english['offset']+0x08000000,'output':english['offset']+0x08000000,
                     'payload':bytes.fromhex(english['encoded_hex']),'maximum':256,'mapped':False},
                    {'id':'fallback-japanese','input':japanese['offset']+0x08000000,'output':japanese['offset']+0x08000000,
                     'payload':bytes.fromhex(japanese['raw_hex']),'maximum':256,'mapped':False},
                    {'id':'fallback-ram','input':HERO,'output':HERO,'payload':None,'maximum':16,'mapped':False}])
    results=[]
    for config in configs:
        for label,name in player_layout_cases():
            for flag in (0,1):
                case=config['id']+'-'+label+f'-flag{flag}';print('Player wrapper:',case,flush=True)
                with Session(rom,OUT/case) as game:
                    game.restore(fixture);m=game.core.memory;overrides=[];entries=[];returns=[];formats=[];pending=None;checks=[];queue_flags=[]
                    def write(address,data):
                        overrides.append({'address':address,'before':bytes(m[address:address+len(data)]).hex(),'after':data.hex()})
                        for i,v in enumerate(data):m.u8[address+i]=v
                    def reg(event,index,value):
                        overrides.append({'pc':event['address'],'register':f'r{index}','before':event['registers'][index],'after':value})
                        game.core.cpu.gprs[index]=value
                    write(HERO,name.ljust(16,b'\0'))
                    address=0x0200DF28;item=bytearray(120);struct.pack_into('<I',item,0,0xC8000000)
                    item[4]=item[5]=1;item[8]=bytes(m[0x020013D0:0x020014D0]).index(177);write(address,item)
                    address=0x02003BAC+177*20;write(address,struct.pack('<I',m.u32[address]|0x40000000))
                    def callback(event):
                        nonlocal pending
                        a,r=event['address'],event['registers']
                        if a==0x08015848:
                            require(not entries,'Unexpected additional player wrapper invocation')
                            entries.append(event|{'guard':bytes(m[r[13]:r[13]+32]).hex()})
                            reg(event,0,config['input']);reg(event,1,flag)
                        if entries and a==0x08000FB8 and r[14]==0x08015861:
                            require(r[0]==r[13] and r[1]==config['output'] and r[2]==HERO,'Player mapper/formatter arguments differ')
                            payload=name if config['payload'] is None else config['payload']
                            expected=materialize(payload,[HERO],m)
                            require(len(expected)<=config['maximum']<=256,'Player formatted bytes exceed owned capacity')
                            pending=(r[0],expected,bytes(m[r[0]+256:r[0]+272]),r[4:12],r[13])
                            checks.append(ActionCheck(game,expected[:-1],0x08015869,256,pending[2]))
                        if pending and a==0x08015860:
                            dest,expected,guard,regs,sp=pending
                            require(bytes(m[dest:dest+len(expected)])==expected and bytes(m[dest+256:dest+272])==guard
                                    and r[4:12]==regs and r[13]==sp,'Player wrapper formatter output/guard/ABI differs')
                            formats.append({'hex':expected.hex(),'bytes':len(expected),'source':config['output'],'capacity':256});pending=None
                        if entries and a==0x0801588C and r[14]==0x08015869:
                            require(r[1]==flag,'Player wrapper changed queue flags');queue_flags.append(r[1])
                        if checks and not(checks[-1].complete and checks[-1].returned):checks[-1].callback(event)
                        if entries and a==0x0801586E:
                            initial=entries[0]['registers']
                            require(r[4:12]==initial[4:12] and r[13]==initial[13] and r[0]==initial[14]
                                    and bytes(m[r[13]:r[13]+32]).hex()==entries[0]['guard'],'Player wrapper changed caller ABI/guard')
                            returns.append(event)
                    addresses={0x08015848,0x08000FB8,0x08015860,0x08015868,0x0801586E,
                               0x0801588C,0x080158CE,0x08001BC4,0x08001C14,0x08001C68}
                    with Debugger(game,callback,max_events=90000) as debug:
                        for a in addresses:debug.breakpoint(a)
                        game.press('B',hold=8,wait=30);game.press('A',wait=30);game.press('A',wait=30)
                        actions=[]
                        for i in range(7):
                            value=m.u16[0x0200CDD0+i*2]
                            if not value:break
                            actions.append(value)
                        require(13 in actions,'Native Life herb Drink action absent')
                        for _ in range(actions.index(13)):game.press('DOWN',wait=20)
                        game.capture('selection');game.press('A',wait=0)
                        for _ in range(900):
                            if returns and checks and checks[-1].complete and checks[-1].returned:break
                            game.frames(1)
                        game.capture('result')
                    require(len(entries)==len(returns)==len(formats)==len(checks)==1 and pending is None and
                            checks[0].complete and checks[0].returned and queue_flags==[flag], 'Player wrapper case incomplete')
                    require(bytes(m[HERO:HERO+16])==name.ljust(16,b'\0') and game.snapshot().battery==fixture.battery,
                            'Player wrapper changed name/battery')
                    results.append({'case':case,'id':config['id'],'mapped':config['mapped'],'input_pointer':config['input'],
                                    'output_pointer':config['output'],'player_case':label,'queue_flag':flag,'controlled_overrides':overrides,
                                    'formats':formats,'queue':checks[0].queued,'glyphs':len(checks[0].draws),'inputs':game.inputs})
    report={'passed':True,'rom_sha256':digest(rom),'cases':results,
            'scope':'Native Life herb Drink reaches the common player-name formatter, then explicit original-source-pointer and queue-flag overrides exercise33 reviewed mappings. Required English, widest English and widest Japanese names; flags0/1; unmapped original Japanese, already-English and existing player-name RAM pointers. Exact source routing, one/two-line decisions,256-byte guards, formatter/queue/wrapper ABI, glyphs, name and battery preservation. Other consumers, ordinary availability/effect progression and arbitrary custom names remain separate.'}
    (OUT/'report.json').write_text(json.dumps(report,indent=2)+'\n');print('Player wrapper:',len(results),'cases passed')

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--cumulative',action='store_true');run(parser.parse_args().cumulative)
