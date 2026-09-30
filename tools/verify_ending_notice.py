"""Original pre-ending save-cancellation message, without saving or ending."""
import argparse,json
from pathlib import Path
import mgba.log
from tools.rom import ROOT,digest,require
from tools.emulator import Session,Debugger,ffi
from tools.bakery_playtest import service_ready
from tools.dialogue_checks import TextChecks

def run(source):
 out=source/'ending-notice-validation';rom=(source/'torneko-2-english.gba').read_bytes();b=json.loads((source/'build.json').read_text());require(digest(rom)==b['output_sha256'],'Stale ending notice ROM');mgba.log.silence();fixture=service_ready(rom,out);row=b['ending_notice']['entries'][0];results=[]
 for button in ('A','B'):
  with Session(rom,out/button) as g:
   g.restore(fixture);m=g.core.memory;c=TextChecks(g,{row['offset']+0x08000000:row});initial=[];returns=[];modals=[];modal_returns=[];overrides=[];draws=[];images={};pixels=0
   inventory=bytes(m[0x0200DF28:0x0200E888]);hero=m.u32[0x02001624];gold=m.u32[hero+0x60]
   def jump(e,at,reason):overrides.append({'event':e,'pc_after':at,'reason':reason});require(g.core._core.writeRegister(g.core._core,b'pc',ffi.new('uint32_t*',at)),'Ending notice redirect failed')
   def cb(e):
    a,r=e['address'],e['registers']
    if a==0x0801DFAC and not initial:initial.append(e|{'guard':bytes(m[r[13]:r[13]+32]).hex()});jump(e,0x08054DA4,'Controlled bank call into full original ending-owner frame.');return
    if not initial or returns:return
    if a==0x08054DA8:
     overrides.append({'event':e,'register':4,'after':0,'reason':'Original zero callback/argument after prelude.'});g.core.cpu.gprs[4]=0;jump(e,0x08054E04,'Select original save-cancellation message block; saving and scene changes excluded.')
    if a==0x08015A34:require(r[0]==row['offset']+0x08000000 and r[3]==0x08153190,'Ending notice source/placement differs');modals.append(e)
    if a==0x08054E20:
     old=modals[-1]['registers'];require(r[4:12]==old[4:12] and r[13]==old[13],'Ending notice modal ABI differs');modal_returns.append(e)
    if a==0x08054E40:jump(e,0x08054EE4,'Original any-button wait and window closure completed; skip subsequent ending/progression.')
    if a==0x08054EEC:
     old=initial[0]['registers'];require(r[4:12]==old[4:12] and r[13]==old[13] and r[1]==old[14] and bytes(m[r[13]:r[13]+32]).hex()==initial[0]['guard'],'Ending notice caller ABI/guard differs');returns.append(e)
    if a==0x080021B4 and r[1] in c.resources:
     w=r[0];require(bytes(m[w:w+2])==bytes((8,120)) and bytes(m[w+4:w+6])==bytes((28,2)),'Ending notice original window differs: '+bytes(m[w:w+24]).hex())
    if a==0x08001BC4 and c.active:
     w=r[0];key=(w,r[1],r[13],r[14],m.u8[w+2],m.u8[w+3])
     if not draws or draws[-1]['key']!=key:draws.append({'key':key,'code':r[1],'x':m.u8[w+2],'y':m.u8[w+3],'origin':[m.u8[w],m.u8[w+1]],'foreground':m.u8[0x020000C2],'bank':m.u16[m.u32[w+12]]>>12})
    if a in c.ADDRESSES:c.callback(e)
   with Debugger(g,cb,max_events=80000) as d:
    for a in set(c.ADDRESSES)|{0x0801DFAC,0x08054DA8,0x08015A34,0x08054E20,0x08054E40,0x08054EEC}:d.breakpoint(a)
    g.press('A',hold=1,wait=120);require(len(c.reads)==len(modals)==1 and not c.active and not returns,'Ending notice failed to wait: '+repr((len(c.reads),len(modals),len(modal_returns),len(returns),bool(c.active))));pic=g.capture('cancelled');images['cancelled.png']=digest((g.output/'cancelled.png').read_bytes())
    for v in draws:
     glyph,_=c.glyph_record(v['code']);colour=m.u16[0x05000000+2*(16*v['bank']+v['foreground'])];rgb=tuple(((colour>>s)&31)*255//31 for s in (0,5,10))
     for y,line in enumerate(glyph['rows']):
      for x,bit in enumerate(line):require((pic.getpixel((v['origin'][0]+v['x']+x,v['origin'][1]+16*v['y']+y))==rgb)==(bit=='#'),'Ending notice final pixels differ');pixels+=1
    g.press('A',hold=1,wait=120);require(len(modal_returns)==1 and not returns,'Ending notice modal/secondary wait differs');g.press(button,hold=1,wait=120);require(len(returns)==1,'Ending notice secondary wait did not dismiss')
   require(bytes(m[0x0200DF28:0x0200E888])==inventory and m.u32[hero+0x60]==gold and g.snapshot().battery==fixture.battery,'Ending notice changed items/gold/save');results.append({'case':button,'inputs':g.inputs,'overrides':overrides,'reads':c.reads,'modals':modals,'modal_returns':modal_returns,'returns':returns,'caller_guard_abi_preserved':True,'visible_pixels_checked':pixels,'images':images})
 report={'passed':True,'rom_sha256':digest(rom),'cases':results,'scope':'Controlled bank-call entry into full54DA4 frame and original save-cancellation block54E04..54E40, native modal, any-button wait with A/B, window closure and original epilogue. Original source/geometry, final pixels and modal/caller ABI checked. Save decision/write, ending sequence and natural reachability excluded. Inventory/gold/battery unchanged.'};(out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print('Ending notice:',len(results),'passed')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--source',type=Path,default=ROOT/'build/english');run(p.parse_args().source)
