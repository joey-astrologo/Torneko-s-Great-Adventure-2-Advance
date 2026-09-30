"""Native pending-to-learned skill flags, indexed names and acquisition panel."""
import argparse,json,struct
from pathlib import Path
import mgba.log
from tools.rom import ROOT,digest,require
from tools.emulator import Session,Debugger,ffi
from tools.dialogue_checks import TextChecks,player_layout_cases
from tools.name_entry import HERO
from tools.verify_result_ui import native_format


def run(source,only=None):
    out=source/'skill-learning-validation';mgba.log.silence();rom=(source/'torneko-2-english.gba').read_bytes();build=json.loads((source/'build.json').read_text());require(digest(rom)==build['output_sha256'],'Stale skill-learning ROM')
    from tools import verify_player_status_prototype as status
    prior=status.OUT
    try:status.OUT=out;fixture=status.ready(rom,build)
    finally:status.OUT=prior
    row=next(r for r in build['skill_messages']['entries'] if r['table_offset']==0x754)
    explanations={r['table_offset']:r for r in build['skill_messages']['entries'] if r['table_offset'] in (0x7E8,0x7EC,0x7F0)}
    names={r['skill_id']:r for r in build['skill_info']['entries'] if r['kind']=='name'};results=[]
    for ident in range(128):
        if only is not None and ident!=only:continue
        for label,player in player_layout_cases():
            case=f'{ident}-{label}';print('Skill acquisition:',case,flush=True)
            with Session(rom,out/case) as g:
                g.restore(fixture);m=g.core.memory;hero=m.u32[0x02001624];overrides=[];initial=[];returns=[];formats=[];pending={};draws=[];images={};pixels=0;tabs=[];panel=TextChecks(g,{r['offset']+0x08000000:r|{'layout':{'pages':[[r['id']]]}} for r in explanations.values()})
                def write(a,data):
                    overrides.append({'address':a,'before':bytes(m[a:a+len(data)]).hex(),'after':data.hex()})
                    for i,v in enumerate(data):m.u8[a+i]=v
                item=bytearray(120);struct.pack_into('<I',item,0,0xC8000000);item[4:6]=b'\1\1';item[8]=bytes(m[0x020013D0:0x020014D0]).index(177);write(0x0200DF28,item)
                at=0x02003BAC+20*177;write(at,struct.pack('<I',m.u32[at]|0x40000000));write(HERO,player.ljust(16,b'\0'))
                def callback(e):
                    nonlocal pending
                    a,r=e['address'],e['registers']
                    if a==0x08015848 and not initial:
                        initial.append(e|{'guard':bytes(m[r[13]:r[13]+32]).hex()})
                        write(hero+0x90,b'\1');write(0x02004DFA,bytes(128));write(0x02004E7B,bytes(int(i==ident) for i in range(128)))
                        overrides.append({'event':e,'r0_after':0,'pc_after':0x0803BE18,'reason':'Native acquisition handler with one controlled pending flag; celebration animation disabled by original parameter0.'})
                        g.core.cpu.gprs[0]=0;require(g.core._core.writeRegister(g.core._core,b'pc',ffi.new('uint32_t*',0x0803BE18)),'Skill acquisition dispatch failed');return
                    if not initial or returns:return
                    if a==0x08000FB8 and r[14]==0x0803BE79:
                        require(r[1]==row['offset']+0x08000000 and r[0]==r[13]+4 and r[2]==names[ident]['offset']+0x08000000,'Skill acquisition native source/name/frame differs')
                        raw=native_format(bytes.fromhex(row['encoded_hex']),[r[2]],m);require(len(raw)<=row['maximum_bytes']<=256,'Skill acquisition output exceeds capacity')
                        pending={'regs':r,'raw':raw,'guard':bytes(m[r[0]+256:r[0]+272])}
                    if a==0x0803BE78 and pending:
                        old=pending['regs'];p=old[0];raw=pending['raw']
                        require(bytes(m[p:p+len(raw)])==raw and bytes(m[p+256:p+272])==pending['guard'] and r[4:12]==old[4:12] and r[13]==old[13],'Skill acquisition output/guard/ABI differs')
                        formats.append({'id':row['id'],'bytes':len(raw),'hex':raw.hex(),'guard_abi_preserved':True});panel.resources[p]=row|{'encoded_hex':raw.hex(),'layout':{'pages':[[row['id']]]}};pending={}
                    if a==0x08015A18 and r[14]==0x0803BF33:
                        definition=bytes.fromhex(build['skill_info']['definitions'][ident]['record_hex']);slot=0x7F0 if struct.unpack_from('<I',definition,16)[0] else 0x7E8 if struct.unpack_from('<I',definition,12)[0]&1 else 0x7EC
                        require(r[0]==explanations[slot]['offset']+0x08000000,'Native skill explanation selector differs')
                    if a==0x080020D6 and panel.active:tabs.append({'before_x':m.u8[r[5]+2],'window':r[5]})
                    if a==0x080020E0 and panel.active:
                        require(tabs and m.u8[tabs[-1]['window']+2]==(tabs[-1]['before_x']&0xE0)+32,'Native trailing09 tab differs');tabs[-1]['after_x']=m.u8[tabs[-1]['window']+2]
                    if a==0x08001BC4 and panel.active:
                        w=r[0];key=(w,r[1],r[13],r[14],m.u8[w+2],m.u8[w+3])
                        if not draws or draws[-1]['key']!=key:draws.append({'key':key,'window':w,'code':r[1],'x':m.u8[w+2],'y':m.u8[w+3],'origin':[m.u8[w],m.u8[w+1]],'foreground':m.u8[0x020000C2],'bank':m.u16[m.u32[w+12]]>>12})
                    if a in panel.ADDRESSES:panel.callback(e)
                    if a==0x0803BF5C:
                        old=initial[0]['registers'];require(r[4:12]==old[4:12] and r[13]==old[13] and r[0]==old[14] and bytes(m[r[13]:r[13]+32]).hex()==initial[0]['guard'],'Skill acquisition caller ABI/guard differs');returns.append(e)
                with Debugger(g,callback,max_events=150000) as debug:
                    for a in {0x08015848,0x08015A18,0x08000FB8,0x0803BE78,0x0803BF5C,0x080020D6,0x080020E0}|set(panel.ADDRESSES):debug.breakpoint(a)
                    g.press('B',hold=8,wait=30);g.press('A',wait=30);g.press('A',wait=30);actions=[]
                    for i in range(7):
                        n=m.u16[0x0200CDD0+i*2]
                        if not n:break
                        actions.append(n)
                    require(13 in actions,'Skill acquisition Drink trigger absent')
                    for _ in range(actions.index(13)):g.press('DOWN',wait=20)
                    g.capture('menu');images['menu.png']=digest((g.output/'menu.png').read_bytes());g.press('A',wait=0);captured=0
                    for _ in range(1200):
                        g.frames(1)
                        if len(panel.reads)>captured and not panel.active:
                            g.frames(3);picture='message' if captured==0 else 'explanation';pic=g.capture(picture);images[picture+'.png']=digest((g.output/(picture+'.png')).read_bytes())
                            for d in draws:
                                glyph,_=panel.glyph_record(d['code']);require(d['x']+glyph['advance']<=m.u8[d['window']+4]*8,'Skill acquisition panel clips')
                                colour=m.u16[0x05000000+2*(16*d['bank']+d['foreground'])];rgb=tuple(((colour>>s)&31)*255//31 for s in (0,5,10))
                                for y,line in enumerate(glyph['rows']):
                                    for x,bit in enumerate(line):require((pic.getpixel((d['origin'][0]+d['x']+x,d['origin'][1]+d['y']*16+y))==rgb)==(bit=='#'),'Skill acquisition final pixels differ');pixels+=1
                            captured+=1;draws.clear();g.press('A',wait=0)
                        if returns:break
                    require(len(initial)==len(returns)==len(formats)==1 and len(panel.reads)==captured==2 and not pending and tabs and all('after_x' in t for t in tabs),'Skill acquisition route incomplete: '+repr((case,len(formats),len(panel.reads),len(returns),tabs)))
                    require(bytes(m[0x02004E7B:0x02004E7B+128])==bytes(128) and bytes(m[0x02004DFA:0x02004DFA+128])==bytes(int(i==ident) for i in range(128)),'Native pending/learned skill flags differ')
                require(g.snapshot().battery==fixture.battery and bytes(m[HERO:HERO+16])==player.ljust(16,b'\0'),'Skill acquisition changed battery/player name')
                results.append({'case':case,'skill_id':ident,'player_case':label,'inputs':g.inputs,'overrides':overrides,'formats':formats,'reads':panel.reads,'tabs':tabs,'native_state_checked':True,'caller_guard_abi_preserved':True,'visible_pixels_checked':pixels,'images':images})
    report={'passed':True,'rom_sha256':digest(rom),'cases':results,'scope':'All128 native pending-to-learned skill selectors and three player-name cases. Actual original acquisition handler runs with its original parameter0 (no celebration animation), original frame,256-byte output, modal panel and09 tab. English name/table routing, learned flags, output guards, caller ABI, glyphs/pixels and battery verified. Pending flags are controlled; natural skill learning conditions and celebration animation remain separate.'}
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print('Skill acquisition:',len(results),'passed',flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,default=ROOT/'build/english');p.add_argument('--only',type=int);a=p.parse_args();run(a.source,a.only)
