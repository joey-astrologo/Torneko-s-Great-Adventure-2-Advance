"""Native record-menu labels, cursor wrap, child dispatch and repeated reopening."""
import argparse,json,struct
from pathlib import Path
import mgba.log
from tools.dialogue_checks import TextChecks
from tools.emulator import Session,Debugger,ffi
from tools.rom import ROOT,digest,require


def run(source=ROOT/'build/history-menu-prototype'):
    out=source/'history-menu-validation'
    rom=(source/'torneko-2-english.gba').read_bytes();build=json.loads((source/'build.json').read_text())
    require(digest(rom)==build['output_sha256'],'Stale history menu ROM');mgba.log.silence()
    from tools import verify_player_status_prototype as status
    old=status.OUT
    try:status.OUT=out;fixture=status.ready(rom,build)
    finally:status.OUT=old
    rows={r['offset']+0x08000000:r for r in build['history_menu']['entries']}
    cases=[]
    for enabled in (False,True):
        actions=['navigate','scores','populated-scores','records']+(['password'] if enabled else [])
        for action in actions:
            name=('three-' if enabled else 'two-')+action
            print('History menu:',name,flush=True)
            with Session(rom,out/name) as g:
                g.restore(fixture);m=g.core.memory
                resources={p:r|{'layout':{'pages':[[r['id']]]}} for p,r in rows.items()}
                c=TextChecks(g,resources);initial=[];returns=[];overrides=[];draws=[];children=[];password_ready=[];password_waits=[];windows=[];images=[];pixels=0
                def write(a,data):
                    overrides.append({'address':a,'before':bytes(m[a:a+len(data)]).hex(),'after':data.hex()})
                    for i,v in enumerate(data):m.u8[a+i]=v
                def callback(e):
                    a,r=e['address'],e['registers']
                    if a==0x08008F4C and not initial:
                        initial.append(e|{'guard':bytes(m[r[13]:r[13]+32]).hex()})
                        write(0x02002C48,struct.pack('<I',(m.u32[0x02002C48]&~0x40000000)|(0x40000000 if enabled else 0)))
                        if action=='populated-scores':write(0x02004EFC,struct.pack('<IIIIhhhBBBBBB',10120,8,120,3600,15,2,6,3,21,8,5,1,0))
                        g.core.cpu.gprs[0]=0x02002C44
                        overrides.append({'event':e,'pc_after':0x08056BC0,'r0_after':0x02002C44})
                        require(g.core._core.writeRegister(g.core._core,b'pc',ffi.new('uint32_t*',0x08056BC0)),'Menu redirect failed')
                    if not initial or returns:return
                    if a==0x08057A24:password_ready.append(e)
                    if a==0x080023A0 and children and children[-1]['address']==0x0805791C:password_waits.append(e)
                    if a in (0x08056E04,0x0805734C,0x0805791C):children.append(e)
                    if a==0x080021B4 and r[1] in rows and c.active is None:
                        row=rows[r[1]];require(row['rows']==2+int(enabled),'Wrong menu variant')
                        require(m.u8[r[0]+4]*8==64 and m.u8[r[0]+5]==row['rows'],'History menu dimensions changed')
                        windows.append({'window':r[0],'bytes':bytes(m[r[0]:r[0]+24]).hex()});draws.clear()
                    if a==0x08001BC4 and c.active:
                        w=r[0];key=(w,r[1],r[13],r[14],m.u8[w+2],m.u8[w+3])
                        if not draws or draws[-1]['key']!=key:
                            draws.append({'key':key,'code':r[1],'x':m.u8[w+2],'y':m.u8[w+3],
                                          'origin':[m.u8[w],m.u8[w+1]],'foreground':m.u8[0x020000C2],'bank':m.u16[m.u32[w+12]]>>12})
                    c.callback(e)
                    if a==0x08056DFC:
                        before=initial[0]['registers']
                        require(r[4:12]==before[4:12] and r[13]==before[13] and r[1]==before[14] and
                                bytes(m[r[13]:r[13]+32]).hex()==initial[0]['guard'],'History menu caller ABI/guard changed')
                        returns.append(e)
                def wait_for(predicate,why,limit=900):
                    for _ in range(limit):
                        if predicate():return
                        g.frames(1)
                    require(False,why)
                def capture(label):
                    nonlocal pixels
                    g.frames(3);pic=g.capture(label);images.append(label+'.png')
                    require(draws and not c.active,'Menu capture before complete draw')
                    for d in draws:
                        glyph,_=c.glyph_record(d['code']);colour=m.u16[0x05000000+2*(16*d['bank']+d['foreground'])]
                        rgb=tuple(((colour>>shift)&31)*255//31 for shift in (0,5,10))
                        for y,line in enumerate(glyph['rows']):
                            for x,bit in enumerate(line):
                                px=d['origin'][0]+d['x']+x;py=d['origin'][1]+d['y']*16+y
                                require((pic.getpixel((px,py))==rgb)==(bit=='#'),'Menu visible glyph mismatch: '+name)
                                pixels+=1
                    return pic
                with Debugger(g,callback,max_events=100000) as debug:
                    for a in set(TextChecks.ADDRESSES+(0x08008F4C,0x08056DFC,0x08056E04,0x0805734C,0x0805791C,0x08057A24)):debug.breakpoint(a)
                    g.press('A',hold=1,wait=0);wait_for(lambda:bool(c.reads),'Menu failed to open');capture('initial')
                    require(m.u32[0x02011BDC]==0,'Initial menu selection differs')
                    if action=='navigate':
                        for index in range(1,3+int(enabled)):
                            g.press('DOWN',wait=20);require(m.u32[0x02011BDC]==index%(2+int(enabled)),'Menu downward wrap differs');capture('down-'+str(index))
                        g.press('UP',wait=20);require(m.u32[0x02011BDC]==1+int(enabled),'Menu upward wrap differs');capture('up-wrap')
                    else:
                        selection={'scores':0,'populated-scores':0,'records':1,'password':2}[action]
                        for _ in range(selection):g.press('DOWN',wait=20)
                        for repeat in range(2):
                            count=len(c.reads);prior=len(children);prior_password=len(password_ready);handled_pages=len(password_waits);g.press('A',hold=1,wait=30)
                            target={0:0x08056E04,1:0x0805734C,2:0x0805791C}[selection]
                            require(len(children)==prior+1 and children[-1]['address']==target,'Menu child dispatch differs')
                            if selection==2:
                                for tick in range(1800):
                                    if len(password_ready)>prior_password:break
                                    if len(password_waits)>handled_pages:
                                        g.frames(3);page='password-page-'+str(repeat)+'-'+str(handled_pages)
                                        g.capture(page);images.append(page+'.png');handled_pages=len(password_waits)
                                        g.press('A',hold=1,wait=0)
                                    else:g.frames(1)
                                require(len(password_ready)>prior_password,'Password message not ready')
                            g.frames(3)
                            g.capture('child-'+str(repeat));images.append('child-'+str(repeat)+'.png')
                            g.press('B',hold=1,wait=0)
                            wait_for(lambda:len(c.reads)>count and not c.active,'Menu child failed to cancel/reopen')
                            capture('reopened-'+str(repeat))
                            require(m.u32[0x02011BDC]==selection,'Menu selection changed on child return')
                    g.press('B',hold=1,wait=0);wait_for(lambda:bool(returns),'History menu failed to close')
                require(len(returns)==1 and not c.active and g.snapshot().battery==fixture.battery,'Menu close/save failed')
                cases.append({'case':name,'password_enabled':enabled,'action':action,'reads':c.reads,'windows':windows,
                              'children':children,'password_page_waits':password_waits,'overrides':overrides,'inputs':g.inputs,'return':returns[0],
                              'visible_pixels_checked':pixels,'images':{p:digest((g.output/p).read_bytes()) for p in images}})
    (out/'report.json').write_text(json.dumps({'passed':True,'rom_sha256':digest(rom),'cases':cases,
        'scope':'Controlled native records-menu entry and password availability flag. Both original64px windows, '
        'complete English rows, cursor wrap, child dispatch/cancellation and repeated reopening, caller ABI/guards '
        'and unchanged battery pass. Scores child text is separately verified; records/password child text and '
        'ordinary menu access/unlocking remain separate.'},indent=2)+'\n');print('History menu:',len(cases),'cases passed',flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,default=ROOT/'build/history-menu-prototype');a=p.parse_args();run(a.source)
