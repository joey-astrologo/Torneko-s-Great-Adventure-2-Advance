"""Original form-code predicate, guard refusal and modal colour/layout checks."""
import argparse,json
from pathlib import Path
import mgba.log
from tools.rom import ROOT,digest,require
from tools.emulator import Session,Debugger,ffi
from tools.dialogue_checks import TextChecks
from tools.bakery_playtest import service_ready

def run(source):
 out=source/'form-refusal-validation';rom=(source/'torneko-2-english.gba').read_bytes();b=json.loads((source/'build.json').read_text());require(digest(rom)==b['output_sha256'],'Form refusal ROM differs');mgba.log.silence();fixture=service_ready(rom,out);row=b['form_refusal']['entries'][0];address=row['offset']+0x08000000;results=[]
 for code in (b'M.A',b'X.A',b'MXA',b'M.X'):
  for layout in (0,2):
   for button in (('A','B') if code==b'M.A' else ('none',)):
    shown=code==b'M.A';case=code.decode()+'-'+str(layout)+'-'+button;print('Form refusal:',case,flush=True)
    with Session(rom,out/case) as g:
     g.restore(fixture);m=g.core.memory;c=TextChecks(g,{address:row});initial=[];returns=[];modals=[];modal_returns=[];predicates=[];draws=[];images={};pixels=0;overrides=[];code_before=bytes(m[0x02010204:0x02010207]);inventory=bytes(m[0x0200DF28:0x0200E888]);hero=m.u32[0x02001624];gold=m.u32[hero+0x60]
     def reg(e,i,v,why):overrides.append(dict(event=e,register=i,after=v,reason=why));g.core.cpu.gprs[i]=v
     def write(at,raw):
      overrides.append(dict(address=at,before=bytes(m[at:at+len(raw)]).hex(),after=raw.hex()))
      for i,v in enumerate(raw):m.u8[at+i]=v
     def jump(e,at,why):overrides.append(dict(event=e,pc_after=at+0x08000000,reason=why));require(g.core._core.writeRegister(g.core._core,b'pc',ffi.new('uint32_t*',at+0x08000000)),'Form refusal redirect failed')
     def cb(e):
      a,r=e['address'],e['registers']
      if a==0x0801DFAC and not initial:initial.append(e|dict(guard=bytes(m[r[13]:r[13]+32]).hex()));jump(e,0x4B8AC,'Controlled bank invocation into complete original map-transition owner.');return
      if not initial or returns:return
      if a==0x0804B8B8:
       write(0x02010204,code);reg(e,9,layout,'Original native layout selector');jump(e,0x4B984,'Execute original three-byte form predicate; map movement setup excluded.')
      if a==0x0804B998:require(shown,'Nonmatching form selected refusal');predicates.append(e)
      if a==0x0804B9B4:require(not shown,'Matching form skipped refusal');predicates.append(e);jump(e,0x4BC2C,'Nonmatching form falls through natively; subsequent travel effects excluded.')
      if a==0x08015A34:require(r[0]==address and r[2]==0,'Form refusal modal source/options differ');modals.append(e)
      if a==0x0804BC68:
       old=modals[-1]['registers'];require(r[4:12]==old[4:12] and r[13]==old[13],'Form refusal modal ABI differs');modal_returns.append(e)
      if a==0x0804BC3C:
       old=initial[0]['registers'];require(r[4:12]==old[4:12] and r[13]==old[13] and r[1]==old[14] and r[0]==0 and bytes(m[r[13]:r[13]+32]).hex()==initial[0]['guard'],'Form refusal owner ABI/return/guard differs');write(0x02010204,code_before);returns.append(e)
      if a==0x080021B4 and r[1]==address:require(bytes(m[r[0]+4:r[0]+6])==bytes([28,2]),'Form refusal panel geometry differs')
      if a==0x08001BC4 and c.active:
       w=r[0];key=(w,r[1],r[13],r[14],m.u8[w+2],m.u8[w+3])
       if not draws or draws[-1]['key']!=key:draws.append(dict(key=key,code=r[1],x=m.u8[w+2],y=m.u8[w+3],origin=[m.u8[w],m.u8[w+1]],foreground=m.u8[0x020000C2],bank=m.u16[m.u32[w+12]]>>12))
      if a in c.ADDRESSES:c.callback(e)
     with Debugger(g,cb,max_events=100000) as d:
      for a in set(c.ADDRESSES)|{0x0801DFAC,0x0804B8B8,0x0804B998,0x0804B9B4,0x08015A34,0x0804BC68,0x0804BC3C}:d.breakpoint(a)
      g.press('A',hold=1,wait=0);captured=False
      for _ in range(1000):
       if returns:break
       if c.reads and not c.active and not captured:
        g.frames(8);pic=g.capture('refusal');images['refusal.png']=digest((g.output/'refusal.png').read_bytes());captured=True
        for v in draws:
         require(v['foreground']==12,'Guard refusal lost original colour4');glyph,_=c.glyph_record(v['code']);colour=m.u16[0x05000000+2*(16*v['bank']+12)];rgb=tuple(((colour>>s)&31)*255//31 for s in (0,5,10))
         for y,line in enumerate(glyph['rows']):
          for x,bit in enumerate(line):require((pic.getpixel((v['origin'][0]+v['x']+x,v['origin'][1]+16*v['y']+y))==rgb)==(bit=='#'),'Form refusal final pixels differ');pixels+=1
        g.press(button,hold=1,wait=0)
       else:g.frames(1)
      require(len(initial)==len(returns)==len(predicates)==1 and len(c.reads)==len(modals)==len(modal_returns)==int(shown) and captured==shown and not c.active,'Form refusal route incomplete')
     require(bytes(m[0x02010204:0x02010207])==code_before and bytes(m[0x0200DF28:0x0200E888])==inventory and m.u32[hero+0x60]==gold and g.snapshot().battery==fixture.battery,'Form refusal changed code/items/gold/save');results.append(dict(case=case,form_hex=code.hex(),layout=layout,button=button,shown=shown,inputs=g.inputs,overrides=overrides,predicates=predicates,modals=modals,modal_returns=modal_returns,returns=returns,reads=c.reads,caller_guard_abi_preserved=True,visible_pixels_checked=pixels,images=images))
 report=dict(passed=True,rom_sha256=digest(rom),cases=results,scope='Full original4B8AC frame, controlled dispatch to original three-byte form predicate at4B984, positive M.A and three individual-byte mismatch cases, both native layout selectors, native modal A/B dismissal, colour4/restoration and exact pixels. All returns execute original refusal/caller epilogues. Map movement setup, natural transformation and post-fallthrough travel effects excluded. Temporary form bytes restored; inventory/gold/battery unchanged.');(out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print('Form refusal:',len(results),'passed')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--source',type=Path,default=ROOT/'build/english');run(p.parse_args().source)
