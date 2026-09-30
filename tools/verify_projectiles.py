"""Throw formatter field bounds and visible output through its native refusal path."""
import argparse,json,struct
from pathlib import Path
import mgba.log
from tools.compact_font import encode
from tools.emulator import Session,Debugger
from tools.rom import ROOT,digest,require
from tools.verify_inventory_action_prototype import ActionCheck
from tools.verify_service_ui import materialize


def run(source=ROOT/'build/projectile-prototype'):
    out=source/'projectile-validation';mgba.log.silence()
    rom=(source/'torneko-2-english.gba').read_bytes();build=json.loads((source/'build.json').read_text())
    require(digest(rom)==build['output_sha256'],'Stale projectile ROM')
    from tools import verify_player_status_prototype as status
    previous=status.OUT
    try:status.OUT=out;fixture=status.ready(rom,build)
    finally:status.OUT=previous
    results=[]
    for row in build['projectiles']['entries']:
        for field in ('native','maximum-width','maximum-bytes','coloured'):
            name=row['id']+'-'+field;print('Projectile:',name,flush=True)
            with Session(rom,out/name) as g:
                g.restore(fixture);m=g.core.memory;initial=[];returns=[];formats=[];checks=[];pending={};overrides=[];colours=[]
                def write(a,data):
                    overrides.append({'address':a,'before':bytes(m[a:a+len(data)]).hex(),'after':data.hex()})
                    for i,v in enumerate(data):m.u8[a+i]=v
                item=bytearray(120);struct.pack_into('<I',item,0,0xCC800000);item[4:6]=b'\1\1';item[8]=bytes(m[0x020013D0:0x020014D0]).index(1)
                write(0x0200DF28,item);definition=0x02003BAC+20;write(definition,struct.pack('<I',m.u32[definition]|0x40000000))
                inventory=bytes(m[0x0200DF28:0x0200E888])
                def callback(e):
                    a,r=e['address'],e['registers']
                    if a==0x080259FC:initial.append(e|{'guard':bytes(m[r[13]:r[13]+32]).hex()})
                    if not initial:return
                    if a==0x08000FB8 and r[14]==0x08025A3D:
                        require(not formats and not pending and r[0]==r[13]+0x10 and r[2]==r[13]+0x188,'Throw message/item frame differs')
                        expected_curse=next(x for x in build['projectiles']['entries'] if x['table_offset']==0x80)
                        require(r[1]==expected_curse['offset']+0x08000000,'Native Throw refusal did not read private table')
                        args=[r[2]];regs=list(r)
                        if row['table_offset']!=0x80:
                            overrides.append({'event':e,'r1_after':row['offset']+0x08000000,'reason':'Controlled format preflight in the audited native256-byte Throw output.'})
                            g.core.cpu.gprs[1]=row['offset']+0x08000000;regs[1]=row['offset']+0x08000000
                        if field!='native':
                            text='W'*27 if field=='maximum-width' else 'i'*31 if field=='maximum-bytes' else 'Item'
                            raw=encode(text) if field!='coloured' else b'\x03\x05'+encode(text)[:-1]+b'\x05\0'
                            write(r[2],raw.ljust(64,b'\0'))
                        if 'actor' in row['field_roles']:
                            actor=encode('W'*31 if field=='maximum-width' else 'i'*31 if field=='maximum-bytes' else 'Slime')
                            if field=='coloured':actor=b'\x03\x07'+actor[:-1]+b'\x05\0'
                            write(0x02008D08,actor.ljust(64,b'\0'));g.core.cpu.gprs[3]=0x02008D08;regs[3]=0x02008D08;args.append(0x02008D08)
                            overrides.append({'event':e,'r3_after':0x02008D08,'reason':'Existing64-byte actor-name scratch supplied for the second native %s role.'})
                        payload=materialize(bytes.fromhex(row['encoded_hex']),args,m)
                        require(len(payload)<=row['maximum_bytes']<=256,'Projectile expansion exceeds output')
                        pending.update(regs=regs,payload=payload,guard=bytes(m[r[0]+256:r[0]+272]),item=bytes(m[r[2]:r[2]+64]))
                        checks.append(ActionCheck(g,payload[:-1],0x08025A45,256,pending['guard']))
                    if a==0x08025A3C and pending:
                        old=pending['regs'];p=old[0];payload=pending['payload']
                        require(bytes(m[p:p+len(payload)])==payload and bytes(m[p+256:p+272])==pending['guard'] and bytes(m[old[2]:old[2]+64])==pending['item'] and r[4:12]==old[4:12] and r[13]==old[13],'Throw format/message guard/item field/ABI differs')
                        formats.append({'id':row['id'],'bytes':len(payload),'capacity':256,'hex':payload.hex(),'guard_abi_match':True});pending.clear()
                    if checks and not (checks[0].complete and checks[0].returned):
                        if a==0x08001C14 and checks[0].pending_glyph:
                            bank=m.u16[m.u32[r[5]+12]]>>12;colour=m.u16[0x05000000+2*(bank*16+m.u8[0x020000C2])]
                            colours.append(tuple(((colour>>s)&31)*255//31 for s in (0,5,10)))
                        checks[0].callback(e)
                    if a==0x080263EC:
                        old=initial[0]['registers'];require(r[4:12]==old[4:12] and r[13]==old[13] and r[0]==old[14] and bytes(m[r[13]:r[13]+32]).hex()==initial[0]['guard'],'Throw full consumer ABI/guard differs');returns.append(e)
                with Debugger(g,callback,max_events=80000) as debug:
                    for a in (0x080259FC,0x080263EC,0x08000FB8,0x08025A3C,0x0801588C,0x080158CE,0x08025A44,0x08001BC4,0x08001C14,0x08001C68):debug.breakpoint(a)
                    g.press('B',hold=8,wait=30);g.press('A',wait=30);g.press('A',wait=30)
                    actions=[]
                    for i in range(7):
                        n=m.u16[0x0200CDD0+i*2]
                        if not n:break
                        actions.append(n)
                    require(9 in actions,'Native Throw absent')
                    for _ in range(actions.index(9)):g.press('DOWN',wait=20)
                    g.capture('menu');g.press('A',wait=0)
                    for _ in range(360):
                        g.frames(1)
                        if returns and checks and checks[0].complete and checks[0].returned:break
                    require(len(initial)==len(returns)==len(checks)==len(formats)==1 and checks[0].complete and checks[0].returned and not pending,'Throw preflight incomplete')
                    g.frames(3);pic=g.capture('message');c=checks[0];visible=[];pixels=0
                    require(len(c.draws)==len(colours),'Projectile colours incomplete')
                    for draw,colour in zip(c.draws,colours):
                        if draw['native_scroll']:
                            shift=draw['key'][-1]-draw['y'];require(shift>0,'Unexpected projectile scroll')
                            for old in visible:old['final_y']-=shift
                        visible.append(draw|{'final_y':draw['y'],'colour':colour})
                    for d in visible:
                        require(d['final_y']>=0,'Projectile message scrolled out of view');glyph,_=c.glyph_record(d['code'])
                        for y,line in enumerate(glyph['rows']):
                            for x,bit in enumerate(line):
                                px=m.u8[0x02000000]+d['x']+x;py=m.u8[0x02000001]+d['final_y']*16+y
                                require((pic.getpixel((px,py))==d['colour'])==(bit=='#'),'Projectile final pixels differ');pixels+=1
                require(bytes(m[0x0200DF28:0x0200E888])==inventory and g.snapshot().battery==fixture.battery,'Refused Throw changed inventory/battery')
                results.append({'case':name,'id':row['id'],'field':field,'overrides':overrides,'inputs':g.inputs,'formats':formats,'queue':checks[0].queued,'visible_pixels_checked':pixels,'caller_guard_abi_preserved':True,'images':{p:digest((g.output/p).read_bytes()) for p in ('menu.png','message.png')}})
    report={'passed':True,'rom_sha256':digest(rom),'cases':results,'scope':'Native Throw command reaches its cursed-equipped refusal from recorded inventory setup. Five reviewed formats use the same audited256-byte output via explicit format/field substitutions; item162px/63-byte and actor186px/63-byte extremes, colours, exact output, separate item field and full caller ABI/guards pass. Final screen pixels and one-line joins/two-line fallbacks are checked. This is formatter preflight, not proof of natural collision, landing, stuck-floor or projectile physics outcomes.'}
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print('Projectiles:',len(results),'passed',flush=True)
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,default=ROOT/'build/projectile-prototype');a=p.parse_args();run(a.source)
