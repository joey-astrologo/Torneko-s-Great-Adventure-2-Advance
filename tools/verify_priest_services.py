"""Priest menu navigation and native transactions after controlled actor setup."""
import argparse
import json
import struct
from pathlib import Path
import mgba.log
from tools.dialogue_checks import TextChecks
from tools.emulator import Session, Debugger, ffi
from tools.rom import ROOT, digest, require
from tools.verify_result_ui import native_format


def run(source=ROOT/'build/priest-prototype'):
    out=source/'priest-service-validation';mgba.log.silence()
    rom=(source/'torneko-2-english.gba').read_bytes();build=json.loads((source/'build.json').read_text())
    require(digest(rom)==build['output_sha256'],'Stale priest service ROM')
    from tools import verify_player_status_prototype as status
    previous=status.OUT
    try:status.OUT=out;fixture=status.ready(rom,build)
    finally:status.OUT=previous
    rows={r['offset']+0x08000000:r for r in build['priest']['entries']}
    menu=next(r for r in rows.values() if r['table_offset']==0x4DC)
    prices=(1200,300,500,50);offers=(0x4E4,0x4F0,0x4FC,0x508)
    configs=[('navigation',None,'cancel')]
    configs += [(f'{i}-{kind}',i,kind) for i in range(4) for kind in ('decline','no-funds','success')]
    configs += [('curse-none',0,'none'),('poison-none',2,'none'),('hp-full',1,'full'),('hp-cap',1,'cap')]
    results=[]
    for name,choice,kind in configs:
        print('Priest service:',name,flush=True)
        with Session(rom,out/name) as g:
            g.restore(fixture);m=g.core.memory;c=TextChecks(g,dict(rows))
            overrides=[];initial=[];ends=[];formats=[];pending={};draws=[];images={};waits=[];menu_reads=[];selections=[]
            service_entries=[];service_ends=[];exit_requests=[];pixels=0
            hero=m.u32[0x02001624];slot=0x0200DF28
            def write(a,data):
                overrides.append({'address':a,'before':bytes(m[a:a+len(data)]).hex(),'after':data.hex()})
                for i,v in enumerate(data):m.u8[a+i]=v
            def stats():
                return {'gold':m.u32[hero+0x60],'hp':m.u16[hero+0x84],'max_hp':m.u16[hero+0x86],
                        'strength':m.u16[hero+0x76],'max_strength':m.u16[hero+0x78],
                        'inventory':bytes(m[slot:slot+2400]).hex()}
            def callback(e):
                a,r=e['address'],e['registers']
                if a==0x08008F4C and not initial:
                    actor=next(m.u32[0x02001624+4*i] for i in range(1,56) if 0x02000000<=m.u32[0x02001624+4*i]<0x0203ff00 and m.u32[m.u32[0x02001624+4*i]+8]&0x80000000)
                    write(actor+0x91,b'\x7f');write(actor+0xA7,b'\1')
                    write(hero+0x60,struct.pack('<I',0 if kind=='no-funds' else 5000))
                    write(hero+0x84,struct.pack('<HH',500 if kind=='cap' else 30 if kind=='full' else 15,500 if kind=='cap' else 30))
                    write(hero+0x76,struct.pack('<HH',8 if kind=='none' else 4,8))
                    for i in range(20):
                        p=slot+120*i;write(p,struct.pack('<I',m.u32[p]&~0x04800000))
                    if choice==0 and kind=='success':
                        item=bytearray(120);struct.pack_into('<I',item,0,0xCC800000);item[4:6]=b'\1\1'
                        item[8]=bytes(m[0x020013D0:0x020014D0]).index(1);write(slot,item)
                    initial.append(e|{'guard':bytes(m[r[13]:r[13]+32]).hex(),'stats':stats()})
                    g.core.cpu.gprs[0]=actor;overrides.append({'event':e,'pc_after':0x0801AAFC,'r0_after':actor})
                    require(g.core._core.writeRegister(g.core._core,b'pc',ffi.new('uint32_t*',0x0801AAFC)),'Priest dispatch failed')
                if not initial or ends:return
                if a in (0x0801AE18,0x0801AF20,0x0801B0D4,0x0801B1F0):service_entries.append(e)
                if a in (0x0801AF1C,0x0801B0CA,0x0801B1E8,0x0801B2A6):
                    before=service_entries[-1]['registers']
                    require(r[4:12]==before[4:12] and r[13]==before[13] and r[1]==before[14],'Priest service ABI differs')
                    service_ends.append({'event':e,'stats':stats(),'result':r[0]})
                if a==0x0801ACC4:
                    overrides.append({'event':e,'r0_after':99,'reason':'Isolate transactions from the independent random bread gift.'});g.core.cpu.gprs[0]=99
                if a==0x08036CAC:exit_requests.append({'reason':r[0],'argument':r[1]})
                if a==0x08000FB8 and r[1] in rows:
                    row=rows[r[1]];require(not row['layout']['direct_rom_stream'] and r[0]==r[13]+4,'Unowned priest format')
                    payload=native_format(bytes.fromhex(row['encoded_hex']),[r[2]],m)
                    require(len(payload)<=row['layout']['maximum_formatted_bytes']<=256,'Priest format overflow')
                    pending.update(row=row,regs=r,payload=payload,guard=bytes(m[r[0]+len(payload):r[0]+272]),ret=r[14]&~1)
                    debug.breakpoint(r[14]&~1)
                if pending and a==pending['ret']:
                    old=pending['regs'];p=old[0];payload=pending['payload'];row=pending['row']
                    require(bytes(m[p:p+len(payload)])==payload and bytes(m[p+len(payload):p+272])==pending['guard'] and r[4:12]==old[4:12] and r[13]==old[13],'Priest formatter bytes/tail/guard/ABI differ')
                    c.resources[p]=row|{'encoded_hex':payload.hex()};formats.append({'id':row['id'],'amount':old[2],'bytes':len(payload),'capacity':256,'tail_guard_abi_match':True});pending.clear()
                if a in (0x08001750,0x08001888):draws[:]=[d for d in draws if d['window']!=r[0]]
                if a==0x080021B4 and r[1]==menu['offset']+0x08000000:
                    require(tuple(m.u8[r[0]+i] for i in (0,1,4,5))==(8,24,23,4),'Priest menu geometry changed')
                    menu_reads.append(e)
                if a==0x0801570C and r[14]==0x08015F13:
                    require(r[0]==8 and r[1] in (24,40,56,72),'Priest cursor left original menu')
                    selections.append({'frame':e['frame'],'choice':(r[1]-24)//16})
                if a==0x08001BC4 and c.active:
                    w=r[0];key=(w,r[1],r[13],r[14],m.u8[w+2],m.u8[w+3])
                    if not draws or draws[-1]['key']!=key:draws.append({'key':key,'window':w,'code':r[1],'x':m.u8[w+2],'y':m.u8[w+3],'origin':[m.u8[w],m.u8[w+1]],'foreground':m.u8[0x020000C2],'bank':m.u16[m.u32[w+12]]>>12})
                if a==0x080023A0 and c.active:waits.append(e)
                c.callback(e)
                if a==0x0801AE04:
                    old=initial[0]['registers'];require(r[4:12]==old[4:12] and r[13]==old[13] and r[1]==old[14] and bytes(m[r[13]:r[13]+32]).hex()==initial[0]['guard'],'Priest root caller ABI/guard differs')
                    ends.append(e)
            def capture(tag):
                nonlocal pixels
                g.frames(3);pic=g.capture(tag);images[tag+'.png']=digest((g.output/(tag+'.png')).read_bytes())
                require(draws,'Empty priest capture')
                for d in draws:
                    glyph,_=c.glyph_record(d['code']);colour=m.u16[0x05000000+2*(16*d['bank']+d['foreground'])];rgb=tuple(((colour>>s)&31)*255//31 for s in (0,5,10))
                    for y,line in enumerate(glyph['rows']):
                        for x,bit in enumerate(line):
                            px=d['origin'][0]+d['x']+x;py=d['origin'][1]+d['y']*16+y
                            require((pic.getpixel((px,py))==rgb)==(bit=='#'),'Priest service final pixels differ: '+repr((name,tag,px,py,hex(d['code']))));pixels+=1
            def advance(predicate,label,key='A',limit=60):
                for i in range(limit):
                    g.frames(15)
                    if predicate():return
                    if c.active or draws:
                        # Wait for a page boundary or completed native stream.
                        if c.active and not waits:continue
                        capture(f'{label}-{i}')
                    g.press(key,hold=1,wait=30);waits.clear()
                raise ValueError('Priest route incomplete: '+name+' '+label)
            with Debugger(g,callback,max_events=300000) as debug:
                for a in set(TextChecks.ADDRESSES+(0x08008F4C,0x08000FB8,0x08001750,0x08001888,0x0801AE04,0x0801ACC4,0x0801570C,0x0801AE18,0x0801AF20,0x0801B0D4,0x0801B1F0,0x0801AF1C,0x0801B0CA,0x0801B1E8,0x0801B2A6,0x08036CAC)):debug.breakpoint(a)
                g.press('A',hold=1,wait=0)
                advance(lambda:bool(menu_reads) and not c.active,'greeting');capture('menu')
                if choice is None:
                    for key,expected in zip(('UP','DOWN','DOWN','DOWN','DOWN','DOWN'),(3,0,1,2,3,0)):
                        g.press(key,hold=1,wait=20);capture('cursor-'+str(len(images)))
                        require(selections[-1]['choice']==expected,'Priest cursor wrap differs')
                else:
                    for _ in range(choice):g.press('DOWN',hold=1,wait=20)
                    capture('selected');g.press('A',hold=1,wait=30)
                    advance(lambda:any(r['id']==f'priest.{offers[choice]:03x}' for r in c.reads) and not c.active,'offer')
                    capture('offer-complete');g.press('B' if kind=='decline' else 'A',hold=1,wait=30)
                    advance(lambda:len(service_ends)==1,'outcome')
                    if not ends:
                        advance(lambda:len(menu_reads)>=2 and not c.active,'reopen');capture('reopened')
                        if kind in ('success','full') and choice!=3:
                            for _ in range(choice):g.press('DOWN',hold=1,wait=20)
                            g.press('A',hold=1,wait=30)
                            advance(lambda:c.completed('priest.51c') and not c.active,'already-blessed');capture('already-blessed')
                            g.press('A',hold=1,wait=30);advance(lambda:len(menu_reads)>=3 and not c.active,'second-reopen');capture('reopened-again')
                if not ends:
                    g.press('B',hold=1,wait=30);advance(lambda:bool(ends),'farewell')
            require(ends and not pending and g.snapshot().battery==fixture.battery,'Priest case incomplete/save changed')
            if choice is not None:
                require(len(service_ends)==1 and formats[0]['amount']==prices[choice],'Priest service dispatch/price differs')
                before=initial[0]['stats'];after=service_ends[0]['stats'];paid=kind in ('success','full')
                require(after['gold']==before['gold']-(prices[choice] if paid else 0) and service_ends[0]['result']==int(paid),'Priest payment/result differs')
                if choice==0 and paid:
                    expected=bytearray.fromhex(before['inventory']);struct.pack_into('<I',expected,0,struct.unpack_from('<I',expected)[0]&~0x04000000)
                    require(after['inventory']==expected.hex(),'Priest curse result differs')
                else:require(after['inventory']==before['inventory'],'Priest changed unrelated inventory')
                if choice==1 and paid:
                    require(after['hp']==after['max_hp']==before['max_hp']+(2 if kind=='full' else 0),'Priest healing result differs')
                if choice==2 and paid:require(after['strength']==after['max_strength'],'Priest strength restoration differs')
                if not paid:
                    require(after==before,'Declined/refused priest service changed player state')
                outcome = ((0x4EC,0x4F8,0x504,0x510)[choice] if kind=='no-funds' else
                           0x9F0 if choice==0 and kind=='none' else 0x9F4 if kind=='none' else
                           0x9EC if kind=='cap' else 0x9E8 if kind=='full' else
                           (0x4E8,0x4F4,0x500,None)[choice] if paid else None)
                if outcome is not None:
                    require(c.completed(f'priest.{outcome:03x}'),'Expected priest outcome text missing')
                require(exit_requests==([{'reason':35,'argument':0}] if choice==3 and paid else []),'Priest return request differs')
            results.append({'case':name,'choice':choice,'kind':kind,'overrides':overrides,'inputs':g.inputs,'reads':c.reads,'formats':formats,'menu_opens':len(menu_reads),'selections':selections,'before':initial[0]['stats'],'service_outcomes':service_ends,'exit_requests':exit_requests,'visible_pixels_checked':pixels,'images':images,'caller_guard_abi_preserved':True})
    report={'passed':True,'rom_sha256':digest(rom),'cases':results,'scope':'Controlled existing dungeon actor/state, then native priest menu, prices, prompts and service branches through ordinary buttons. Original184px four-row menu, final glyph pixels, cancellation/reopening, numeric buffers, caller ABI, payments, inventory curse flags, HP/strength restoration and return request checked. Random bread gift is isolated by an explicit recorded RNG-result override; its messages have separate paged preflight. Ordinary priest encounter/progression and completed surface transition are not claimed.'}
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print('Priest services:',len(results),'passed',flush=True)
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,default=ROOT/'build/priest-prototype');a=p.parse_args();run(a.source)
