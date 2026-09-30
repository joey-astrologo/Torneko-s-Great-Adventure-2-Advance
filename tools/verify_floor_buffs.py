"""Native item bonus selection, floor duration messages and exhausted effects."""
import argparse,json,struct
from pathlib import Path
import mgba.log
from tools.rom import ROOT,digest,require
from tools.emulator import Session,Debugger,ffi
from tools.compact_font import encode
from tools.dialogue_checks import player_layout_cases
from tools.name_entry import HERO
from tools.verify_inventory_action_prototype import ActionCheck
from tools.verify_result_ui import native_format


def run(source):
    out=source/'floor-buff-validation';mgba.log.silence();rom=(source/'torneko-2-english.gba').read_bytes();build=json.loads((source/'build.json').read_text());require(digest(rom)==build['output_sha256'],'Stale floor buff ROM')
    from tools import verify_player_status_prototype as status
    previous=status.OUT
    try:status.OUT=out;fixture=status.ready(rom,build)
    finally:status.OUT=previous
    slots=(0xF4,0xF8,0xFC,0x100,0x104,0x108,0x10C,0x8EC)
    rows={r['table_offset']:r for r in build['player_messages']['entries']};rows[0x8EC]=build['floor_buffs']['entries'][0]
    configs=[(branch,label,name) for branch in range(7) for label,name in player_layout_cases()]+[(7,field,encode('Torneko')) for field in ('native','maximum-width','maximum-bytes','coloured')]
    results=[]
    for branch,field,player in configs:
        name=f'{branch}-{field}';row=rows[slots[branch]];print('Floor buff:',name,flush=True)
        with Session(rom,out/name) as g:
            g.restore(fixture);m=g.core.memory;initial=[];returns=[];reads=[];formats=[];checks=[];pending={};overrides=[];colours=[];wrapper=[]
            hero=m.u32[0x02001624]
            def write(a,data):
                require(0x02000000<=a and a+len(data)<=0x04000000,'Floor buff override outside existing RAM')
                overrides.append({'address':a,'before':bytes(m[a:a+len(data)]).hex(),'after':data.hex()})
                for i,v in enumerate(data):m.u8[a+i]=v
            write(HERO,player.ljust(16,b'\0'))
            item=bytearray(120);struct.pack_into('<I',item,0,0xC8000000);item[4:6]=b'\1\1';item[8]=bytes(m[0x020013D0:0x020014D0]).index(177);write(0x0200DF28,item)
            at=0x02003BAC+177*20;write(at,struct.pack('<I',m.u32[at]|0x40000000))
            fmt_return=0x0803353C if branch==7 else 0x08015860;queue_lr=0x08033545 if branch==7 else 0x08015869
            def callback(e):
                a,r=e['address'],e['registers']
                if a==0x08015848 and not initial:
                    write(hero+8,struct.pack('<I',m.u32[hero+8]&~0x7C000000));write(hero+0x84,struct.pack('<HH',10,30));write(hero+0x76,struct.pack('<HH',10,10));write(hero+0x54,bytes(m[hero+0x58:hero+0x5C]));write(0x020081E6,bytes([1 if branch==7 else 0])*7)
                    initial.append(e|{'guard':bytes(m[r[13]:r[13]+32]).hex(),'hero_before':bytes(m[hero:hero+0xC0]).hex()})
                    g.core.cpu.gprs[0]=hero;g.core.cpu.gprs[1]=1
                    overrides.append({'event':e,'r0_r1_after':[hero,1],'pc_after':0x080334E0});require(g.core._core.writeRegister(g.core._core,b'pc',ffi.new('uint32_t*',0x080334E0)),'Floor buff dispatch failed');return
                if not initial or returns:return
                if a==0x080334FC:
                    value=min(branch,6);g.core.cpu.gprs[0]=value;overrides.append({'event':e,'register':0,'after':value,'reason':'Choose a valid native RNG index; native search and used flags remain active.'})
                if a==0x08015848 and r[14] in (0x08033637,0x08033657):
                    require(branch<7 and r[0]==row['source']['offset']+0x08000000 and r[1]==1,'Floor buff native selector differs');reads.append(e);wrapper.append(e|{'guard':bytes(m[r[13]:r[13]+32]).hex()})
                if a==0x08000FB8 and r[14]==fmt_return+1:
                    require(r[1]==row['offset']+0x08000000 and r[0]==r[13],'Floor buff source/output differs')
                    regs=list(r)
                    if branch==7 and field!='native':
                        raw=encode('W'*27 if field=='maximum-width' else 'i'*31 if field=='maximum-bytes' else 'Oaken club')
                        if field=='coloured':raw=b'\x03\x05'+raw[:-1]+b'\x05\0'
                        write(0x02008D08,raw.ljust(64,b'\0'));regs[2]=0x02008D08;g.core.cpu.gprs[2]=regs[2];overrides.append({'event':e,'register':2,'after':regs[2]})
                    if branch==7:reads.append(e)
                    payload=native_format(bytes.fromhex(row['encoded_hex']),[regs[2]],m);require(len(payload)<=row['maximum_bytes']<=256,'Floor buff output overflow')
                    pending.update(regs=regs,payload=payload,guard=bytes(m[r[0]+256:r[0]+272]),field=bytes(m[regs[2]:regs[2]+(16 if branch<7 else 64)]))
                    checks.append(ActionCheck(g,payload[:-1],queue_lr,256,pending['guard']))
                if a==fmt_return and pending:
                    old=pending['regs'];p=old[0];payload=pending['payload'];n=len(pending['field'])
                    require(bytes(m[p:p+len(payload)])==payload and bytes(m[p+256:p+272])==pending['guard'] and r[4:12]==old[4:12] and r[13]==old[13] and bytes(m[old[2]:old[2]+n])==pending['field'],'Floor buff formatter/field/guard/ABI differs')
                    formats.append({'id':row['id'],'hex':payload.hex(),'bytes':len(payload),'capacity':256,'guard_abi_match':True});pending.clear()
                if checks and not(checks[0].complete and checks[0].returned):
                    duplicate=False
                    if a==0x08001C14 and checks[0].pending_glyph:
                        bank=m.u16[m.u32[r[5]+12]]>>12;c=m.u16[0x05000000+2*(bank*16+m.u8[0x020000C2])];rgb=tuple(((c>>s)&31)*255//31 for s in (0,5,10))
                        glyph=checks[0].pending_glyph;key=(r[0],r[4],r[5],r[13],r[14],rgb)
                        duplicate='probe_preparation' in glyph
                        if duplicate:require(glyph['probe_preparation']==key,'Repeated glyph preparation differs')
                        else:glyph['probe_preparation']=key;colours.append(rgb)
                    if not duplicate:checks[0].callback(e)
                if a==0x0801586E and wrapper:
                    old=wrapper[0]['registers'];require(r[4:12]==old[4:12] and r[13]==old[13] and r[0]==old[14] and bytes(m[r[13]:r[13]+32]).hex()==wrapper[0]['guard'],'Floor buff wrapper caller changed')
                if a==0x0803365C:
                    old=initial[0]['registers'];require(r[4:12]==old[4:12] and r[13]==old[13] and r[0]==old[14] and bytes(m[r[13]:r[13]+32]).hex()==initial[0]['guard'],'Floor buff caller changed');returns.append(e)
            with Debugger(g,callback,max_events=160000) as debug:
                for a in (0x08015848,0x080334FC,0x08000FB8,fmt_return,queue_lr&~1,0x0801586E,0x0803365C,0x0801588C,0x080158CE,0x08001BC4,0x08001C14,0x08001C68):debug.breakpoint(a)
                g.press('B',hold=8,wait=30);g.press('A',wait=30);g.press('A',wait=30)
                actions=[]
                for i in range(7):
                    n=m.u16[0x0200CDD0+i*2]
                    if not n:break
                    actions.append(n)
                require(13 in actions,'Floor buff Drink trigger missing')
                for _ in range(actions.index(13)):g.press('DOWN',wait=20)
                g.capture('menu');g.press('A',wait=0)
                for _ in range(1200):
                    g.frames(1)
                    if returns:break
                require(len(initial)==len(returns)==len(reads)==len(formats)==len(checks)==1 and checks[0].complete and checks[0].returned and not pending,'Floor buff route incomplete: '+repr((name,len(returns),len(reads),len(formats))))
                used=bytes(m[0x020081E6:0x020081ED]);require(used==bytes([1]*7) if branch==7 else used==bytes(int(i==branch) for i in range(7)),'Native bonus effect flags differ')
                expected_flag={0:0x40000000,1:0x20000000,2:0x10000000,3:0x08000000,6:0x04000000}.get(branch,0)
                require(m.u32[hero+8]&0x7C000000==expected_flag,'Native floor effect differs')
                require(m.u16[hero+0x84]==(30 if branch==4 else 10),'Native HP result differs')
                require(m.u16[hero+0x76]==m.u16[hero+0x78]==(11 if branch==5 else 10),'Native strength result differs')
                g.frames(3);pic=g.capture('message');c=checks[0];visible=[];pixels=0;require(len(c.draws)==len(colours),'Floor buff colour coverage differs')
                for d,colour in zip(c.draws,colours):
                    if d['native_scroll']:
                        shift=d['key'][-1]-d['y']
                        for old in visible:old['final_y']-=shift
                    visible.append(d|{'final_y':d['y'],'colour':colour})
                for d in visible:
                    require(d['final_y']>=0,'Floor buff message scrolled away');glyph,_=c.glyph_record(d['code'])
                    for y,line in enumerate(glyph['rows']):
                        for x,bit in enumerate(line):
                            px=m.u8[c.window]+d['x']+x;py=m.u8[c.window+1]+d['final_y']*16+y
                            require((pic.getpixel((px,py))==d['colour'])==(bit=='#'),'Floor buff final pixels differ');pixels+=1
            require(g.snapshot().battery==fixture.battery and bytes(m[HERO:HERO+16])==player.ljust(16,b'\0'),'Floor buff changed name/save')
            results.append({'case':name,'branch':branch,'field':field,'id':row['id'],'inputs':g.inputs,'overrides':overrides,'reads':reads,'formats':formats,'queue':c.queued,'native_state_checked':True,'caller_guard_abi_preserved':True,'visible_pixels_checked':pixels,'images':{p:digest((g.output/p).read_bytes()) for p in ('menu.png','message.png')}})
    report={'passed':True,'rom_sha256':digest(rom),'cases':results,'scope':'Controlled original bonus-effect routine080334E0 from Drink. All seven native outcomes and exhausted-effect branch; original RNG search, state flags, HP/strength changes and complete routine/wrapper return. Ordinary acquisition and floor transition expiry remain separate. Three player-name cases and four exhausted-message field cases validate bytes/guards, native wrapping, colour and final pixels.'}
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print('Floor buffs:',len(results),'passed',flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,default=ROOT/'build/floor-buffs-prototype');a=p.parse_args();run(a.source)
