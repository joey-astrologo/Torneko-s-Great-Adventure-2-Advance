"""Native skill assignment confirmation, cancellation and actual Set mutation."""
import argparse,json,struct
from pathlib import Path
import mgba.log
from tools.emulator import Session,Debugger
from tools.rom import ROOT,digest,require
from tools.dialogue_checks import TextChecks
from tools.verify_service_ui import materialize


def run(source=ROOT/'build/skill-menu-prototype',only=None):
    out=source/'skill-set-validation';mgba.log.silence()
    rom=(source/'torneko-2-english.gba').read_bytes();build=json.loads((source/'build.json').read_text())
    require(digest(rom)==build['output_sha256'],'Stale skill menu ROM')
    from tools import verify_player_status_prototype as status
    previous=status.OUT
    try:status.OUT=out;fixture=status.ready(rom,build)
    finally:status.OUT=previous
    definitions=build['skill_info']['definitions'];eligible={r['id'] for r in definitions if r['menu_eligible']}
    direct={r['offset']+0x08000000:r for r in build['skill_menu']['entries']}
    direct.update({r['offset']+0x08000000:r|{'capacity':256} for r in build['skill_info']['entries'] if r['kind'] in ('header','footer','footer-label')})
    names={r['offset']+0x08000000:r for r in build['skill_info']['entries'] if r['kind']=='name'}
    results=[];cases=[(False,True)]
    for shield,learned in cases:
        name='set-weapon'
        if only and name!=only:continue
        ids={15}
        print('Skill menu:',name,flush=True)
        with Session(rom,out/name) as g:
            g.restore(fixture);m=g.core.memory;overrides=[];formats=[];pending=[];draws=[];images={};pixels=0;entries=[];returns=[];creations=[];info_entries=[]
            def write(a,data):
                overrides.append({'address':a,'before':bytes(m[a:a+len(data)]).hex(),'after':data.hex()})
                for i,v in enumerate(data):m.u8[a+i]=v
            hero=m.u32[0x02001624];write(hero+0x90,b'\1');write(0x02004DFA,bytes(int(i in ids) for i in range(128)));write(0x02004CF0,bytes(144))
            item=bytearray(120);struct.pack_into('<I',item,0,0xC8800000);item[4:6]=bytes((1,1));item[8]=bytes(m[0x020013D0:0x020014D0]).index(1);write(0x0200DF28,item)
            at=0x02003BAC+20;write(at,struct.pack('<I',m.u32[at]|0x40000000))
            resources={p:r|{'layout':{'pages':[[r['id']]]}} for p,r in direct.items() if b'%' not in bytes.fromhex(r['encoded_hex'])}
            resources.update({r['offset']+0x08000000:r|{'layout':{'pages':[[r['id']]]}} for r in build['skill_info']['entries'] if r['kind']=='description'})
            c=TextChecks(g,resources)
            def callback(e):
                a,r=e['address'],e['registers']
                if a==0x08020F9C:entries.append(e|{'guard':bytes(m[r[13]:r[13]+32]).hex()})
                if a==0x0802172C:info_entries.append(e)
                if a==0x08001798:creations.append(e)
                if a==0x0801D044:draws.clear()
                if a in (0x08001750,0x08001888):draws[:]=[d for d in draws if d['window']!=r[0]]
                if a==0x08000FB8 and r[1] not in direct:c.resources.pop(r[0],None)
                if a==0x08000FB8 and r[1] in direct:
                    row=direct[r[1]];cap=row['capacity'];args=r[2:4]+[m.u32[r[13]+i*4] for i in range(4)]
                    expected=4 if row['kind']=='list-row' or row['id'].startswith('skill-info.') else 0x24 if row['kind']=='confirmation' else 8
                    require(r[0]==r[13]+expected,'Skill menu output ownership differs: '+repr((row['id'],hex(r[0]),hex(r[13]))))
                    payload=materialize(bytes.fromhex(row['encoded_hex']),args,m);require(len(payload)<=cap,'Skill menu format overflow')
                    selected=[names[v]['skill_id'] for v in args if v in names]
                    pending.append((r,row,payload,bytes(m[r[0]+cap:r[0]+cap+16]),selected))
                if pending and a==(pending[-1][0][14]&~1):
                    old,row,payload,guard,selected=pending.pop();at=old[0];cap=row['capacity']
                    require(bytes(m[at:at+len(payload)])==payload and bytes(m[at+cap:at+cap+16])==guard and r[4:12]==old[4:12] and r[13]==old[13],'Skill menu output/guard/ABI differs')
                    c.resources[at]={'id':row['id'],'encoded_hex':payload.hex(),'layout':{'pages':[[row['id']]]}}
                    formats.append({'id':row['id'],'hex':payload.hex(),'bytes':len(payload),'capacity':cap,'skill_ids':selected,'guard_abi_preserved':True})
                if a==0x08001BC4 and c.active:
                    w=r[0];key=(w,r[1],r[13],r[14],m.u8[w+2],m.u8[w+3])
                    if not draws or draws[-1]['key']!=key:draws.append({'key':key,'resource':c.active['id'],'window':w,'code':r[1],'x':m.u8[w+2],'y':m.u8[w+3],'origin':[m.u8[w],m.u8[w+1]],'foreground':m.u8[0x020000C2],'bank':m.u16[m.u32[w+12]]>>12})
                if a in c.ADDRESSES:c.callback(e)
                if a==0x0802140A:
                    old=entries[-1]['registers'];require(r[4:12]==old[4:12] and r[13]==old[13] and r[0]==old[14] and bytes(m[r[13]:r[13]+32]).hex()==entries[-1]['guard'],'Skill menu caller ABI/guard differs');returns.append(e)
            def capture(tag,front=False):
                nonlocal pixels
                g.frames(3);pic=g.capture(tag);images[tag+'.png']=digest((g.output/(tag+'.png')).read_bytes());require(draws,'Missing skill menu glyphs')
                for d in draws:
                    if front and d['window']!=c.reads[-1]['window']:continue
                    glyph,_=c.glyph_record(d['code']);colour=m.u16[0x05000000+2*(16*d['bank']+d['foreground'])];rgb=tuple(((colour>>s)&31)*255//31 for s in (0,5,10))
                    if d['resource']=='skill-menu.914' and d['x']<6:
                        require(d['x']+glyph['advance']<=6 and all('#' not in line for line in glyph['rows']),'Skill category text enters the cursor reserve')
                        continue # The blinking cursor legitimately overlays this blank reserve.
                    for y,line in enumerate(glyph['rows']):
                        for x,bit in enumerate(line):
                            px=d['origin'][0]+d['x']+x;py=d['origin'][1]+d['y']*16+y
                            require((pic.getpixel((px,py))==rgb)==(bit=='#'),'Skill menu final pixels differ: '+repr((name,tag,px,py,hex(d['code']))));pixels+=1
            with Debugger(g,callback,max_events=500000) as debug:
                addresses=(0x08020F9C,0x0802140A,0x0802172C,0x08001798,0x08001750,0x08001888,0x0801D044,0x08000FB8,0x08021DE6,0x08021E10,0x08021E32,0x08021E4C,0x08021352,0x080214F4,0x08021588,0x080215B8,0x080215EE,0x08021616,0x08021792,0x08021846,0x08021884,0x08021898)
                for a in set(c.ADDRESSES+addresses):debug.breakpoint(a)
                g.press('B',hold=8,wait=120);g.press('DOWN',wait=30);g.press('A',wait=120);capture('categories')
                require(entries and creations[-1]['registers'][:4]==[1,3,6,2],'Warrior categories missing')
                if shield:g.press('DOWN',wait=30)
                g.press('A',wait=120);capture('list')
                g.press('A',wait=120);capture('actions')
                require(c.completed('skill-menu.89c'),'Enabled Set action missing')
                g.press('A',wait=120);capture('confirmation',True)
                require(c.completed('skill-menu.92c'),'Set confirmation missing')
                g.press('B',wait=120);capture('cancelled-confirmation')
                require(bytes(m[0x02004CF0:0x02004D80])==bytes(144),'Cancelled Set changed assignment')
                g.press('A',wait=120);capture('list-reopened');g.press('A',wait=120);capture('actions-reopened');g.press('A',wait=120);capture('confirmation-reopened',True)
                g.press('A',wait=120);capture('set-result',True)
                require(c.completed('skill-menu.960'),'Set result missing')
                require(bytes(m[0x02004CF3:0x02004CF6])==bytes((15,0,0)),'Native Set did not assign Double-Edged Slash to Oaken club')
                g.press('A',wait=120);capture('categories-returned');g.press('B',wait=120)
            covered={i for r in formats if r['capacity']==64 for i in r['skill_ids']}
            require(covered==ids,'Skill source set differs: '+repr((name,covered,ids)))
            require(len(entries)==len(returns)==1 and not pending and not c.active and g.snapshot().battery==fixture.battery,'Skill menu return/guard/battery incomplete')
            require(bytes(m[0x02004DFA:0x02004E7A])==bytes(int(i in ids) for i in range(128)),'Skill Set changed learned state')
            results.append({'case':name,'skill_ids':sorted(ids),'covered_ids':sorted(covered),'reads':c.reads,'formats':formats,'inputs':g.inputs,'overrides':overrides,'visible_pixels_checked':pixels,'caller_guard_abi_preserved':True,'returns':returns,'info_entries':info_entries,'images':images})
    report={'passed':True,'rom_sha256':digest(rom),'cases':results,'scope':'Controlled warrior, learned skill15 and equipped Oaken club. Ordinary buttons open the original Set action, cancel and reopen confirmation, perform native assignment, display completion and close. Source/format/output/ABI/final pixels and unchanged battery checked. Acquisition and combat use remain separate.'}
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print('Skill menu:',len(results),'passed',flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,default=ROOT/'build/skill-menu-prototype');p.add_argument('--only');a=p.parse_args();run(a.source,a.only)
