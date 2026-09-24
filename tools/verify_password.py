"""Native password paging, complete glyphs, unchanged kana format and caller guards."""
import argparse,json,struct
from pathlib import Path
import mgba.log
from tools.dialogue_checks import TextChecks
from tools.emulator import Session,Debugger,ffi
from tools.rom import ROOT,digest,load_base,require
from tools.verify_service_ui import cstring


def run(source=ROOT/'build/password-prototype'):
    out=source/'password-validation';mgba.log.silence()
    rom=(source/'torneko-2-english.gba').read_bytes();build=json.loads((source/'build.json').read_text())
    require(digest(rom)==build['output_sha256'],'Stale password ROM')
    base=load_base()
    for start,end in ((0x5791C,0x57A44),(0x57A4C,0x57C00),(0x154494,0x154594)):
        require(rom[start:end]==base[start:end],'Native password code/alphabet changed')
    from tools import verify_player_status_prototype as status
    previous=status.OUT
    try:status.OUT=out;fixture=status.ready(rom,build)
    finally:status.OUT=previous
    cases=[]
    for index,(trips,depth,cleared,frames,button) in enumerate(((0,0,False,0,'B'),(50,127,True,215999,'A'),(51,1,True,216000,'B'),(32767,255,True,2147483647,'A'))):
        name='password-'+str(index);print(name,flush=True)
        with Session(rom,out/name) as g:
            g.restore(fixture);m=g.core.memory
            rows={r['offset']+0x08000000:r for r in build['password']['entries']}
            c=TextChecks(g,rows);initial=[];returns=[];ready=[];waits=[];draws=[];formats=[];pending={};overrides=[];images=[];pixels=0
            def write(a,data):
                overrides.append({'address':a,'before':bytes(m[a:a+len(data)]).hex(),'after':data.hex()})
                for i,v in enumerate(data):m.u8[a+i]=v
            def callback(e):
                a,r=e['address'],e['registers']
                if a==0x08008F4C and not initial:
                    initial.append(e|{'guard':bytes(m[r[13]:r[13]+32]).hex()})
                    write(0x02002C48,struct.pack('<I',(m.u32[0x02002C48]&~0x40000000)|(0x40000000 if cleared else 0)))
                    write(0x02002C50,struct.pack('<hB',trips,depth));write(0x02002C30,struct.pack('<I',frames))
                    g.core.cpu.gprs[0]=0x02002C44;overrides.append({'event':e,'pc_after':0x0805791C,'r0_after':0x02002C44})
                    require(g.core._core.writeRegister(g.core._core,b'pc',ffi.new('uint32_t*',0x0805791C)),'Password redirect failed')
                if not initial or returns:return
                if a==0x08000FB8 and r[14]==0x080579E3:
                    require(not pending and r[0]==r[13]+28,'Password formatter output changed')
                    args=[r[2],r[3]]+[m.u32[r[13]+i*4] for i in range(7)]
                    alphabet=m.u32[0x08057A40];indices=m.u32[m.u32[0x08057A38]]
                    expected_args=[m.u32[alphabet+m.u8[indices+i]*4] for i in (0,5,1,6,2,7,3,8,4)]
                    require(args==expected_args,'Password kana permutation differs')
                    payload=b'\x14'+b''.join(cstring(m,p) for p in args)+b'\0'
                    require(len(payload)==20 and cstring(m,r[1])==b'\x14'+b'%s'*9,'Password native format differs')
                    pending.update(event=e,args=args,payload=payload,output=r[0],before=bytes(m[r[0]:r[0]+36]))
                if a==0x080579E2:
                    p=pending;require(p,'Missing password formatter entry');before=p['event']['registers'];data=p['payload'];target=p['output']
                    require(bytes(m[target:target+len(data)])==data and bytes(m[target+len(data):target+36])==p['before'][len(data):] and r[4:12]==before[4:12] and r[13]==before[13],'Password native output/tail/guard/ABI changed')
                    c.resources[target]={'id':'password.generated-kana','encoded_hex':data.hex(),'layout':{'pages':[['native kana']]}}
                    formats.append({'arguments':p['args'],'encoded_hex':data.hex(),'bytes':len(data),'capacity':32,'guard_tail_abi_match':True});pending.clear()
                if a==0x08001750:draws[:]=[d for d in draws if d['window']!=r[0]]
                if a==0x08001BC4 and c.active:
                    w=r[0];key=(w,r[1],r[13],r[14],m.u8[w+2],m.u8[w+3])
                    if not draws or draws[-1]['key']!=key:
                        draws.append({'key':key,'window':w,'code':r[1],'x':m.u8[w+2],'y':m.u8[w+3],'origin':[m.u8[w],m.u8[w+1]],'foreground':m.u8[0x020000C2],'bank':m.u16[m.u32[w+12]]>>12})
                if a==0x080023A0 and c.active:waits.append(e)
                c.callback(e)
                if a==0x08057A24:ready.append(e)
                if a==0x08057A8E:
                    before=initial[0]['registers']
                    require(r[4:12]==before[4:12] and r[13]==before[13] and r[0]==before[14] and bytes(m[r[13]:r[13]+32]).hex()==initial[0]['guard'],'Password caller ABI/guard changed')
                    returns.append(e)
            def capture(label):
                nonlocal pixels
                g.frames(3);picture=g.capture(label);images.append(label+'.png')
                require(draws,'Missing password glyphs')
                for d in draws:
                    glyph,_=c.glyph_record(d['code']);colour=m.u16[0x05000000+2*(16*d['bank']+d['foreground'])]
                    rgb=tuple(((colour>>s)&31)*255//31 for s in (0,5,10))
                    for y,line in enumerate(glyph['rows']):
                        for x,bit in enumerate(line):
                            px=d['origin'][0]+d['x']+x;py=d['origin'][1]+d['y']*16+y
                            require((picture.getpixel((px,py))==rgb)==(bit=='#'),'Password visible glyph mismatch: '+repr((name,label,px,py,hex(d['code']))))
                            pixels+=1
            with Debugger(g,callback,max_events=150000) as debug:
                for a in set(TextChecks.ADDRESSES+(0x08008F4C,0x08000FB8,0x080579E2,0x08057A24,0x08057A8E,0x08001750)):debug.breakpoint(a)
                g.press('A',hold=1,wait=0);handled=0
                for tick in range(2400):
                    if ready:break
                    if len(waits)>handled:
                        capture('page-'+str(handled));handled=len(waits);g.press('A',hold=1,wait=0)
                    else:g.frames(1)
                require(ready and not c.active and len(formats)==1,'Password text did not finish')
                capture('page-'+str(handled));g.press(button,hold=1,wait=0)
                for tick in range(120):
                    if returns:break
                    g.frames(1)
            notice=next(r for r in build['password']['entries'] if r['literal']==0x57A48)
            require(len(returns)==1 and len(images)==len(notice['layout']['pages']) and {r['id'] for r in c.reads}=={'password.heading','password.notice','password.generated-kana'} and g.snapshot().battery==fixture.battery,'Password coverage/close/save differs')
            cases.append({'case':name,'trips':trips,'depth':depth,'cleared':cleared,'frame_counter':frames,'close_button':button,'reads':c.reads,'formats':formats,'page_waits':waits,'overrides':overrides,'inputs':g.inputs,'return':returns[0],'visible_pixels_checked':pixels,'images':{p:digest((g.output/p).read_bytes()) for p in images}})
    (out/'report.json').write_text(json.dumps({'passed':True,'rom_sha256':digest(rom),'cases':cases,'scope':'Controlled native password screen entry and native code generation at trip/depth/flag/time boundaries. Every page, heading and retained nine-kana code has final-screen pixel checks; original32-byte format output, tail/guard/ABI and original64/128/224px windows retained. A/B close and unchanged battery verified. Ordinary unlocking and any historical external promotion are not validated.'},indent=2)+'\n');print('Password:',len(cases),'cases passed',flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,default=ROOT/'build/password-prototype');a=p.parse_args();run(a.source)
