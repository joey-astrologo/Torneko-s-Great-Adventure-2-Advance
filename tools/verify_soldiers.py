"""Native type2 object selection, paged pixels and player-name bounds for soldiers."""
import argparse,json,struct
from pathlib import Path
import mgba.log
from tools.dialogue_checks import TextChecks,player_layout_cases
from tools.name_entry import HERO
from tools.emulator import Session,Debugger
from tools.rom import ROOT,digest,require


def run(source=ROOT/'build/soldier-prototype'):
    out=source/'soldier-validation';mgba.log.silence()
    rom=(source/'torneko-2-english.gba').read_bytes();build=json.loads((source/'build.json').read_text())
    require(digest(rom)==build['output_sha256'],'Stale soldier ROM')
    from tools import verify_player_status_prototype as status
    previous=status.OUT
    try:status.OUT=out;fixture=status.ready(rom,build)
    finally:status.OUT=previous
    rows={r['offset']+0x08000000:r for r in build['soldiers']['entries']};cases=[]
    configs=[(p,r,label,player) for p,r in rows.items() for label,player in (player_layout_cases() if '{player}' in r['english'] else [('native',None)])]
    for pointer,row,label,player in configs:
        name='selector-'+str(row['selector'])+'-'+label;print('Soldier:',name,flush=True)
        with Session(rom,out/name) as g:
            g.restore(fixture);m=g.core.memory;c=TextChecks(g,dict(rows))
            initial=[];returns=[];waits=[];draws=[];overrides=[];images={};selected=[];objects=[];restored=[];pixels=0
            hero=m.u32[0x02001624];gold=m.u32[hero+0x60];inventory=bytes(m[0x0200DF28:0x0200E888])
            def write(a,data):
                overrides.append({'address':a,'before':bytes(m[a:a+len(data)]).hex(),'after':data.hex()})
                for i,v in enumerate(data):m.u8[a+i]=v
            def callback(e):
                a,r=e['address'],e['registers']
                if a==0x08023C14 and not initial:
                    initial.append(e|{'guard':bytes(m[r[13]:r[13]+32]).hex()})
                    if player:write(HERO,player.ljust(16,b'\0'))
                if not initial or returns:return
                if a==0x08023E2C and not objects:
                    record=0x0200D048;old=bytes(m[record:record+0x44]);objects.append({'address':record,'before':old.hex()})
                    # The native action has already computed its facing tile.
                    x=m.u32[r[13]+0x10C];y=m.u32[r[13]+0x110]
                    require(0<=x<56 and 0<=y<32,'Soldier target outside native map')
                    write(record,struct.pack('<I',2));write(record+0x3E,bytes([x,y,row['selector']]))
                if a==0x0802434E and objects and not restored:
                    require(r[0]==row['selector'],'Soldier object selector differs')
                    record=objects[0];write(record['address'],bytes.fromhex(record['before']));restored.append(e)
                if a==0x08015A18:
                    require(r[0]==pointer and r[14]==0x08024375,'Soldier native object/source selection differs');selected.append(e)
                if a==0x08001750:draws[:]=[d for d in draws if d['window']!=r[0]]
                if a==0x08001BC4 and c.active:
                    w=r[0];key=(w,r[1],r[13],r[14],m.u8[w+2],m.u8[w+3])
                    if not draws or draws[-1]['key']!=key:draws.append({'key':key,'window':w,'code':r[1],'x':m.u8[w+2],'y':m.u8[w+3],'origin':[m.u8[w],m.u8[w+1]],'foreground':m.u8[0x020000C2],'bank':m.u16[m.u32[w+12]]>>12})
                if a==0x080023A0 and c.active:waits.append(e)
                c.callback(e)
                if a==0x080243BA:
                    old=initial[0]['registers']
                    require(r[4:12]==old[4:12] and r[13]==old[13] and r[0]==old[14] and bytes(m[r[13]:r[13]+32]).hex()==initial[0]['guard'],'Soldier caller ABI/guard differs');returns.append(e)
            def capture():
                nonlocal pixels
                g.frames(3);tag='page-'+str(len(images));pic=g.capture(tag);images[tag+'.png']=digest((g.output/(tag+'.png')).read_bytes());require(draws,'No soldier glyphs')
                for d in draws:
                    glyph,_=c.glyph_record(d['code']);colour=m.u16[0x05000000+2*(16*d['bank']+d['foreground'])];rgb=tuple(((colour>>s)&31)*255//31 for s in (0,5,10))
                    for y,line in enumerate(glyph['rows']):
                        for x,bit in enumerate(line):
                            px=d['origin'][0]+d['x']+x;py=d['origin'][1]+d['y']*16+y
                            require((pic.getpixel((px,py))==rgb)==(bit=='#'),'Soldier final pixels differ: '+repr((name,tag,px,py,hex(d['code']))));pixels+=1
            with Debugger(g,callback,max_events=160000) as debug:
                for a in set(TextChecks.ADDRESSES+(0x08023C14,0x08023E2C,0x0802434E,0x08015A18,0x08001750,0x080243BA)):debug.breakpoint(a)
                g.press('A',hold=1,wait=0);handled=0;final=False
                for tick in range(2400):
                    if returns:break
                    if len(waits)>handled:
                        capture();handled=len(waits);g.press('B',hold=1,wait=0)
                    elif c.completed(row['id']) and not final:
                        capture();final=True;g.press('B',hold=1,wait=0)
                    elif final and tick%20==0:g.press('B',hold=1,wait=0)
                    else:g.frames(1)
            require(len(objects)==len(restored)==len(returns)==len(selected)==1 and not c.active and c.completed(row['id']) and len(images)==len(row['layout']['pages']),'Soldier pages/return incomplete')
            require(m.u32[hero+0x60]==gold and bytes(m[0x0200DF28:0x0200E888])==inventory and g.snapshot().battery==fixture.battery,'Soldier probe changed inventory/gold/save')
            cases.append({'case':name,'id':row['id'],'selector':row['selector'],'player_case':label,'temporary_objects':objects,'object_restore_events':restored,'reads':c.reads,'selection':selected,'overrides':overrides,'inputs':g.inputs,'return':returns[0],'visible_pixels_checked':pixels,'images':images})
    (out/'report.json').write_text(json.dumps({'passed':True,'rom_sha256':digest(rom),'cases':cases,'scope':'Ordinary A enters native08023C14. At its object scan, the first existing68-byte record is temporarily assigned type2, the facing tile and selector0..6; original bytes are restored immediately after the unchanged selector load, before display. No PC/register/source-pointer redirect. All seven sources, three player-name bounds where present, pages, final pixels/colours, full caller ABI/guard and unchanged inventory/gold/battery pass. Natural soldier placement, quest progression and other selector reachability remain unverified.'},indent=2)+'\n');print('Soldier:',len(cases),'cases passed',flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,default=ROOT/'build/soldier-prototype');a=p.parse_args();run(a.source)
