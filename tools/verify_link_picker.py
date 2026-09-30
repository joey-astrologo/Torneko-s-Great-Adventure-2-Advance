"""Native original-size link storage picker, Trade/Info, cancellation/reopening."""
import argparse,json,struct
from pathlib import Path
import mgba.log
from tools.rom import ROOT,digest,require
from tools.emulator import Session,Debugger,ffi
from tools.bakery_playtest import service_ready
from tools.verify_items import ItemChecks

def run(source):
 out=source/'link-picker-validation';rom=(source/'torneko-2-english.gba').read_bytes();b=json.loads((source/'build.json').read_text());require(digest(rom)==b['output_sha256'],'Stale link picker ROM');mgba.log.silence();fixture=service_ready(rom,out);row=next(r for r in b['link_text']['entries'] if r['source']['offset']==0x6ECAC);results=[]
 for action in ('cancel','trade','info'):
  case=action;print('Link picker:',case,flush=True)
  with Session(rom,out/case) as g:
   g.restore(fixture);m=g.core.memory;c=ItemChecks(g,b);c.materialized[row['offset']+0x08000000]=row;initial=[];returns=[];overrides=[];draws=[];images={};pixels=0;cycle=0;infos=[];parent_checks=0
   def write(at,raw):
    overrides.append({'address':at,'before':bytes(m[at:at+len(raw)]).hex(),'after':raw.hex()})
    for i,v in enumerate(raw):m.u8[at+i]=v
   mapping=bytes(m[0x020013D0:0x020014D0]);stored=bytearray(250*12)
   for i in range(9):
    item=bytearray(12);struct.pack_into('<I',item,0,0xC8000000);item[5]=1;item[8]=mapping.index(1+i);stored[i*12:i*12+12]=item;at=0x02003BAC+20*(1+i);write(at,struct.pack('<I',m.u32[at]|0x40000000))
   write(0x0200F008,stored);write(0x02002C2A,struct.pack('<H',9));inventory=bytes(m[0x0200DF28:0x0200E888]);hero=m.u32[0x02001624];gold=m.u32[hero+0x60]
   def jump(e,at):overrides.append({'event':e,'pc_after':at,'reason':'Controlled bank call into complete original57E08 storage picker; transfer and natural access excluded.'});require(g.core._core.writeRegister(g.core._core,b'pc',ffi.new('uint32_t*',at)),'Link picker redirect failed')
   def callback(e):
    a,r=e['address'],e['registers']
    if a==0x0801DFAC and len(initial)==len(returns):initial.append(e|{'guard':bytes(m[r[13]:r[13]+32]).hex()});draws.clear();jump(e,0x08057E08);return
    if len(initial)==len(returns):return
    if a in (0x08001750,0x08001888):draws[:]=[v for v in draws if v['window']!=r[0]]
    if a==0x080021B4 and r[1]==row['offset']+0x08000000:
     w=r[0];require(bytes(m[w:w+2])==bytes((192,56)) and bytes(m[w+4:w+6])==bytes((5,2)),'Link action original geometry differs');parent=m.u32[0x0200CD2C];require(bytes(m[parent:parent+2])==bytes((8,24)) and m.u8[parent+4]==21,'Link parent original geometry differs');require(m.u8[w]-(m.u8[parent]+8*m.u8[parent+4])==16,'Link outer border gap differs')
    if a==0x08001BC4 and c.active:
     w=r[0];key=(w,r[1],r[13],r[14],m.u8[w+2],m.u8[w+3])
     if not draws or draws[-1]['key']!=key:draws.append({'key':key,'window':w,'code':r[1],'x':m.u8[w+2],'y':m.u8[w+3],'origin':[m.u8[w],m.u8[w+1]],'foreground':m.u8[0x020000C2],'bank':m.u16[m.u32[w+12]]>>12,'id':c.active['id']})
    if a in c.ADDRESSES:c.callback(e)
    if a==0x08017A4C:infos.append(e)
    if a==0x08058080:
     old=initial[-1]['registers'];require(r[4:12]==old[4:12] and r[13]==old[13] and r[1]==old[14] and bytes(m[r[13]:r[13]+32]).hex()==initial[-1]['guard'],'Link picker caller ABI/guard differs');require(r[0]==int(cycle==2 and action=='trade'),'Link picker result differs');returns.append(e)
   def capture(tag):
    nonlocal pixels
    g.frames(8);pic=g.capture(tag);images[tag+'.png']=digest((g.output/(tag+'.png')).read_bytes());require(draws and not c.active,'Link picker text incomplete')
    for v in draws:
     glyph,_=c.glyph_record(v['code']);colour=m.u16[0x05000000+2*(16*v['bank']+v['foreground'])];rgb=tuple(((colour>>s)&31)*255//31 for s in (0,5,10))
     if v['id']==row['id']:require(v['x']>=6,'Link action cursor overlaps label')
     for y,line in enumerate(glyph['rows']):
      for x,bit in enumerate(line):require((pic.getpixel((v['origin'][0]+v['x']+x,v['origin'][1]+16*v['y']+y))==rgb)==(bit=='#'),'Link picker pixels differ: '+repr((tag,v['id'],hex(v['code']),v['x'],v['y'])));pixels+=1
   def parent_state():
    w=m.u32[0x0200CD2C];base=m.u32[w+12];control=m.u16[0x0400000E];char_base=0x06000000+((control>>2)&3)*0x4000;words=[m.u16[base+y*64+x*2] for y in range(m.u8[w+5]*2) for x in range(m.u8[w+4])];indices=sorted({v&0x3FF for v in words});return digest(bytes(m[w:w+24])+b''.join(v.to_bytes(2,'little') for v in words)+b''.join(bytes(m[char_base+i*32:char_base+(i+1)*32]) for i in indices))
   with Debugger(g,callback,max_events=600000) as d:
    for a in set(c.ADDRESSES)|{0x0801DFAC,0x08058080,0x08017A4C,0x08001750,0x08001888}:d.breakpoint(a)
    for cycle in range(3):
     g.press('A',hold=1,wait=120);capture('list-'+str(cycle));g.press('RIGHT',wait=120);capture('page2-'+str(cycle));require(m.u16[0x0200CEE2]==1,'Link second page missing');g.press('LEFT',wait=120);require(m.u16[0x0200CEE2]==0,'Link first page missing');before=parent_state()
     g.press('A',wait=120);capture('actions-'+str(cycle));g.press('DOWN',wait=20);capture('info-cursor-'+str(cycle));g.press('UP',wait=20);g.press('B',wait=120);require(parent_state()==before,'Link action cancellation changed parent');parent_checks+=1
     if cycle<2 or action=='cancel':g.press('B',wait=120)
     elif action=='trade':g.press('A',wait=120);g.press('A',wait=120)
     else:
      g.press('A',wait=120);g.press('DOWN',wait=20);g.press('A',wait=120);capture('info');g.press('B',wait=120);capture('info-return');require(parent_state()==before,'Link Info return changed parent');parent_checks+=1;g.press('B',wait=120)
     require(len(returns)==cycle+1,'Link picker did not return')
   flags=bytes(m[0x0200CDE8:0x0200CEE2]);require(flags==(b'\1'+bytes(249) if action=='trade' else bytes(250)),'Link native selected-item flags differ');require(bytes(m[0x0200F008:0x0200FBC0])==stored,'Link picker changed stored item identities');require(bytes(m[0x0200DF28:0x0200E888])==inventory and m.u32[hero+0x60]==gold and g.snapshot().battery==fixture.battery,'Link picker changed inventory/gold/save');require(not c.stack and not c.active,'Link picker left pending item render');require(len(infos)==int(action=='info'),'Link Info action count differs')
   results.append({'case':case,'inputs':g.inputs,'overrides':overrides,'reads':c.reads,'formats':c.formats,'returns':returns,'infos':infos,'parent_restoration_checks':parent_checks,'caller_guard_abi_preserved':True,'visible_pixels_checked':pixels,'images':images});(out/'partial.json').write_text(json.dumps(results,indent=2)+'\n')
 report={'passed':True,'rom_sha256':digest(rom),'cases':results,'scope':'Controlled nine native-format storage records and count, full original57E08 picker after bank-call redirect. Original168px list and40px Trade/Info panel with8px outer border gap, both pages, cursor toggles, repeated action/list cancellation and reopening, exact parent restoration, native Info and native Trade selection flag. Item formatter64-byte guards, complete English, final pixels and caller ABI. Link transfer and natural access excluded; stored/carried item identities, gold and battery unchanged.'};(out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print('Link picker:',len(results),'passed')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--source',type=Path,default=ROOT/'build/english');run(p.parse_args().source)
