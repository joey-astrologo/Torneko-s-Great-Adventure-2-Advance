"""All48 record rows,11 ranks, state colours, numeric bounds and native page navigation."""
import argparse,json,struct
from pathlib import Path
import mgba.log
from tools.dialogue_checks import TextChecks
from tools.emulator import Session,Debugger,ffi
from tools.rom import ROOT,digest,require
from tools.verify_result_ui import native_format


def run(source=ROOT/'build/records-prototype'):
    out=source/'records-validation';mgba.log.silence()
    rom=(source/'torneko-2-english.gba').read_bytes();build=json.loads((source/'build.json').read_text())
    require(digest(rom)==build['output_sha256'],'Stale records ROM')
    from tools import verify_player_status_prototype as status
    previous=status.OUT
    try:status.OUT=out;fixture=status.ready(rom,build)
    finally:status.OUT=previous
    rows={r['offset']+0x08000000:r for r in build['records']['entries']};cases=[]
    configs=[('rank-'+str(i),'rank',i) for i in range(11)]+[(s,s,None) for s in ('maximum','minimum','locked','grey')]
    for name,mode,rank in configs:
        print('Records:',name,flush=True)
        with Session(rom,out/name) as g:
            g.restore(fixture);m=g.core.memory;c=TextChecks(g,{})
            initial=[];returns=[];ready=[];pending={};formats=[];draws=[];overrides=[];images=[];pixels=0;page_indices=[]
            def write(a,data):
                overrides.append({'address':a,'before':bytes(m[a:a+len(data)]).hex(),'after':data.hex()})
                for i,v in enumerate(data):m.u8[a+i]=v
            def callback(e):
                a,r=e['address'],e['registers']
                if a==0x08008F4C and not initial:
                    initial.append(e|{'guard':bytes(m[r[13]:r[13]+32]).hex()})
                    data=bytearray(0x34)
                    if mode in ('maximum','minimum'):
                        struct.pack_into('<II',data,0,0xFFFFFFFF,0xFFFFFFFF)
                    elif mode=='grey':struct.pack_into('<I',data,0,0x100)
                    elif mode=='rank':
                        first=(0x100 if rank>=8 else 0)|(0x200000 if rank>=10 else 0)
                        second=sum(1<<(24+i) for i in range(min(rank,7)))
                        struct.pack_into('<II',data,0,first,second)
                        if rank>=9:struct.pack_into('<h',data,12,1000)
                    if mode=='maximum':
                        for offset in range(12,44,2):struct.pack_into('<h',data,offset,32767)
                        for offset in (44,48):struct.pack_into('<I',data,offset,2147483647)
                    write(0x02002C44,data);write(0x02002C30,struct.pack('<I',2147483647 if mode=='maximum' else 215999 if mode=='minimum' else 0))
                    g.core.cpu.gprs[0]=0x02002C44;overrides.append({'event':e,'pc_after':0x0805734C,'r0_after':0x02002C44})
                    require(g.core._core.writeRegister(g.core._core,b'pc',ffi.new('uint32_t*',0x0805734C)),'Records redirect failed')
                if not initial or returns:return
                if a==0x08057424 and mode=='rank':require(r[4]==rank,'Native merchant rank setup differs: '+repr((rank,r[4])))
                if a==0x08001750:draws[:]=[d for d in draws if d['window']!=r[0]]
                if a==0x08000FB8 and r[1] in rows:
                    row=rows[r[1]];args=r[2:4]+[m.u32[r[13]+4*i] for i in range(2)]
                    if row.get('literal')==0x57500:
                        timer=m.u32[0x02002C30];require(args[:2]==[timer//216000,(timer//3600)%60],'Record play-time fields differ')
                    payload=native_format(bytes.fromhex(row['encoded_hex']),args,m)
                    require(len(payload)<=row['maximum_bytes']<=128,'Record formatter exceeds128bytes: '+row['id'])
                    ret=r[14]&~1;require(ret not in pending,'Recursive record formatter')
                    pending[ret]=(r,row,payload,bytes(m[r[0]+len(payload):r[0]+144]));debug.breakpoint(ret)
                if a in pending:
                    before,row,payload,guard=pending.pop(a);target=before[0]
                    require(bytes(m[target:target+len(payload)])==payload and bytes(m[target+len(payload):target+144])==guard and r[4:12]==before[4:12] and r[13]==before[13],'Record format bytes/tail/guard/ABI changed')
                    c.resources[target]={'id':row['id'],'encoded_hex':payload.hex(),'layout':{'pages':[[row['id']]]}}
                    formats.append({'id':row['id'],'arguments':before[2:4],'encoded_hex':payload.hex(),'capacity':128,'guard_tail_abi_match':True})
                if a==0x080021B4 and r[1] in rows and not rows[r[1]]['printf_kinds']:
                    row=rows[r[1]];c.resources[r[1]]={'id':row['id'],'encoded_hex':row['encoded_hex'],'layout':{'pages':[[row['id']]]}}
                if a==0x080021B4 and not c.active and r[1] in c.resources:
                    payload=bytes.fromhex(c.resources[r[1]]['encoded_hex'])
                    if bytes(m[r[1]:r[1]+len(payload)])!=payload:c.resources.pop(r[1])
                if a==0x08001BC4 and c.active:
                    w=r[0];key=(w,r[1],r[13],r[14],m.u8[w+2],m.u8[w+3])
                    if not draws or draws[-1]['key']!=key:
                        draws.append({'key':key,'window':w,'id':c.active['id'],'code':r[1],'x':m.u8[w+2],'y':m.u8[w+3],'origin':[m.u8[w],m.u8[w+1]],'foreground':m.u8[0x020000C2],'bank':m.u16[m.u32[w+12]]>>12})
                c.callback(e)
                if a==0x08057568:ready.append(e)
                if a==0x0805761C:
                    before=initial[0]['registers']
                    require(r[4:12]==before[4:12] and r[13]==before[13] and r[0]==before[14] and bytes(m[r[13]:r[13]+32]).hex()==initial[0]['guard'],'Record caller ABI/guard changed');returns.append(e)
            def wait_ready(count):
                for tick in range(500):
                    if len(ready)>count and not c.active and not pending:return
                    g.frames(1)
                require(False,'Records panel did not finish: '+name)
            def capture(label):
                nonlocal pixels
                g.frames(3);picture=g.capture(label);images.append(label+'.png');page_indices.append(m.u32[0x02011BD0])
                require(draws,'No visible record text')
                for d in draws:
                    glyph,_=c.glyph_record(d['code']);colour=m.u16[0x05000000+2*(16*d['bank']+d['foreground'])]
                    rgb=tuple(((colour>>s)&31)*255//31 for s in (0,5,10))
                    for y,line in enumerate(glyph['rows']):
                        for x,bit in enumerate(line):
                            px=d['origin'][0]+d['x']+x;py=d['origin'][1]+d['y']*16+y
                            require((picture.getpixel((px,py))==rgb)==(bit=='#'),'Record visible glyph mismatch: '+repr((name,label,d['id'],px,py,hex(d['code']))));pixels+=1
            with Debugger(g,callback,max_events=300000) as debug:
                for a in set(TextChecks.ADDRESSES+(0x08008F4C,0x08000FB8,0x08001750,0x08057424,0x08057568,0x0805761C)):debug.breakpoint(a)
                g.press('A',hold=1,wait=0);wait_ready(0);capture('page-0')
                if mode!='rank':
                    for page in range(1,8):
                        count=len(ready);g.press('RIGHT',hold=1,wait=0);wait_ready(count)
                        require(m.u32[0x02011BD0]==page,'Record next-page failed: '+repr((page,m.u32[0x02011BD0])));capture('page-'+str(page))
                    g.press('RIGHT',wait=20);require(m.u32[0x02011BD0]==7,'Record last-page limit changed')
                    count=len(ready);g.press('LEFT',hold=1,wait=0);wait_ready(count);require(m.u32[0x02011BD0]==6,'Record previous-page failed');capture('back-6')
                g.press('B',hold=1,wait=0)
                for tick in range(120):
                    if returns:break
                    g.frames(1)
            require(len(returns)==1 and not pending and not c.active and g.snapshot().battery==fixture.battery,'Records close/save changed')
            if mode in ('maximum','minimum'):require({f'records.row.{i}' for i in range(48)}<={r['id'] for r in c.reads},'Record48-row coverage incomplete')
            cases.append({'case':name,'mode':mode,'rank':rank,'reads':c.reads,'formats':formats,'overrides':overrides,'inputs':g.inputs,'page_indices':page_indices,'return':returns[0],'visible_pixels_checked':pixels,'images':{p:digest((g.output/p).read_bytes()) for p in images}})
    (out/'report.json').write_text(json.dumps({'passed':True,'rom_sha256':digest(rom),'cases':cases,'scope':'Controlled existing record flags/statistics with native rank calculation and original navigation. All48 rows,11 ranks, hidden/grey/white states, zero/maximum numeric records and time boundary, right-aligned values,128-byte format guards/ABI, complete final-screen pixels and A-menu/B-close flow. Original224px windows and battery retained. Ordinary achievement acquisition/persistence remains separate.'},indent=2)+'\n');print('Records:',len(cases),'cases passed',flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,default=ROOT/'build/records-prototype');a=p.parse_args();run(a.source)
