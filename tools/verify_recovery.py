"""Native recovery/warp branches and bounded formatter output in visible gameplay."""
import argparse,json,struct
from pathlib import Path
import mgba.log
from tools.compact_font import encode
from tools.emulator import Session,Debugger,ffi
from tools.rom import ROOT,digest,require
from tools.verify_inventory_action_prototype import ActionCheck
from tools.verify_result_ui import native_format

CONSUMERS=(
    ('heal',0x120,0x13D90,0x13E90,0x13E9F,0x13EAC,10,30,(0,5,1)),
    ('maximum',0x124,0x13D90,0x13E18,0x13E27,0x13EAC,20,20,(2,0,1)),
    ('skill',0x120,0x40DB8,0x40E20,0x40E29,0x40E2E,10,30,(5,0,0)),
    ('warp',0x210,0x12220,0x12260,0x12269,0x122E8,10,30,(1,0,0)))


def run(source=ROOT/'build/recovery-prototype',only=None):
    out=source/'recovery-validation';mgba.log.silence()
    rom=(source/'torneko-2-english.gba').read_bytes();build=json.loads((source/'build.json').read_text())
    require(digest(rom)==build['output_sha256'],'Stale recovery ROM')
    from tools import verify_player_status_prototype as status
    previous=status.OUT
    try:status.OUT=out;fixture=status.ready(rom,build)
    finally:status.OUT=previous
    rows={r['table_offset']:r for r in build['recovery']['entries']};results=[]
    for owner,slot,entry,formatted,queued,end,hp,max_hp,arguments in CONSUMERS:
        if only and owner!=only:continue
        row=rows[slot]
        fields=['native']+(['maximum-width','maximum-bytes','coloured'] if 'actor' in row['fields'] else [])+(['zero','maximum-number'] if 'amount' in row['fields'] else [])
        for field in fields:
            name=owner+'-'+field;print('Recovery:',name,flush=True)
            with Session(rom,out/name) as g:
                g.restore(fixture);m=g.core.memory;initial=[];returns=[];formats=[];checks=[];pending={};overrides=[];colours=[];skips=[]
                hero=m.u32[0x02001624]
                def write(a,data):
                    overrides.append({'address':a,'before':bytes(m[a:a+len(data)]).hex(),'after':data.hex()})
                    for i,v in enumerate(data):m.u8[a+i]=v
                item=bytearray(120);struct.pack_into('<I',item,0,0xC8000000);item[4:6]=b'\1\1';item[8]=bytes(m[0x020013D0:0x020014D0]).index(177)
                write(0x0200DF28,item);definition=0x02003BAC+177*20;write(definition,struct.pack('<I',m.u32[definition]|0x40000000))
                def jump(e,address):
                    overrides.append({'event':e,'pc_after':address})
                    require(g.core._core.writeRegister(g.core._core,b'pc',ffi.new('uint32_t*',address)),'Recovery dispatch failed')
                def callback(e):
                    a,r=e['address'],e['registers']
                    if a==0x08015848 and not initial:
                        write(hero+0x84,struct.pack('<HH',hp,max_hp))
                        initial.append(e|{'guard':bytes(m[r[13]:r[13]+32]).hex(),'hp':hp,'max_hp':max_hp})
                        for i,v in enumerate((hero,)+arguments):g.core.cpu.gprs[i]=v
                        overrides.append({'event':e,'r0_r3_after':list((hero,)+arguments)});jump(e,entry+0x08000000)
                    if not initial or returns:return
                    if owner=='skill' and a==0x0803F354:
                        require(r[14]==0x08040DD1,'Unexpected skill animation caller')
                        skips.append(e|{'reason':'Isolate text/HP arithmetic from the skill sprite animation, whose setup is absent in this controlled Drink context.'})
                        jump(e,0x08040DD0)
                    if a==0x08000FB8 and r[14]==formatted+0x08000001:
                        require(r[1]==row['offset']+0x08000000 and r[0]==r[13],'Recovery native selection/buffer differs')
                        regs=list(r);args=[]
                        for i,role in enumerate(row['fields'],2):
                            if role=='actor' and field in ('maximum-width','maximum-bytes','coloured'):
                                raw=encode('W'*31 if field=='maximum-width' else 'i'*31 if field=='maximum-bytes' else 'Torneko')
                                if field=='coloured':raw=b'\x03\x05'+raw[:-1]+b'\x05\0'
                                write(0x02008D08,raw.ljust(64,b'\0'));regs[i]=0x02008D08
                            elif role=='amount' and field in ('zero','maximum-number'):regs[i]=0 if field=='zero' else 2147483647
                            if regs[i]!=r[i]:g.core.cpu.gprs[i]=regs[i];overrides.append({'event':e,'register':i,'after':regs[i]})
                            args.append(regs[i])
                        payload=native_format(bytes.fromhex(row['encoded_hex']),args,m)
                        require(len(payload)<=row['maximum_bytes']<=256,'Recovery output overflow')
                        names=[(v,bytes(m[v:v+64]).hex()) for role,v in zip(row['fields'],args) if role=='actor']
                        pending.update(regs=regs,payload=payload,guard=bytes(m[r[0]+256:r[0]+272]),names=names)
                        checks.append(ActionCheck(g,payload[:-1],queued+0x08000000,256,pending['guard']))
                    if a==formatted+0x08000000 and pending:
                        old=pending['regs'];p=old[0];payload=pending['payload']
                        require(bytes(m[p:p+len(payload)])==payload and bytes(m[p+256:p+272])==pending['guard'] and r[4:12]==old[4:12] and r[13]==old[13] and all(bytes(m[v:v+64]).hex()==raw for v,raw in pending['names']),'Recovery output/name/guard/ABI differs')
                        formats.append({'id':row['id'],'hex':payload.hex(),'bytes':len(payload),'capacity':256,'guard_abi_match':True});pending.clear()
                    if checks and not (checks[0].complete and checks[0].returned):
                        if a==0x08001C14 and checks[0].pending_glyph:
                            bank=m.u16[m.u32[r[5]+12]]>>12;colour=m.u16[0x05000000+2*(bank*16+m.u8[0x020000C2])]
                            colours.append(tuple(((colour>>s)&31)*255//31 for s in (0,5,10)))
                        checks[0].callback(e)
                    if owner=='warp' and a==(queued&~1)+0x08000000:
                        require(checks and checks[0].complete and checks[0].returned,'Warp text incomplete before controlled skip')
                        skips.append(e);jump(e,0x080122E2)
                    if a==end+0x08000000:
                        old=initial[0]['registers'];require(r[4:12]==old[4:12] and r[13]==old[13] and r[0]==old[14] and bytes(m[r[13]:r[13]+32]).hex()==initial[0]['guard'],'Recovery caller ABI/guard differs');returns.append(e)
                with Debugger(g,callback,max_events=100000) as debug:
                    for a in (0x08015848,0x08000FB8,0x0803F354,formatted+0x08000000,0x0801588C,0x080158CE,(queued&~1)+0x08000000,end+0x08000000,0x08001BC4,0x08001C14,0x08001C68):debug.breakpoint(a)
                    g.press('B',hold=8,wait=30);g.press('A',wait=30);g.press('A',wait=30)
                    actions=[]
                    for i in range(7):
                        n=m.u16[0x0200CDD0+i*2]
                        if not n:break
                        actions.append(n)
                    require(13 in actions,'Native recovery test Drink unavailable')
                    for _ in range(actions.index(13)):g.press('DOWN',wait=20)
                    g.capture('menu');g.press('A',wait=0)
                    for _ in range(900):
                        g.frames(1)
                        if returns:break
                    require(len(initial)==len(returns)==len(checks)==len(formats)==1 and checks[0].complete and checks[0].returned and not pending,'Recovery route incomplete: '+repr((name,len(initial),len(returns),len(checks),len(formats),[hex(x) for x in g.core.cpu.gprs],m.u16[hero+0x84],m.u16[hero+0x86])))
                    expected=(15,30) if owner in ('heal','skill') else (22,22) if owner=='maximum' else (10,30)
                    require((m.u16[hero+0x84],m.u16[hero+0x86])==expected,'Recovery native HP outcome differs')
                    g.frames(3);pic=g.capture('message');c=checks[0];visible=[];pixels=0
                    require(len(c.draws)==len(colours),'Recovery colours incomplete')
                    for draw,colour in zip(c.draws,colours):
                        if draw['native_scroll']:
                            shift=draw['key'][-1]-draw['y'];require(shift>0,'Unexpected recovery scroll')
                            for old in visible:old['final_y']-=shift
                        visible.append(draw|{'final_y':draw['y'],'colour':colour})
                    for d in visible:
                        require(d['final_y']>=0,'Recovery scrolled out of view');glyph,_=c.glyph_record(d['code'])
                        for y,line in enumerate(glyph['rows']):
                            for x,bit in enumerate(line):
                                px=m.u8[0x02000000]+d['x']+x;py=m.u8[0x02000001]+d['final_y']*16+y
                                require((pic.getpixel((px,py))==d['colour'])==(bit=='#'),'Recovery final pixels differ');pixels+=1
                require(g.snapshot().battery==fixture.battery,'Recovery wrote battery')
                results.append({'case':name,'id':row['id'],'owner':owner,'field':field,'overrides':overrides,'inputs':g.inputs,'formats':formats,'queue':checks[0].queued,'visible_pixels_checked':pixels,'caller_guard_abi_preserved':True,'hp_after':expected,'visual_effect_skips':skips,'images':{p:digest((g.output/p).read_bytes()) for p in ('menu.png','message.png')}})
    report={'passed':True,'rom_sha256':digest(rom),'cases':results,'scope':'Native Drink opens the message window, then explicit dispatch invokes owned HP helpers or warp. Both healing helpers and max-HP growth retain actual native arithmetic. Native sources,256-byte outputs, actor186px/63-byte and nonnegative integer0/2147483647 preflight fields, coloured final pixels and full caller ABI/guards pass. Skill sprite animation0803F354 and warp animation/movement after its real queue return are explicitly skipped; natural skill activation/acquisition, encounters and teleport destination are not claimed.'}
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print('Recovery:',len(results),'passed',flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,default=ROOT/'build/recovery-prototype');p.add_argument('--only');a=p.parse_args();run(a.source,a.only)
