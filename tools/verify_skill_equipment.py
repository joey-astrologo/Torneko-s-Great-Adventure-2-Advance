"""Controlled native equipment-skill preview layouts and hunger totals."""
import argparse,json,struct
from pathlib import Path
import mgba.log
from tools.emulator import Session,Debugger,ffi
from tools.rom import ROOT,digest,require
from tools.dialogue_checks import TextChecks
from tools.verify_service_ui import materialize


def run(source=ROOT/'build/skill-menu-prototype',only=None):
    out=source/'skill-equipment-validation';mgba.log.silence()
    rom=(source/'torneko-2-english.gba').read_bytes();build=json.loads((source/'build.json').read_text());require(digest(rom)==build['output_sha256'],'Stale skill equipment ROM')
    from tools import verify_player_status_prototype as status
    previous=status.OUT
    try:status.OUT=out;fixture=status.ready(rom,build)
    finally:status.OUT=previous
    direct={r['offset']+0x08000000:r for r in build['skill_menu']['entries']};definitions=build['skill_info']['definitions']
    names={r['offset']+0x08000000:r for r in build['skill_info']['entries'] if r['kind']=='name'}
    cases=[('empty-weapon',1,[],True),('three-weapon',1,[15,27,54],True),('zero-cost',6,[10],True),('incompatible',1,[10],True),('not-equipped',1,[15],False),('shield',30,[77,101,103],True),('empty-shield',30,[],True)];results=[]
    for name,item_id,assigned,equipped in cases:
        if only and name!=only:continue
        print('Skill equipment:',name,flush=True)
        with Session(rom,out/name) as g:
            g.restore(fixture);m=g.core.memory;overrides=[];redirects=[];formats=[];pending=[];draws=[];images={};pixels=0;returns=[];creations=[];copies=[];copy_pending={}
            def write(a,data):
                overrides.append({'address':a,'before':bytes(m[a:a+len(data)]).hex(),'after':data.hex()})
                for i,v in enumerate(data):m.u8[a+i]=v
            mapping=bytes(m[0x020013D0:0x020014D0]);item=bytearray(120);struct.pack_into('<I',item,0,0xC8000000);item[4:6]=bytes((1,1));item[8]=mapping.index(153);write(0x0200DF28,item)
            target=0x0200DF28+120;struct.pack_into('<I',item,0,0xC8000000|(0x800000 if equipped else 0));item[8]=mapping.index(item_id);write(target,item)
            for ident in (153,item_id):
                at=0x02003BAC+20*ident;write(at,struct.pack('<I',m.u32[at]|0x40000000))
            write(0x02004CF0,bytes(144));write(0x02004CF0+3*item_id,bytes(assigned).ljust(3,b'\0'))
            c=TextChecks(g,{})
            def callback(e):
                a,r=e['address'],e['registers']
                if a==0x08022828:
                    require(r[0]==1 and r[14]==0x08017B13,'Equipment preview Info trigger differs')
                    redirects.append(e|{'guard':bytes(m[r[13]:r[13]+32]).hex(),'r0_after':target,'r1_after':1,'pc_after':0x0802144C})
                    g.core.cpu.gprs[0]=target;g.core.cpu.gprs[1]=1
                    require(g.core._core.writeRegister(g.core._core,b'pc',ffi.new('uint32_t*',0x0802144C)),'Equipment preview dispatch failed')
                if a==0x08001798:creations.append(e)
                if a==0x0800EF30:c.resources.pop(r[1],None)
                if a in (0x08001750,0x08001888):draws[:]=[d for d in draws if d['window']!=r[0]]
                if a==0x08000FB8 and r[1] not in direct:c.resources.pop(r[0],None)
                if a==0x08000FB8 and r[1] in direct:
                    row=direct[r[1]];require(r[0]==r[13]+8 and row['capacity']==256,'Equipment skill output ownership differs')
                    args=r[2:4]+[m.u32[r[13]]];payload=materialize(bytes.fromhex(row['encoded_hex']),args,m)
                    require(len(payload)<=256,'Equipment skill format overflow');selected=[names[v]['skill_id'] for v in args if v in names]
                    pending.append((r,row,payload,bytes(m[r[0]+256:r[0]+272]),selected,args))
                if pending and a==(pending[-1][0][14]&~1):
                    old,row,payload,guard,selected,args=pending.pop();at=old[0]
                    require(bytes(m[at:at+len(payload)])==payload and bytes(m[at+256:at+272])==guard and r[4:12]==old[4:12] and r[13]==old[13],'Equipment skill output/guard/ABI differs')
                    c.resources[at]={'id':row['id'],'encoded_hex':payload.hex(),'layout':{'pages':[[row['id']]]}}
                    formats.append({'id':row['id'],'hex':payload.hex(),'bytes':len(payload),'skill_ids':selected,'arguments':args,'guard_abi_preserved':True})
                if a==0x0805CF54 and r[14]==0x08021657:
                    row=next(r for r in direct.values() if r['id']=='skill-menu.738');raw=bytes.fromhex(row['encoded_hex'])
                    require(r[0]==r[13]+8 and r[1]==row['offset']+0x08000000,'Equipment Use copy owner differs');copy_pending.update(regs=r,row=row,raw=raw,guard=bytes(m[r[0]+256:r[0]+272]))
                if a==0x08021656 and copy_pending:
                    old=copy_pending['regs'];at=old[0];raw=copy_pending['raw'];row=copy_pending['row']
                    require(bytes(m[at:at+len(raw)])==raw and bytes(m[at+256:at+272])==copy_pending['guard'] and r[4:12]==old[4:12] and r[13]==old[13],'Equipment Use copy/ABI differs')
                    c.resources[at]=row|{'layout':{'pages':[[row['id']]]}};copies.append({'id':row['id'],'guard_abi_preserved':True});copy_pending.clear()
                if a==0x08001BC4 and c.active:
                    w=r[0];key=(w,r[1],r[13],r[14],m.u8[w+2],m.u8[w+3])
                    require(m.u8[w+2]+c.glyph_record(r[1])[0]['advance']<=(40 if m.u8[w+4]==5 else 160),'Equipment skills exceed original text endpoint')
                    if not draws or draws[-1]['key']!=key:draws.append({'key':key,'window':w,'code':r[1],'x':m.u8[w+2],'y':m.u8[w+3],'origin':[m.u8[w],m.u8[w+1]],'foreground':m.u8[0x020000C2],'bank':m.u16[m.u32[w+12]]>>12})
                if a==0x080021B4 and r[1] in c.resources:
                    row=c.resources[r[1]];raw=bytes.fromhex(row['encoded_hex'])
                    require(bytes(m[r[1]:r[1]+len(raw)])==raw,'Equipment source mismatch: '+repr((row['id'],hex(r[1]),hex(r[14]),raw.hex(),bytes(m[r[1]:r[1]+len(raw)]).hex())))
                if a in c.ADDRESSES:c.callback(e)
                if a==0x08021720:
                    old=redirects[-1]['registers'];require(r[4:12]==old[4:12] and r[13]==old[13] and r[1]==old[14] and r[0]==0 and bytes(m[r[13]:r[13]+32]).hex()==redirects[-1]['guard'],'Equipment skill cancel caller ABI differs');returns.append(e)
            def capture(tag):
                nonlocal pixels
                g.frames(3);pic=g.capture(tag);images[tag+'.png']=digest((g.output/(tag+'.png')).read_bytes());require(draws,'No equipment skill glyphs')
                for d in draws:
                    glyph,_=c.glyph_record(d['code']);colour=m.u16[0x05000000+2*(16*d['bank']+d['foreground'])];rgb=tuple(((colour>>s)&31)*255//31 for s in (0,5,10))
                    for y,line in enumerate(glyph['rows']):
                        for x,bit in enumerate(line):
                            px=d['origin'][0]+d['x']+x;py=d['origin'][1]+d['y']*16+y
                            require((pic.getpixel((px,py))==rgb)==(bit=='#'),'Equipment skill final pixels differ: '+repr((name,tag,px,py,hex(d['code']))));pixels+=1
            with Debugger(g,callback,max_events=250000) as debug:
                for a in set(c.ADDRESSES+(0x08022828,0x08021720,0x08001798,0x08001750,0x08001888,0x0800EF30,0x08000FB8,0x080214F4,0x08021588,0x080215B8,0x080215EE,0x08021616,0x0805CF54,0x08021656)):debug.breakpoint(a)
                g.press('B',hold=8,wait=120);g.press('A',wait=120);g.press('A',wait=120)
                actions=[]
                for i in range(7):
                    n=m.u16[0x0200CDD0+i*2]
                    if not n:break
                    actions.append(n&127)
                require(40 in actions,'Controlled spellbook Info missing')
                for _ in range(actions.index(40)):g.press('DOWN',wait=20)
                for repeat in range(2):
                    first=len(creations);draws.clear();g.press('A',wait=120)
                    require(creations[first]['registers'][:4]==[1,4,21,6],'Equipment skill preview geometry differs')
                    if copies:require(creations[-1]['registers'][:4]==[24,4,5,1] and (24*8-4)-((1+21)*8+4)==8,'Equipment skill action geometry/gap differs')
                    capture('preview-'+str(repeat));g.press('B',wait=120)
                    if repeat==0:
                        g.press('A',wait=120)
                        for _ in range(actions.index(40)):g.press('DOWN',wait=20)
            covered={i for r in formats for i in r['skill_ids']};require(covered==set(assigned),'Equipment skill set incomplete')
            require(len(returns)==2 and not pending and not copy_pending and not c.active and g.snapshot().battery==fixture.battery,'Equipment preview incomplete/battery changed')
            require(bytes(m[0x02004CF0+3*item_id:0x02004CF0+3*item_id+3])==bytes(assigned).ljust(3,b'\0'),'Equipment preview changed assignment')
            results.append({'case':name,'item_id':item_id,'assigned_skills':assigned,'equipped':equipped,'reads':c.reads,'formats':formats,'copies':copies,'dispatch_overrides':redirects,'overrides':overrides,'inputs':g.inputs,'visible_pixels_checked':pixels,'images':images,'caller_guard_abi_preserved':True})
    report={'passed':True,'rom_sha256':digest(rom),'cases':results,'scope':'Controlled item Info dispatch invokes original equipment-skill preview with pinned existing inventory/assignment fields. Empty, three-skill, zero-cost, incompatible, unequipped and shield branches, original geometry/gaps,256-byte guards, final pixels, cancel/reopen and unchanged assignment/battery. Native acquisition and Use outcomes remain separate.'}
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print('Skill equipment:',len(results),'passed',flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,default=ROOT/'build/skill-menu-prototype');p.add_argument('--only');a=p.parse_args();run(a.source,a.only)
