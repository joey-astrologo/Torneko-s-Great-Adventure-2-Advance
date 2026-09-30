"""All native species selectors and field bounds for the owned announcement reader."""
import argparse,json,struct
from pathlib import Path
import mgba.log
from tools.compact_font import encode
from tools.emulator import Session,Debugger,ffi
from tools.monster_announcement_text import selectors
from tools.rom import ROOT,digest,load_base,require
from tools.verify_inventory_action_prototype import ActionCheck
from tools.verify_service_ui import materialize


def run(source=ROOT/'build/monster-announcement-prototype'):
    out=source/'monster-announcement-validation';mgba.log.silence()
    rom=(source/'torneko-2-english.gba').read_bytes();build=json.loads((source/'build.json').read_text())
    require(digest(rom)==build['output_sha256'],'Stale announcement ROM')
    from tools import verify_player_status_prototype as status
    previous=status.OUT
    try:status.OUT=out;fixture=status.ready(rom,build)
    finally:status.OUT=previous
    rows={r['table_offset']:r for r in build['monster_announcements']['entries']};selected=selectors(load_base())
    configs=[(i,slot,'native') for i,slot in selected.items()]
    configs += [(r['actor_ids'][0],slot,field) for slot,r in rows.items() for field in ('maximum-width','maximum-bytes','coloured')]
    results=[]
    for ident,slot,field in configs:
        name=f'actor-{ident}-{field}';row=rows[slot];print('Monster announcement:',name,flush=True)
        with Session(rom,out/name) as g:
            g.restore(fixture);m=g.core.memory;initial=[];returns=[];formats=[];checks=[];pending={};overrides=[];colours=[];skips=[]
            def write(a,data):
                overrides.append({'address':a,'before':bytes(m[a:a+len(data)]).hex(),'after':data.hex()})
                for i,v in enumerate(data):m.u8[a+i]=v
            item=bytearray(120);struct.pack_into('<I',item,0,0xC8000000);item[4:6]=b'\1\1';item[8]=bytes(m[0x020013D0:0x020014D0]).index(177)
            write(0x0200DF28,item);definition=0x02003BAC+177*20;write(definition,struct.pack('<I',m.u32[definition]|0x40000000))
            def jump(e,address):
                overrides.append({'event':e,'pc_after':address})
                require(g.core._core.writeRegister(g.core._core,b'pc',ffi.new('uint32_t*',address)),'Announcement dispatch failed')
            def callback(e):
                a,r=e['address'],e['registers']
                if a==0x08015848 and not initial:
                    actor=next(m.u32[0x02001624+4*i] for i in range(1,56) if 0x02000000<=m.u32[0x02001624+4*i]<0x0203FF00 and m.u32[m.u32[0x02001624+4*i]+8]&0x80000000)
                    write(actor+0x91,bytes([ident]));initial.append(e|{'actor':actor,'guard':bytes(m[r[13]:r[13]+32]).hex()})
                    g.core.cpu.gprs[0]=actor;overrides.append({'event':e,'r0_after':actor});jump(e,0x0802A998)
                if not initial or returns:return
                if a==0x08000FB8 and r[14]==0x0802A9F1:
                    require(r[1]==row['offset']+0x08000000 and r[0]==r[13],'Species selector/message ownership differs: '+repr((name,[hex(v) for v in r[:4]],hex(r[13]))))
                    regs=list(r)
                    if field!='native':
                        raw=encode('W'*31 if field=='maximum-width' else 'i'*31 if field=='maximum-bytes' else 'Monster')
                        if field=='coloured':raw=b'\x03\x05'+raw[:-1]+b'\x05\0'
                        write(0x02008D08,raw.ljust(64,b'\0'));g.core.cpu.gprs[2]=0x02008D08;regs[2]=0x02008D08
                        overrides.append({'event':e,'r2_after':0x02008D08,'reason':'Existing64-byte name-plus-level scratch; ordinary names may be immutable ROM pointers.'})
                    payload=materialize(bytes.fromhex(row['encoded_hex']),[regs[2]],m)
                    require(len(payload)<=row['maximum_bytes']<=256,'Announcement expansion overflow')
                    pending.update(regs=regs,payload=payload,guard=bytes(m[r[0]+256:r[0]+272]),actor=bytes(m[regs[2]:regs[2]+64]))
                    checks.append(ActionCheck(g,payload[:-1],0x0802A9F9,256,pending['guard']))
                if a==0x0802A9F0 and pending:
                    old=pending['regs'];p=old[0];payload=pending['payload']
                    require(bytes(m[p:p+len(payload)])==payload and bytes(m[p+256:p+272])==pending['guard'] and bytes(m[old[2]:old[2]+64])==pending['actor'] and r[4:12]==old[4:12] and r[13]==old[13],'Announcement output/name/guard/ABI differs')
                    formats.append({'id':row['id'],'hex':payload.hex(),'bytes':len(payload),'capacity':256,'actor_hex':pending['actor'].hex(),'guard_abi_match':True});pending.clear()
                if checks and not (checks[0].complete and checks[0].returned):
                    duplicate=False
                    if a==0x08001C14 and checks[0].pending_glyph:
                        bank=m.u16[m.u32[r[5]+12]]>>12;colour=m.u16[0x05000000+2*(bank*16+m.u8[0x020000C2])]
                        rgb=tuple(((colour>>s)&31)*255//31 for s in (0,5,10))
                        glyph=checks[0].pending_glyph;key=(r[0],r[4],r[5],r[13],r[14],rgb)
                        duplicate='probe_preparation' in glyph
                        if duplicate:require(glyph['probe_preparation']==key,'Repeated announcement glyph preparation differs')
                        else:glyph['probe_preparation']=key;colours.append(rgb)
                    if not duplicate:checks[0].callback(e)
                if a==0x0802A9F8:
                    require(checks and checks[0].complete and checks[0].returned,'Announcement has not completed before effects')
                    skips.append(e);jump(e,0x0802AB76)
                if a==0x0802AB80:
                    old=initial[0]['registers'];require(r[4:12]==old[4:12] and r[13]==old[13] and r[0]==old[14] and bytes(m[r[13]:r[13]+32]).hex()==initial[0]['guard'],'Announcement caller ABI/guard differs');returns.append(e)
            with Debugger(g,callback,max_events=80000) as debug:
                for a in (0x08015848,0x08000FB8,0x0802A9F0,0x0801588C,0x080158CE,0x0802A9F8,0x0802AB80,0x08001BC4,0x08001C14,0x08001C68):debug.breakpoint(a)
                g.press('B',hold=8,wait=30);g.press('A',wait=30);g.press('A',wait=30)
                actions=[]
                for i in range(7):
                    n=m.u16[0x0200CDD0+i*2]
                    if not n:break
                    actions.append(n)
                require(13 in actions,'Native Life herb Drink unavailable')
                for _ in range(actions.index(13)):g.press('DOWN',wait=20)
                g.capture('menu');g.press('A',wait=0)
                for _ in range(900):
                    g.frames(1)
                    if returns:break
                require(len(initial)==len(returns)==len(checks)==len(formats)==len(skips)==1 and checks[0].complete and checks[0].returned and not pending,'Announcement route incomplete')
                g.frames(3);pic=g.capture('message');c=checks[0];visible=[];pixels=0
                require(len(c.draws)==len(colours),'Announcement colours incomplete')
                for draw,colour in zip(c.draws,colours):
                    if draw['native_scroll']:
                        shift=draw['key'][-1]-draw['y'];require(shift>0,'Unexpected announcement scroll')
                        for old in visible:old['final_y']-=shift
                    visible.append(draw|{'final_y':draw['y'],'colour':colour})
                for d in visible:
                    require(d['final_y']>=0,'Announcement scrolled out of view');glyph,_=c.glyph_record(d['code'])
                    for y,line in enumerate(glyph['rows']):
                        for x,bit in enumerate(line):
                            px=m.u8[0x02000000]+d['x']+x;py=m.u8[0x02000001]+d['final_y']*16+y
                            require((pic.getpixel((px,py))==d['colour'])==(bit=='#'),'Announcement final pixels differ: '+repr((name,px,py)));pixels+=1
            require(g.snapshot().battery==fixture.battery,'Announcement wrote battery')
            results.append({'case':name,'id':row['id'],'actor_id':ident,'table_offset':slot,'field':field,'overrides':overrides,'inputs':g.inputs,'formats':formats,'queue':checks[0].queued,'visible_pixels_checked':pixels,'caller_guard_abi_preserved':True,'effect_body_explicitly_skipped':True,'images':{p:digest((g.output/p).read_bytes()) for p in ('menu.png','message.png')}})
    report={'passed':True,'rom_sha256':digest(rom),'cases':results,'scope':'Native Drink opens a visible message window, then controlled dispatch to CPU0802A998 supplies an existing actor with each of45 nonzero species IDs. The unchanged native species definition selects its message; every one of24 formats also receives186px/63-byte and colour bounds. Exact output, actor scratch,256-byte guard, queue/caller ABI, final visible pixels and unchanged battery pass. The subsequent ability body is explicitly skipped at its native epilogue. No natural encounters or spell/effect outcomes are claimed by this announcement verifier.'}
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print('Monster announcements:',len(results),'passed',flush=True)
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,default=ROOT/'build/monster-announcement-prototype');a=p.parse_args();run(a.source)
