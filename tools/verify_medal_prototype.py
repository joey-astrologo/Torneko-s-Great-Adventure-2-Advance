"""Native medal counts, alternating rewards and bounded message formatting."""
import argparse,json,struct
from collections import Counter
import mgba.log
from tools.rom import ROOT,digest,require
from tools.emulator import Session,Debugger,ffi
from tools.medal_text import add_medals,CAPACITY
from tools.bakery_playtest import service_ready
from tools.dialogue_checks import TextChecks,player_layout_cases
from tools.name_entry import HERO
from tools.opening_text import BANK_RAM
from tools.lz77 import decompress
from tools.verify_service_ui import materialize
from tools.verify_bank import balance
from tools.holy_flame_playtest import items

OUT=ROOT/'build/medal-prototype'
FLAGS=0x020101AC
TOTAL=0x020102A8
INVENTORY=0x0200DF28

def flag(m,ident,value=None):
    address=FLAGS+(ident>>3);mask=1<<(ident&7)
    if value is not None:m.u8[address]=(m.u8[address]&~mask)|(mask if value else 0)
    return bool(m.u8[address]&mask)

def candidate():
    import tools.build_english as english
    prior=english.add_combat;medals=None
    def add(build):
        nonlocal medals
        result=prior(build);medals=add_medals(build);return result
    try:english.add_combat=add;rom,build=english.build_rom(include_story=False)
    finally:english.add_combat=prior
    build['medals']=medals;OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'game.gba').write_bytes(rom);(OUT/'build.json').write_text(json.dumps(build,indent=2)+'\n')
    return rom,build

def run(cumulative=False):
    global OUT
    mgba.log.silence()
    if cumulative:
        from tools.build_english import build_rom
        OUT=ROOT/'build/english/medal-validation';rom,build=build_rom()
    else:rom,build=candidate()
    fixture=service_ready(rom,OUT);medals=build['medals']
    data,_=decompress(rom,medals['bank_rom_offset']);data=bytearray(data)
    for word in range(4):struct.pack_into('<I',data,word*4,(struct.unpack_from('<I',data,word*4)[0]+BANK_RAM)&0xFFFFFFFF)
    sources={r['offset']+0x08000000:r for r in medals['entries']};results=[]
    # total, carried medals, conversation flag DB, next-reward flag FD,
    # explicitly forced source 4 (not selected by the observed ordinary branch).
    configurations=[('initial',0,0,False,False,False),('next-sword',0,0,True,False,False),
                    ('next-shield',19,0,True,True,False),('donate-one',0,1,True,False,False),
                    ('earn-sword',19,1,True,False,False),('earn-shield',39,1,True,True,False),
                    ('full-medals',0,20,True,False,False),('cap-sword',980,19,True,False,False),
                    ('cap-shield',980,19,True,True,False),('terminal',999,1,True,False,False),
                    ('forced-shield-introduction',0,0,False,False,True)]
    for title,total,held,discussed,next_shield,forced in configurations:
        for name,player in player_layout_cases():
            case=title+'-'+name;print('Medals',case,flush=True)
            with Session(rom,OUT/case) as game:
                game.restore(fixture);m=game.core.memory;saved_bank=bytes(m[BANK_RAM:BANK_RAM+len(data)])
                for i,value in enumerate(data):m.u8[BANK_RAM+i]=value
                for i,value in enumerate(player.ljust(16,b'\0')):m.u8[HERO+i]=value
                prior_items=items(game);prior_total=m.u16[TOTAL];prior_flags=bytes(m[FLAGS:FLAGS+32])
                template=bytearray(bytes(m[INVENTORY:INVENTORY+120]));mapping=bytes(m[0x020013D0:0x020014D0])
                struct.pack_into('<I',template,0,0xC8000000);template[8]=mapping.index(215)
                template[4]=template[5]=1;template[24:]=bytes(96)
                gold=balance(game);check=TextChecks(game,{a:r for a,r in sources.items() if r['index'] in (8,9)})
                entries,formats,returned,forced_calls=[],[],[],[];pending=None
                def callback(event):
                    nonlocal pending
                    a,r=event['address'],event['registers']
                    if a==0x0801DFAC:
                        require(not entries,'Repeated medal entry');entries.append(event)
                        m.u16[TOTAL]=total;flag(m,0xDB,discussed);flag(m,0xFD,next_shield)
                        for slot in range(20):
                            if slot<held:
                                for i,value in enumerate(template):m.u8[INVENTORY+slot*120+i]=value
                            else:m.u32[INVENTORY+slot*120]=0
                        require(game.core._core.writeRegister(game.core._core,b'pc',ffi.new('uint32_t*',0x0805132C)),
                                'Controlled medal entry failed');return
                    if a==0x08051568 and forced:
                        require(r[0]==14 and r[1]==3,'Unexpected forced-introduction source')
                        game.core.cpu.gprs[1]=4;forced_calls.append({'group':14,'index_before':3,'index_after':4})
                    if a==0x08000FB8 and r[1] in sources:
                        require(pending is None and r[14] in (0x08051479,0x08051577),'Unexpected medal formatter caller')
                        row=sources[r[1]];require(r[0]==r[13] and 0x03007000<=r[13]
                                                and r[13]+CAPACITY+32==entries[0]['registers'][13], 'Medal buffer outside owned stack frame')
                        require(0<=r[2]<=999,'Medal number exceeds proven native bound')
                        expected=materialize(bytes.fromhex(row['encoded_hex']),[r[2]],m)
                        require(len(expected)<=row['layout']['maximum_formatted_bytes']<=CAPACITY,'Medal format exceeds bound')
                        pending=(r[0],expected,bytes(m[r[0]+CAPACITY:r[0]+CAPACITY+32]),r[4:12],r[13],row,r[2])
                    if a in (0x08051478,0x08051576):
                        require(pending is not None,'Medal formatter entry missing')
                        dest,expected,guard,regs,sp,row,value=pending
                        require(bytes(m[dest:dest+len(expected)])==expected,'Medal formatter output differs')
                        require(bytes(m[dest+CAPACITY:dest+CAPACITY+32])==guard and r[4:12]==regs and r[13]==sp,
                                'Medal formatter guard/ABI differs')
                        check.resources[dest]=row|{'encoded_hex':expected.hex()}
                        formats.append({'id':row['id'],'index':row['index'],'value':value,'dest':dest,
                                        'bytes':len(expected),'capacity':CAPACITY,'expected_hex':expected.hex(),
                                        'guard_and_abi_preserved':True});pending=None
                    if a==medals['returned']:
                        require(r[4:12]==entries[0]['registers'][4:12] and r[13]==entries[0]['registers'][13]
                                and r[0]==entries[0]['registers'][14],'Medal service return ABI differs')
                        require(check.active is None and all(check.completed(row['id']) for row in formats),
                                'Medal service returned before message finished')
                        require(bytes(m[BANK_RAM:BANK_RAM+len(data)])==data,'Medal service changed supplied bank')
                        for i,value in enumerate(saved_bank):m.u8[BANK_RAM+i]=value
                        returned.append(event['frame'])
                    if a in check.ADDRESSES:check.callback(event)
                with Debugger(game,callback,max_events=200000) as debug:
                    for address in set(check.ADDRESSES+(0x0801DFAC,0x08051568,0x08000FB8,0x08051478,0x08051576,medals['returned'])):
                        debug.breakpoint(address)
                    game.press('A',wait=120);game.capture('page-0')
                    for page in range(1,24):
                        if returned:break
                        game.press('A',wait=120);game.capture(f'page-{page}')
                    require(returned and pending is None,'Medal service failed to finish')
                expected_total=min(999,total+held) if total<999 else total
                threshold=(total//20+1)*20 if total<=979 else 999
                reward=bool(held and total<999 and expected_total>=threshold)
                reward_id=43 if next_shield else 22
                expected_items=Counter([reward_id] if reward else ([215]*held if total==999 else []))
                require(m.u16[TOTAL]==expected_total,'Native medal total/clamp differs')
                require(Counter(ident for _,ident,_ in items(game))==expected_items,'Native medal removal/reward differs')
                require(flag(m,0xFD)==(next_shield^reward) and flag(m,0xDB)==discussed,'Native medal flags differ')
                if reward:require(check.completed(next(r['id'] for r in sources.values() if r['index']==(9 if next_shield else 8))),
                                  'English reward message missing')
                require(bool(forced_calls)==forced,'Forced-introduction probe missing')
                require(balance(game)==gold and game.snapshot().battery==fixture.battery,'Medal probe changed gold/battery')
                results.append({'case':case,'total_before':total,'carried_medals':held,'total_after':expected_total,
                                'reward_id':reward_id if reward else None,'discussed':discussed,'next_shield':next_shield,
                                'original_items':prior_items,'original_total':prior_total,'original_flags_hex':prior_flags.hex(),
                                'controlled_player_hex':player.hex(),'controlled_bank_bytes':len(data),
                                'entries':entries,'forced_source_calls':forced_calls,'formats':formats,'reads':check.reads,
                                'glyph_checks':check.glyph_checks,'inputs':game.inputs,'bank_restored':True})
    required={r['id'] for r in sources.values()};seen={r['id'] for case in results for r in case['reads']}
    require(required<=seen,'Some medal resources lack native reads')
    report={'passed':True,'rom_sha256':digest(rom),'cases':results,
            'scope':'33 controlled native medal calls cover initial/repeat explanations, donation, sword/shield rewards, a full inventory of twenty medals, the 999 clamp/terminal branch and three player names. Source index4 is explicitly forced because the observed selector does not naturally choose it. Exact format/guard/ABI, pixels/paging, medal counts/removal, reward IDs, flags, gold and battery pass. Ordinary postgame access remains unaccepted.'}
    (OUT/'report.json').write_text(json.dumps(report,indent=2)+'\n');print('Medals:',len(results),'native cases passed')

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--cumulative',action='store_true');run(parser.parse_args().cumulative)
