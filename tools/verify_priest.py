"""Controlled priest-owned paged reads and original256-byte service formats."""
import argparse,json,struct
from pathlib import Path
import mgba.log
from tools.dialogue_checks import TextChecks,player_layout_cases
from tools.emulator import Session,Debugger,ffi
from tools.name_entry import HERO
from tools.rom import ROOT,digest,require
from tools.verify_result_ui import native_format


def run(source=ROOT/'build/priest-prototype'):
    out=source/'priest-validation';mgba.log.silence()
    rom=(source/'torneko-2-english.gba').read_bytes();build=json.loads((source/'build.json').read_text())
    require(digest(rom)==build['output_sha256'],'Stale priest ROM')
    from tools import verify_player_status_prototype as status
    previous=status.OUT
    try:status.OUT=out;fixture=status.ready(rom,build)
    finally:status.OUT=previous
    rows={r['offset']+0x08000000:r for r in build['priest']['entries']};cases=[]
    for row in rows.values():
        if row['table_offset']==0x4DC:continue
        formatted=not row['layout']['direct_rom_stream']
        names=player_layout_cases() if '{player}' in row['english'] else [('native',None)]
        for label,player in names:
            for amount in ((0,32767) if formatted else (None,)):
                name=row['id']+'-'+label+('-'+str(amount) if amount is not None else '')
                print('Priest:',name,flush=True)
                with Session(rom,out/name) as g:
                    g.restore(fixture);m=g.core.memory;c=TextChecks(g,dict(rows))
                    initial=[];returns=[];waits=[];draws=[];formats=[];pending={};overrides=[];images=[];pixels=0;redirected=[]
                    hero=m.u32[0x02001624];gold=m.u32[hero+0x60];inventory=bytes(m[0x0200DF28:0x0200E888])
                    def write(a,data):
                        overrides.append({'address':a,'before':bytes(m[a:a+len(data)]).hex(),'after':data.hex()})
                        for i,v in enumerate(data):m.u8[a+i]=v
                    def callback(e):
                        a,r=e['address'],e['registers']
                        if a==0x08008F4C and not initial:
                            initial.append(e|{'guard':bytes(m[r[13]:r[13]+32]).hex()})
                            actor=next(m.u32[0x02001624+4*i] for i in range(1,56) if 0x02000000<=m.u32[0x02001624+4*i]<0x0203ff00 and m.u32[m.u32[0x02001624+4*i]+8]&0x80000000)
                            write(actor+0x91,b'\x7f');write(actor+0xA7,b'\0')
                            if player:write(HERO,player.ljust(16,b'\0'))
                            entry=0x0801AE18 if formatted else 0x0801AAFC
                            g.core.cpu.gprs[0]=actor;overrides.append({'event':e,'pc_after':entry,'r0_after':actor})
                            require(g.core._core.writeRegister(g.core._core,b'pc',ffi.new('uint32_t*',entry)),'Priest redirect failed')
                        if not initial or returns:return
                        if a==0x08000FB8 and formatted and r[14]==0x0801AE3F and not redirected:
                            target=row['offset']+0x08000000;overrides.append({'event':e,'r1_after':target,'r2_after':amount})
                            g.core.cpu.gprs[1]=target;g.core.cpu.gprs[2]=amount
                            regs=list(r);regs[1:3]=[target,amount];redirected.append(e)
                            payload=native_format(bytes.fromhex(row['encoded_hex']),[amount],m)
                            require(regs[0]==regs[13]+4 and len(payload)<=row['layout']['maximum_formatted_bytes']<=256,'Priest format ownership differs')
                            pending.update(regs=regs,payload=payload,guard=bytes(m[regs[0]+len(payload):regs[0]+272]))
                        if a==0x0801AE3E and pending:
                            before=pending['regs'];payload=pending['payload'];target=before[0]
                            require(bytes(m[target:target+len(payload)])==payload and bytes(m[target+len(payload):target+272])==pending['guard'] and r[4:12]==before[4:12] and r[13]==before[13],'Priest format tail/guard/ABI differs')
                            c.resources[target]=row|{'encoded_hex':payload.hex()};formats.append({'id':row['id'],'amount':amount,'bytes':len(payload),'capacity':256,'guard_tail_abi_match':True});pending.clear()
                        if a==0x08015A18 and not formatted and not redirected:
                            target=row['offset']+0x08000000;overrides.append({'event':e,'r0_after':target});g.core.cpu.gprs[0]=target;redirected.append(e)
                        if a==0x08001750:draws[:]=[d for d in draws if d['window']!=r[0]]
                        if a==0x08001BC4 and c.active:
                            w=r[0];key=(w,r[1],r[13],r[14],m.u8[w+2],m.u8[w+3])
                            if not draws or draws[-1]['key']!=key:draws.append({'key':key,'window':w,'code':r[1],'x':m.u8[w+2],'y':m.u8[w+3],'origin':[m.u8[w],m.u8[w+1]],'foreground':m.u8[0x020000C2],'bank':m.u16[m.u32[w+12]]>>12})
                        if a==0x080023A0 and c.active:waits.append(e)
                        c.callback(e)
                        if a==(0x0801AF1C if formatted else 0x0801AE04):
                            before=initial[0]['registers'];retreg=1
                            require(r[4:12]==before[4:12] and r[13]==before[13] and r[retreg]==before[14] and bytes(m[r[13]:r[13]+32]).hex()==initial[0]['guard'],'Priest caller ABI/guard differs');returns.append(e)
                    def capture():
                        nonlocal pixels
                        g.frames(3);tag='page-'+str(len(images));pic=g.capture(tag);images.append(tag+'.png');require(draws,'No priest glyphs')
                        for d in draws:
                            glyph,_=c.glyph_record(d['code']);colour=m.u16[0x05000000+2*(16*d['bank']+d['foreground'])];rgb=tuple(((colour>>s)&31)*255//31 for s in (0,5,10))
                            for y,line in enumerate(glyph['rows']):
                                for x,bit in enumerate(line):
                                    px=d['origin'][0]+d['x']+x;py=d['origin'][1]+d['y']*16+y
                                    require((pic.getpixel((px,py))==rgb)==(bit=='#'),'Priest final pixels differ: '+repr((name,tag,px,py,hex(d['code']))));pixels+=1
                    with Debugger(g,callback,max_events=160000) as debug:
                        for a in set(TextChecks.ADDRESSES+(0x08008F4C,0x08000FB8,0x0801AE3E,0x08015A18,0x08001750,0x0801AF1C,0x0801AE04)):debug.breakpoint(a)
                        g.press('A',hold=1,wait=0);handled=0;final=False
                        for tick in range(2400):
                            if returns:break
                            if len(waits)>handled:
                                capture();handled=len(waits);g.press('B',hold=1,wait=0)
                            elif c.completed(row['id']) and not final:
                                capture();final=True;g.press('B',hold=1,wait=0)
                            elif final and tick%20==0:g.press('B',hold=1,wait=0)
                            else:g.frames(1)
                    require(len(returns)==1 and not c.active and c.completed(row['id']) and len(images)==len(row['layout']['pages']),'Priest pages/return incomplete')
                    require(len(formats)==int(formatted) and m.u32[hero+0x60]==gold and bytes(m[0x0200DF28:0x0200E888])==inventory and g.snapshot().battery==fixture.battery,'Declined priest probe changed inventory/gold/save')
                    cases.append({'case':name,'id':row['id'],'amount':amount,'name_variant':label,'reads':c.reads,'formats':formats,'overrides':overrides,'inputs':g.inputs,'return':returns[0],'visible_pixels_checked':pixels,'images':{p:digest((g.output/p).read_bytes()) for p in images}})
    (out/'report.json').write_text(json.dumps({'passed':True,'rom_sha256':digest(rom),'cases':cases,'scope':'Controlled priest-owned root refusal and original256-byte service formatter arguments. All24 non-menu source bindings, every page and name/numeric bounds, colours, final-screen glyph pixels, tails/guards/caller ABI and unchanged inventory/gold/battery. Root menu, service outcomes and ordinary acquisition are separately validated.'},indent=2)+'\n');print('Priest:',len(cases),'cases passed',flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,default=ROOT/'build/priest-prototype');a=p.parse_args();run(a.source)
