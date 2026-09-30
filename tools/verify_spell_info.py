"""Native item153 Info selects every spell, retaining cost, target and description."""
import argparse,json,struct
from pathlib import Path
import mgba.log
from tools.emulator import Session,Debugger
from tools.rom import ROOT,digest,require
from tools.dialogue_checks import TextChecks,player_layout_cases
from tools.name_entry import HERO
from tools.verify_result_ui import native_format


def run(source=ROOT/'build/spell-info-prototype',only=None):
    out=source/'spell-info-validation';mgba.log.silence()
    rom=(source/'torneko-2-english.gba').read_bytes();build=json.loads((source/'build.json').read_text())
    require(digest(rom)==build['output_sha256'],'Stale spell Info ROM')
    from tools import verify_player_status_prototype as status
    previous=status.OUT
    try:status.OUT=out;fixture=status.ready(rom,build)
    finally:status.OUT=previous
    definitions=build['spell_info']['definitions'];entries={r['id']:r for r in build['spell_info']['entries']}
    header=entries['spell-info.840'];results=[]
    cases=[(i,'native',None) for i in range(61) if only is None or i==only]
    if only in (None,22):cases.extend((22,label,raw) for label,raw in player_layout_cases())
    for ident,label,player in cases:
        name=f'{ident}-{label}';print('Spell Info:',name,flush=True)
        with Session(rom,out/name) as g:
            g.restore(fixture);m=g.core.memory;initial=[];returns=[];formats=[];pending={};overrides=[];draws=[];creations=[];images={};pixels=0
            def write(a,data):
                overrides.append({'address':a,'before':bytes(m[a:a+len(data)]).hex(),'after':data.hex()})
                for n,v in enumerate(data):m.u8[a+n]=v
            item=bytearray(120);struct.pack_into('<I',item,0,0xC8000000);item[4:6]=bytes((ident,1));item[8]=bytes(m[0x020013D0:0x020014D0]).index(153)
            write(0x0200DF28,item);at=0x02003BAC+153*20;write(at,struct.pack('<I',m.u32[at]|0x40000000))
            if player:write(HERO,player.ljust(16,b'\0'))
            description=entries[f'spell.description.{ident}']
            resources={description['offset']+0x08000000:description|{'layout':{'pages':[[description['id']]]}}}
            c=TextChecks(g,resources)
            def callback(e):
                a,r=e['address'],e['registers']
                if a==0x08022828:
                    require(r[0]==ident and r[14]==0x08017B13,'Item153 selected unexpected native spell')
                    initial.append(e|{'guard':bytes(m[r[13]:r[13]+32]).hex()})
                if a==0x08001798:creations.append(e)
                if a==0x08000FB8 and r[14]==0x0802286B:
                    require(r[1]==header['offset']+0x08000000 and r[0]==r[13]+4,'Spell header pointer/output differs')
                    args=r[2:4]+[m.u32[r[13]]]
                    target=entries['spell-info.'+format(0x8BC+4*definitions[ident]['target_kind'],'03x')]
                    require(args==[entries[f'spell.name.{ident}']['offset']+0x08000000,definitions[ident]['hp_cost'],target['offset']+0x08000000],'Native spell name/cost/target selection differs')
                    payload=native_format(bytes.fromhex(header['encoded_hex']),args,m)
                    require(len(payload)<=header['maximum_bytes']<=256,'Spell header exceeds256bytes')
                    pending.update(regs=r,payload=payload,guard=bytes(m[r[0]+256:r[0]+272]),args=args)
                if a==0x0802286A and pending:
                    old=pending['regs'];at=old[0];payload=pending['payload']
                    require(bytes(m[at:at+len(payload)])==payload and bytes(m[at+256:at+272])==pending['guard'] and r[4:12]==old[4:12] and r[13]==old[13],'Spell header output/guard/ABI differs')
                    c.resources[at]={'id':header['id'],'encoded_hex':payload.hex(),'layout':{'pages':[[header['id']]]}}
                    formats.append({'id':header['id'],'hex':payload.hex(),'bytes':len(payload),'arguments':pending['args'],'guard_abi_preserved':True});pending.clear()
                if a==0x08001BC4 and c.active:
                    w=r[0];key=(w,r[1],r[13],r[14],m.u8[w+2],m.u8[w+3])
                    if not draws or draws[-1]['key']!=key:
                        require(m.u8[w+2]+c.glyph_record(r[1])[0]['advance']<=216,'Spell Info exceeds its216px text budget')
                        draws.append({'key':key,'window':w,'code':r[1],'x':m.u8[w+2],'y':m.u8[w+3],'origin':[m.u8[w],m.u8[w+1]],'foreground':m.u8[0x020000C2],'bank':m.u16[m.u32[w+12]]>>12})
                if a in c.ADDRESSES:c.callback(e)
                if a==0x080228C8:
                    old=initial[-1]['registers'];require(r[4:12]==old[4:12] and r[13]==old[13] and r[0]==old[14] and bytes(m[r[13]:r[13]+32]).hex()==initial[-1]['guard'],'Spell Info caller ABI/guard differs');returns.append(e)
            def capture(tag):
                nonlocal pixels
                g.frames(3);pic=g.capture(tag);images[tag+'.png']=digest((g.output/(tag+'.png')).read_bytes());require(draws,'No spell Info glyphs')
                for d in draws:
                    glyph,_=c.glyph_record(d['code']);colour=m.u16[0x05000000+2*(16*d['bank']+d['foreground'])];rgb=tuple(((colour>>s)&31)*255//31 for s in (0,5,10))
                    for y,line in enumerate(glyph['rows']):
                        for x,bit in enumerate(line):
                            px=d['origin'][0]+d['x']+x;py=d['origin'][1]+d['y']*16+y
                            require((pic.getpixel((px,py))==rgb)==(bit=='#'),'Spell Info final pixels differ: '+repr((name,tag,px,py,hex(d['code']))));pixels+=1
            with Debugger(g,callback,max_events=150000) as debug:
                for a in set(c.ADDRESSES+(0x08022828,0x080228C8,0x08001798,0x08000FB8,0x0802286A)):debug.breakpoint(a)
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
                    require(creations[-1]['registers'][:4]==[1,4,28,6],'Spell Info geometry changed')
                    require([r['id'] for r in c.reads[first:]]==[header['id'],description['id']],'Complete native spell Info sources missing')
                    capture('info-'+str(repeat));g.press('B',wait=120)
                    if repeat==0:
                        g.press('A',wait=120)
                        for _ in range(actions.index(40)):g.press('DOWN',wait=20)
            require(len(initial)==len(returns)==len(formats)==2 and not c.active and not pending and g.snapshot().battery==fixture.battery,'Spell Info close/reopen/battery incomplete')
            results.append({'case':name,'spell_id':ident,'player_case':label,'reads':c.reads,'formats':formats,'inputs':g.inputs,'overrides':overrides,'visible_pixels_checked':pixels,'caller_guard_abi_preserved':True,'selection':initial,'return':returns,'images':images})
    report={'passed':True,'rom_sha256':digest(rom),'cases':results,'scope':'Controlled item153 records select all61 spell IDs through ordinary inventory Info buttons, with no PC/register dispatch override. Each native header preserves the original cost and target and renders the full independently translated description in the original224px/six-row window,216px text region. Three extra seven-character player-name cases,256-byte header guards, coloured final pixels, caller ABI, closing/reopening and unchanged battery are checked. Spell acquisition, casting, menu lists and other consumers are separate.'}
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print('Spell Info:',len(results),'passed',flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,default=ROOT/'build/spell-info-prototype');p.add_argument('--only',type=int);a=p.parse_args();run(a.source,a.only)
