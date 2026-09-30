"""Native maximum-fullness messages, decimal bounds and state limits."""
import argparse,json,struct
from pathlib import Path
import mgba.log
from tools.rom import ROOT,digest,require
from tools.emulator import Session,Debugger,ffi
from tools.verify_inventory_action_prototype import ActionCheck
from tools.verify_result_ui import native_format
# owner, entry, formatter return, queue LR, final BX
OWNERS=(('food',0x3316C,0x331EA,0x331F3,0x33232),('increase',0x33908,0x33984,0x3398D,0x33992),('decrease',0x33998,0x339FA,0x33A03,0x33A08))


def run(source):
    out=source/'fullness-validation';mgba.log.silence();rom=(source/'torneko-2-english.gba').read_bytes();build=json.loads((source/'build.json').read_text());require(digest(rom)==build['output_sha256'],'Stale fullness ROM')
    from tools import verify_player_status_prototype as status
    previous=status.OUT
    try:status.OUT=out;fixture=status.ready(rom,build)
    finally:status.OUT=previous
    row=build['fullness']['entries'][0];results=[]
    for owner,entry,formatted,queued,end in OWNERS:
        for field in ('normal','boundary','maximum-decimal','zero-decimal'):
            name=owner+'-'+field;print('Fullness:',name,flush=True)
            maximum=198 if owner=='food' and field=='boundary' else 195 if owner=='increase' and field=='boundary' else 5 if owner=='decrease' and field=='boundary' else 100
            final=min(200,maximum+1) if owner=='food' else min(200,maximum+10) if owner=='increase' else max(0,maximum-10)
            with Session(rom,out/name) as g:
                g.restore(fixture);m=g.core.memory;initial=[];returns=[];formats=[];checks=[];pending={};overrides=[];colours=[];hero=m.u32[0x02001624]
                def write(a,data):
                    require(0x02000000<=a and a+len(data)<=0x04000000,'Fullness override outside existing RAM')
                    overrides.append({'address':a,'before':bytes(m[a:a+len(data)]).hex(),'after':data.hex()})
                    for i,v in enumerate(data):m.u8[a+i]=v
                item=bytearray(120);struct.pack_into('<I',item,0,0xC8000000);item[4:6]=b'\1\1';item[8]=bytes(m[0x020013D0:0x020014D0]).index(177);write(0x0200DF28,item);at=0x02003BAC+177*20;write(at,struct.pack('<I',m.u32[at]|0x40000000))
                def callback(e):
                    a,r=e['address'],e['registers']
                    if a==0x08015848 and not initial:
                        write(hero+8,struct.pack('<I',m.u32[hero+8]&~0x800));write(hero+0x54,struct.pack('<II',maximum*256,maximum*256))
                        args=(hero,1,30,0);initial.append(e|{'guard':bytes(m[r[13]:r[13]+32]).hex()})
                        for i,v in enumerate(args):g.core.cpu.gprs[i]=v
                        overrides.append({'event':e,'arguments_after':args,'pc_after':entry+0x08000000});require(g.core._core.writeRegister(g.core._core,b'pc',ffi.new('uint32_t*',entry+0x08000000)),'Fullness dispatch failed');return
                    if not initial or returns:return
                    if a==0x08000FB8 and r[14]==formatted+0x08000001:
                        require(r[1]==row['offset']+0x08000000 and r[0]==r[13] and r[2]==final,'Native fullness source/output/value differs')
                        regs=list(r)
                        if field in ('maximum-decimal','zero-decimal'):
                            regs[2]=0x7FFFFFFF if field=='maximum-decimal' else 0;g.core.cpu.gprs[2]=regs[2];overrides.append({'event':e,'register':2,'after':regs[2],'reason':'Formatter-only nonnegative decimal boundary; native state remains bounded0..200.'})
                        payload=native_format(bytes.fromhex(row['encoded_hex']),[regs[2]],m);require(len(payload)<=row['maximum_bytes']<=256,'Fullness decimal overflow');pending.update(regs=regs,payload=payload,guard=bytes(m[r[0]+256:r[0]+272]));checks.append(ActionCheck(g,payload[:-1],queued+0x08000000,256,pending['guard']))
                    if a==formatted+0x08000000 and pending:
                        old=pending['regs'];p=old[0];payload=pending['payload'];require(bytes(m[p:p+len(payload)])==payload and bytes(m[p+256:p+272])==pending['guard'] and r[4:12]==old[4:12] and r[13]==old[13],'Fullness formatter/guard/ABI differs');formats.append({'id':row['id'],'hex':payload.hex(),'bytes':len(payload),'capacity':256,'guard_abi_match':True});pending.clear()
                    if checks and not(checks[0].complete and checks[0].returned):
                        duplicate=False
                        if a==0x08001C14 and checks[0].pending_glyph:
                            bank=m.u16[m.u32[r[5]+12]]>>12;c=m.u16[0x05000000+2*(bank*16+m.u8[0x020000C2])];rgb=tuple(((c>>s)&31)*255//31 for s in (0,5,10))
                            glyph=checks[0].pending_glyph;key=(r[0],r[4],r[5],r[13],r[14],rgb)
                            duplicate='probe_preparation' in glyph
                            if duplicate:require(glyph['probe_preparation']==key,'Repeated glyph preparation differs')
                            else:glyph['probe_preparation']=key;colours.append(rgb)
                        if not duplicate:checks[0].callback(e)
                    if a==end+0x08000000:
                        old=initial[0]['registers'];require(r[4:12]==old[4:12] and r[13]==old[13] and r[0]==old[14] and bytes(m[r[13]:r[13]+32]).hex()==initial[0]['guard'],'Fullness caller changed');returns.append(e)
                with Debugger(g,callback,max_events=100000) as debug:
                    for a in (0x08015848,0x08000FB8,formatted+0x08000000,(queued&~1)+0x08000000,end+0x08000000,0x0801588C,0x080158CE,0x08001BC4,0x08001C14,0x08001C68):debug.breakpoint(a)
                    g.press('B',hold=8,wait=30);g.press('A',wait=30);g.press('A',wait=30);actions=[]
                    for i in range(7):
                        n=m.u16[0x0200CDD0+i*2]
                        if not n:break
                        actions.append(n)
                    require(13 in actions,'Fullness Drink trigger absent')
                    for _ in range(actions.index(13)):g.press('DOWN',wait=20)
                    g.capture('menu');g.press('A',wait=0)
                    for _ in range(1200):
                        g.frames(1)
                        if returns:break
                    require(len(initial)==len(returns)==len(checks)==len(formats)==1 and checks[0].complete and checks[0].returned and not pending,'Fullness route incomplete: '+name)
                    require(m.u32[hero+0x58]==final*256 and m.u32[hero+0x54]==(final if owner!='increase' else maximum)*256,'Fullness native state differs')
                    g.frames(3);pic=g.capture('message');c=checks[0];pixels=0;require(len(c.draws)==len(colours),'Fullness colour coverage differs')
                    for d,colour in zip(c.draws,colours):
                        require(c.queued['one_line'] and d['y']==c.draws[0]['y'],'Fullness should fit one native line');glyph,_=c.glyph_record(d['code'])
                        for y,line in enumerate(glyph['rows']):
                            for x,bit in enumerate(line):
                                px=m.u8[c.window]+d['x']+x;py=m.u8[c.window+1]+d['y']*16+y;require((pic.getpixel((px,py))==colour)==(bit=='#'),'Fullness final pixels differ');pixels+=1
                require(g.snapshot().battery==fixture.battery,'Fullness wrote save')
                results.append({'case':name,'owner':owner,'field':field,'id':row['id'],'inputs':g.inputs,'overrides':overrides,'formats':formats,'queue':c.queued,'native_state_checked':True,'caller_guard_abi_preserved':True,'visible_pixels_checked':pixels,'images':{p:digest((g.output/p).read_bytes()) for p in ('menu.png','message.png')}})
    report={'passed':True,'rom_sha256':digest(rom),'cases':results,'scope':'Three native callers and actual fullness changes including zero and200. Controlled Drink dispatch with native item/actor state. Zero and maximum nonnegative integer arguments are formatter-only probes. All messages retain one line and exact compact digits; adjacent guards, ABI and battery are checked. Acquisition and unrelated eating paths remain separate.'}
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print('Fullness:',len(results),'passed',flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,default=ROOT/'build/food-effects-prototype');a=p.parse_args();run(a.source)
