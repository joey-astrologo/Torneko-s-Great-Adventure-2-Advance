"""Controlled skill Info selectors, original hunger costs/types and equipment footer."""
import argparse,json,struct
from pathlib import Path
import mgba.log
from tools.emulator import Session,Debugger,ffi
from tools.rom import ROOT,digest,require
from tools.dialogue_checks import TextChecks,player_layout_cases
from tools.name_entry import HERO
from tools.compact_font import encode
from tools.verify_result_ui import native_format


def run(source=ROOT/'build/skill-info-prototype',only=None):
    out=source/'skill-info-validation';mgba.log.silence()
    rom=(source/'torneko-2-english.gba').read_bytes();build=json.loads((source/'build.json').read_text())
    require(digest(rom)==build['output_sha256'],'Stale skill Info ROM')
    from tools import verify_player_status_prototype as status
    previous=status.OUT
    try:status.OUT=out;fixture=status.ready(rom,build)
    finally:status.OUT=previous
    definitions=build['skill_info']['definitions'];entries={r['id']:r for r in build['skill_info']['entries']}
    results=[]
    cases=[(i,'unassigned',None) for i in range(128) if only is None or i==only]
    if only in (None,77):cases.extend((77,label,None) for label in ('single','multiple','hidden'))
    for ident,label,player in cases:
        name=f'{ident}-{label}';print('Skill Info:',name,flush=True)
        with Session(rom,out/name) as g:
            g.restore(fixture);m=g.core.memory;initial=[];returns=[];formats=[];pending={};overrides=[];draws=[];creations=[];images={};pixels=0
            def write(a,data):
                overrides.append({'address':a,'before':bytes(m[a:a+len(data)]).hex(),'after':data.hex()})
                for n,v in enumerate(data):m.u8[a+n]=v
            item=bytearray(120);struct.pack_into('<I',item,0,0xC8000000);item[4:6]=bytes((1,1));item[8]=bytes(m[0x020013D0:0x020014D0]).index(153)
            write(0x0200DF28,item);at=0x02003BAC+153*20;write(at,struct.pack('<I',m.u32[at]|0x40000000))
            write(0x02004CF0,bytes(144))
            item_names={int(r['id'].split('.')[-1]):r for r in build['items']['entries'] if r['id'].startswith('item.name.')}
            assigned=max(range(48),key=lambda i:len(item_names[i]['english']))
            if label in ('single','multiple'):write(0x02004CF0+3*assigned,bytes((ident,0,0)))
            if label=='multiple':write(0x02004CF0+3*((assigned+1)%48),bytes((ident,0,0)))
            header=entries['skill-info.'+('7b0' if definitions[ident]['hunger_cost'] else '7c8')]
            footer=entries['skill-info.924'] if ident==0 or label in ('single','multiple') else entries['skill-info.928'] if ident<=76 or ident==115 else entries['skill-info.unset-shield']
            footer_field=entries['skill-info.multiple'] if ident==0 or label=='multiple' else item_names[assigned]
            redirects=[];copies=[];copy_pending={}
            description=entries[f'skill.description.{ident}']
            resources={r['offset']+0x08000000:r|{'layout':{'pages':[[r['id']]]}} for r in (description,footer)}
            c=TextChecks(g,resources)
            def callback(e):
                a,r=e['address'],e['registers']
                if a==0x08022828:
                    require(r[0]==1 and r[14]==0x08017B13,'Item Info trigger differs')
                    initial.append(e|{'guard':bytes(m[r[13]:r[13]+32]).hex()})
                    redirects.append({'event':e,'r0_after':ident,'r1_after':int(label=='hidden'),'pc_after':0x0802172C})
                    g.core.cpu.gprs[0]=ident;g.core.cpu.gprs[1]=int(label=='hidden')
                    require(g.core._core.writeRegister(g.core._core,b'pc',ffi.new('uint32_t*',0x0802172C)),'Skill Info controlled dispatch failed')
                if a==0x08001798:creations.append(e)
                if a==0x0805CF54 and r[14]==0x08021833:
                    raw=bytes.fromhex(entries['skill-info.multiple']['encoded_hex'])
                    require(r[1]==entries['skill-info.multiple']['offset']+0x08000000 and r[0]==r[13]+0x104 and len(raw)<=64,'Skill multiple-assignment copy owner differs')
                    copy_pending.update(regs=r,raw=raw,guard=bytes(m[r[0]+64:r[0]+80]))
                if a==0x08021832 and copy_pending:
                    old=copy_pending['regs'];at=old[0];raw=copy_pending['raw']
                    require(bytes(m[at:at+len(raw)])==raw and bytes(m[at+64:at+80])==copy_pending['guard'] and r[4:12]==old[4:12] and r[13]==old[13],'Skill multiple-assignment complete copy/ABI/guard differs')
                    copies.append({'bytes':len(raw),'hex':raw.hex(),'guard_abi_preserved':True});copy_pending.clear()
                if a==0x08000FB8 and r[14] in (0x08021793,0x08021847,0x08021885,0x08021899):
                    row=header if r[14]==0x08021793 else footer
                    require(r[1]==row['offset']+0x08000000 and r[0]==r[13]+4,'Skill Info format pointer/output differs')
                    args=r[2:4]+[m.u32[r[13]]]
                    if row==header:
                        kind=entries['skill-info.'+format((0x7B4,0x7B8,0x7BC,0x894)[definitions[ident]['kind']],'03x')]
                        require(args==[entries[f'skill.name.{ident}']['offset']+0x08000000,kind['offset']+0x08000000,definitions[ident]['hunger_cost']],'Native skill name/type/hunger selection differs')
                    elif row['id']=='skill-info.924':
                        raw=bytes.fromhex(footer_field['encoded_hex'])
                        require(args[0]==r[13]+0x104 and bytes(m[args[0]:args[0]+len(raw)])==raw,'Skill assignment field incomplete/wrong name')
                    payload=native_format(bytes.fromhex(row['encoded_hex']),args,m)
                    require(len(payload)<=row.get('maximum_bytes',len(payload))<=256,'Skill Info output exceeds256bytes')
                    pending.update(regs=r,payload=payload,guard=bytes(m[r[0]+256:r[0]+272]),args=args,row=row)
                if pending and a==(pending['regs'][14]&~1):
                    old=pending['regs'];at=old[0];payload=pending['payload'];row=pending['row']
                    require(bytes(m[at:at+len(payload)])==payload and bytes(m[at+256:at+272])==pending['guard'] and r[4:12]==old[4:12] and r[13]==old[13],'Skill Info output/guard/ABI differs')
                    c.resources[at]={'id':row['id'],'encoded_hex':payload.hex(),'layout':{'pages':[[row['id']]]}}
                    formats.append({'id':row['id'],'hex':payload.hex(),'bytes':len(payload),'arguments':pending['args'],'guard_abi_preserved':True});pending.clear()
                if a==0x08001BC4 and c.active:
                    w=r[0];key=(w,r[1],r[13],r[14],m.u8[w+2],m.u8[w+3])
                    if not draws or draws[-1]['key']!=key:
                        require(m.u8[w+2]+c.glyph_record(r[1])[0]['advance']<=216,'Skill Info exceeds its216px text budget: '+repr((name,c.active['id'],m.u8[w+2],m.u8[w+3],hex(r[1]),m.u8[w+6],m.u8[w+8])))
                        draws.append({'key':key,'window':w,'code':r[1],'x':m.u8[w+2],'y':m.u8[w+3],'origin':[m.u8[w],m.u8[w+1]],'foreground':m.u8[0x020000C2],'bank':m.u16[m.u32[w+12]]>>12})
                if a in c.ADDRESSES:c.callback(e)
                if a==0x080218E0:
                    old=initial[-1]['registers'];require(r[4:12]==old[4:12] and r[13]==old[13] and r[0]==old[14] and bytes(m[r[13]:r[13]+32]).hex()==initial[-1]['guard'],'Skill Info caller ABI/guard differs');returns.append(e)
            def capture(tag):
                nonlocal pixels
                g.frames(3);pic=g.capture(tag);images[tag+'.png']=digest((g.output/(tag+'.png')).read_bytes());require(draws,'No skill Info glyphs')
                for d in draws:
                    glyph,_=c.glyph_record(d['code']);colour=m.u16[0x05000000+2*(16*d['bank']+d['foreground'])];rgb=tuple(((colour>>s)&31)*255//31 for s in (0,5,10))
                    for y,line in enumerate(glyph['rows']):
                        for x,bit in enumerate(line):
                            px=d['origin'][0]+d['x']+x;py=d['origin'][1]+d['y']*16+y
                            require((pic.getpixel((px,py))==rgb)==(bit=='#'),'Skill Info final pixels differ: '+repr((name,tag,px,py,hex(d['code']))));pixels+=1
            with Debugger(g,callback,max_events=150000) as debug:
                for a in set(c.ADDRESSES+(0x08022828,0x080218E0,0x08001798,0x08000FB8,0x08021792,0x08021846,0x08021884,0x08021898,0x0805CF54,0x08021832)):debug.breakpoint(a)
                g.press('B',hold=8,wait=120);g.press('A',wait=120);g.press('A',wait=120)
                actions=[]
                for i in range(7):
                    n=m.u16[0x0200CDD0+i*2]
                    if not n:break
                    actions.append(n&127)
                require(40 in actions,'Spellbook Info unavailable')
                for _ in range(actions.index(40)):g.press('DOWN',wait=20)
                for repeat in range(2):
                    draws.clear();first=len(c.reads);g.press('A',wait=120)
                    require(creations[-1]['registers'][:4]==[1,4,28,6],'Skill Info geometry changed')
                    require([r['id'] for r in c.reads[first:]]==[header['id'],description['id']]+([] if label=='hidden' else [footer['id']]),'Complete native skill Info sources missing: '+repr((name,[r['id'] for r in c.reads[first:]])))
                    capture('info-'+str(repeat));g.press('B',wait=120)
                    if repeat==0:
                        g.press('A',wait=120)
                        for _ in range(actions.index(40)):g.press('DOWN',wait=20)
            require(len(initial)==len(returns)==2 and len(formats)==4 and not c.active and not pending and not copy_pending and g.snapshot().battery==fixture.battery,'Skill Info close/reopen/battery incomplete')
            results.append({'case':name,'skill_id':ident,'footer_case':label,'dispatch_overrides':redirects,'complete_multiple_copies':copies,'reads':c.reads,'formats':formats,'inputs':g.inputs,'overrides':overrides,'visible_pixels_checked':pixels,'caller_guard_abi_preserved':True,'selection':initial,'return':returns,'images':images})
    report={'passed':True,'rom_sha256':digest(rom),'cases':results,'scope':'Controlled dispatch from ordinary item Info invokes every128 skill Info ID and original hunger/type selection. Original224px/six-row window,216px text, three body rows and footer row4 are preserved. All sources, single/multiple/hidden equipment footer variants, complete64-byte assignment copies,256-byte outputs, coloured final pixels, caller guards, twice reopening and unchanged battery are checked. Natural warrior/skill acquisition, list/action menus and skill effects remain separate.'}
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print('Skill Info:',len(results),'passed',flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,default=ROOT/'build/skill-info-prototype');p.add_argument('--only',type=int);a=p.parse_args();run(a.source,a.only)
