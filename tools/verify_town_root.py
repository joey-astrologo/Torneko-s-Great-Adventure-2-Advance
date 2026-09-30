"""town Items/Option root, child routing and reopening without overlap."""
import argparse,json,struct
from pathlib import Path
import mgba.log
from tools.rom import ROOT,digest,require
from tools.emulator import Session,Debugger,ffi
from tools.dialogue_checks import TextChecks
from tools.bakery_playtest import service_ready
from tools.compact_font import encode

def run(source=ROOT/'build/english'):
 out=source/'town-root-validation';mgba.log.silence();rom=(source/'torneko-2-english.gba').read_bytes();build=json.loads((source/'build.json').read_text());require(digest(rom)==build['output_sha256'],'Stale town-root ROM');fixture=service_ready(rom,out);row=build['town_root']['entries'][0];results=[]
 for case in ('cancel','items-empty','items-populated','option'):
  print('Town root:',case,flush=True)
  with Session(rom,out/case) as g:
   g.restore(fixture);m=g.core.memory;initial=[];returns=[];overrides=[];creations=[];closures=[];children=[];draws=[];images={};pixels=0;c=TextChecks(g,{row['offset']+0x08000000:row|{'layout':{'pages':[[row['id']]]}}});root_windows=[]
   def write(at,data):
    overrides.append({'address':at,'before':bytes(m[at:at+len(data)]).hex(),'after':data.hex()})
    for i,v in enumerate(data):m.u8[at+i]=v
   write(0x0200DF28,bytes(2400))
   if case=='items-populated':
    item=bytearray(120);struct.pack_into('<I',item,0,0xC8000000);item[4:6]=b'\1\1';item[8]=bytes(m[0x020013D0:0x020014D0]).index(1);write(0x0200DF28,item)
   before=bytes(m[0x0200DF28:0x0200DF28+2400]);hero=m.u32[0x02001624];gold=m.u32[hero+0x60]
   def callback(e):
    a,r=e['address'],e['registers']
    if a==0x0801DFAC and not initial:
     require(r[0]==0x020141AC,'Town root controlled caller differs');initial.append(e|{'guard':bytes(m[r[13]:r[13]+32]).hex()});overrides.append({'event':e,'pc_after':0x0802068C,'reason':'Controlled native bank invocation redirected to entire town-root function with the same context pointer.'});require(g.core._core.writeRegister(g.core._core,b'pc',ffi.new('uint32_t*',0x0802068C)),'Town root redirect failed');return
    if not initial or returns:return
    if a==0x08001798:creations.append(e)
    if a==0x080021B4 and r[1]==row['offset']+0x08000000:
     require(bytes(m[r[0]:r[0]+2])==bytes((8,24)) and bytes(m[r[0]+4:r[0]+6])==bytes((5,2)),'Town root actual geometry differs');root_windows.append(r[0]);draws.clear()
    if a==0x08001888:closures.append(e)
    if a in (0x0801E490,0x0801A780):
     require(root_windows and closures and closures[-1]['registers'][0]==root_windows[-1] and m.u16[root_windows[-1]+16]==0,'Town root remained active beneath child');children.append(e)
    if a==0x08001BC4 and c.active:
     w=r[0];key=(w,r[1],r[13],r[14],m.u8[w+2],m.u8[w+3])
     if not draws or draws[-1]['key']!=key:draws.append({'key':key,'window':w,'code':r[1],'x':m.u8[w+2],'y':m.u8[w+3],'origin':[m.u8[w],m.u8[w+1]],'foreground':m.u8[0x020000C2],'bank':m.u16[m.u32[w+12]]>>12})
    if a in c.ADDRESSES:c.callback(e)
    if a==0x0802075E:
     old=initial[0]['registers'];require(r[4:12]==old[4:12] and r[13]==old[13] and r[0]==old[14] and bytes(m[r[13]:r[13]+32]).hex()==initial[0]['guard'],'Town-root caller ABI differs');returns.append(e)
   def capture(tag):
    nonlocal pixels
    g.frames(8);pic=g.capture(tag);images[tag+'.png']=digest((g.output/(tag+'.png')).read_bytes());require(draws and not c.active,'Town root missing complete render')
    for d in draws:
     glyph,_=c.glyph_record(d['code'])
     if d['x']<6:require(all('#' not in l for l in glyph['rows']),'Town cursor reserve contains text');continue
     require(d['x']+glyph['advance']<=40,'Town command clips');colour=m.u16[0x05000000+2*(16*d['bank']+d['foreground'])];rgb=tuple(((colour>>s)&31)*255//31 for s in (0,5,10))
     for y,line in enumerate(glyph['rows']):
      for x,bit in enumerate(line):
       px=d['origin'][0]+d['x']+x;py=d['origin'][1]+d['y']*16+y;require((pic.getpixel((px,py))==rgb)==(bit=='#'),'Town root final pixels differ');pixels+=1
   with Debugger(g,callback,max_events=150000) as debug:
    for a in set(c.ADDRESSES)|{0x0801DFAC,0x0802075E,0x08001798,0x08001888,0x0801E490,0x0801A780}:debug.breakpoint(a)
    g.press('A',wait=180);capture('root');g.press('UP',wait=20);g.press('DOWN',wait=20);capture('cursor-wrap')
    if case!='cancel':
     if case=='option':g.press('DOWN',wait=20)
     for cycle in range(2):
      old=len(c.reads);g.press('A',wait=120);g.capture('child-'+str(cycle));images['child-'+str(cycle)+'.png']=digest((g.output/('child-'+str(cycle)+'.png')).read_bytes())
      require(children[-1]['address']==(0x0801A780 if case=='option' else 0x0801E490),'Town root selected wrong child')
      for _ in range(8):
       if len(c.reads)>old:break
       g.press('A' if case=='items-empty' else 'B',wait=120)
      require(len(c.reads)==old+1,'Town root did not reopen after child');capture('reopened-'+str(cycle))
    g.press('B',wait=120)
   require(len(initial)==len(returns)==1 and len(children)==(0 if case=='cancel' else 2) and not c.active,'Town root incomplete')
   require(bytes(m[0x0200DF28:0x0200DF28+2400])==before and m.u32[hero+0x60]==gold and g.snapshot().battery==fixture.battery,'Town root browsing changed items/gold/battery')
   results.append({'case':case,'inputs':g.inputs,'overrides':overrides,'reads':c.reads,'children':children,'closures':closures,'creations':creations,'caller_guard_abi_preserved':True,'visible_pixels_checked':pixels,'images':images})
 report={'passed':True,'rom_sha256':digest(rom),'cases':results,'scope':'Native bank invocation is explicitly redirected to complete2068C town-root owner with the original020141AC context. Original cursor and Items/Option mappings, cancellation, empty/populated item child and Option child, twice reopening, exact visible pixels, caller ABI and item/gold/battery preservation. The root closes before either child, so widening32 to40px creates no neighbor overlap. Natural4BF78 town invocation remains separate.'}
 (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print('Town root:',len(results),'passed',flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,default=ROOT/'build/english');run(p.parse_args().source)
