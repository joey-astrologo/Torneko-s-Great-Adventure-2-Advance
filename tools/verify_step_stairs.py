import argparse,json,struct
from pathlib import Path
import mgba.log
from tools.rom import ROOT,digest,require
from tools.emulator import Session,Debugger,ffi
from tools.dialogue_checks import TextChecks

def run(source=ROOT/'build/english'):
 out=source/'step-stairs-validation';mgba.log.silence();rom=(source/'torneko-2-english.gba').read_bytes();build=json.loads((source/'build.json').read_text());require(digest(rom)==build['output_sha256'],'Stale step/stairs ROM')
 from tools import verify_player_status_prototype as status
 prior=status.OUT
 try:status.OUT=out;fixture=status.ready(rom,build)
 finally:status.OUT=prior
 results=[]
 for kind,entry,end,command in [('step',0x17854,0x1787A,20),('stairs',0x1787C,0x17A24,24)]:
  row=next(r for r in build['step_stairs']['entries'] if r['id']=='step-stairs.'+kind)
  for choice in ('cancel','stay','act'):
   case=kind+'-'+choice;print('Step/stairs:',case,flush=True)
   with Session(rom,out/case) as g:
    g.restore(fixture);m=g.core.memory;initial=[];returns=[];overrides=[];draws=[];images={};pixels=0;creations=[];c=TextChecks(g,{row['offset']+0x08000000:row});cycle=0
    inventory=bytes(m[0x0200DF28:0x0200E888]);hero=m.u32[0x02001624];gold=m.u32[hero+0x60]
    def write(at,data):
     overrides.append({'address':at,'before':bytes(m[at:at+len(data)]).hex(),'after':data.hex()})
     for i,v in enumerate(data):m.u8[at+i]=v
    def callback(e):
     a,r=e['address'],e['registers']
     if a==0x08023C14 and len(initial)==len(returns):
      initial.append(e|{'guard':bytes(m[r[13]:r[13]+32]).hex(),'command_before':bytes(m[r[0]:r[0]+8]).hex()})
      if kind=='stairs':write(0x02003B6C,struct.pack('<I',12))
      overrides.append({'event':e,'pc_after':entry+0x08000000,'reason':'Controlled ordinary A command redirect; original Step/Stairs owner runs with its native command pointer.'});require(g.core._core.writeRegister(g.core._core,b'pc',ffi.new('uint32_t*',entry+0x08000000)),'Step/stairs dispatch failed');return
     if len(initial)==len(returns):return
     if a==0x08001798:creations.append(e)
     if a==0x080021B4 and r[1]==row['offset']+0x08000000:
      require(bytes(m[r[0]:r[0]+2])==bytes((64,72) if kind=='step' else (64,56)) and bytes(m[r[0]+4:r[0]+6])==bytes((14,1) if kind=='step' else (12,2)),'Step/stairs geometry differs');draws.clear()
     if a==0x08001BC4 and c.active:
      w=r[0];key=(w,r[1],r[13],r[14],m.u8[w+2],m.u8[w+3])
      if not draws or draws[-1]['key']!=key:draws.append({'key':key,'window':w,'code':r[1],'x':m.u8[w+2],'y':m.u8[w+3],'origin':[m.u8[w],m.u8[w+1]],'foreground':m.u8[0x020000C2],'bank':m.u16[m.u32[w+12]]>>12})
     if a in c.ADDRESSES:c.callback(e)
     if a==end+0x08000000:
      old=initial[-1]['registers'];expected=int(cycle==2 and choice=='act');require(r[4:12]==old[4:12] and r[13]==old[13] and r[1]==old[14] and bytes(m[r[13]:r[13]+32]).hex()==initial[-1]['guard'],'Step/stairs caller ABI/guard differs')
      before=bytearray.fromhex(initial[-1]['command_before'])
      if expected:before[1]=command
      require(r[0]==expected and bytes(m[old[0]:old[0]+8])==before,'Step/stairs original command/result differs: '+repr((case,cycle,r[0],expected,bytes(m[old[0]:old[0]+8]).hex(),before.hex())))
      returns.append(e|{'native_selection_checked':True});g.core.cpu.gprs[0]=0;write(old[0],bytes.fromhex(initial[-1]['command_before']));overrides.append({'event':e,'r0_after':0,'reason':'Original selection/result verified; suppress subsequent map/trap execution in this controlled menu-only probe.'})
    def capture(tag):
     nonlocal pixels
     g.frames(3);pic=g.capture(tag);images[tag+'.png']=digest((g.output/(tag+'.png')).read_bytes());require(draws and not c.active,'Incomplete step/stairs render')
     if kind=='step':require(draws[0]['x']==6 and draws[4]['x']==52,'Native step columns differ')
     for d in draws:
      glyph,_=c.glyph_record(d['code']);colour=m.u16[0x05000000+2*(16*d['bank']+d['foreground'])];rgb=tuple(((colour>>s)&31)*255//31 for s in (0,5,10))
      for y,line in enumerate(glyph['rows']):
       for x,bit in enumerate(line):require((pic.getpixel((d['origin'][0]+d['x']+x,d['origin'][1]+16*d['y']+y))==rgb)==(bit=='#'),'Step/stairs final pixels differ');pixels+=1
    with Debugger(g,callback,max_events=100000) as debug:
     for a in set(c.ADDRESSES)|{0x08023C14,0x08001798,end+0x08000000}:debug.breakpoint(a)
     for cycle in range(3):
      g.press('A',hold=1,wait=60);capture('opened-'+str(cycle));next_key='RIGHT' if kind=='step' else 'DOWN';back='LEFT' if kind=='step' else 'UP';g.press(next_key,wait=15);capture('second-'+str(cycle));g.press(back,wait=15)
      if cycle<2 or choice=='cancel':g.press('B',hold=1,wait=45)
      elif choice=='stay':g.press(next_key,wait=15);g.press('A',hold=1,wait=45)
      else:g.press('A',hold=1,wait=45)
      require(len(returns)==cycle+1,'Step/stairs failed to return')
    require(len(initial)==len(returns)==len(c.reads)==3 and not c.active,'Step/stairs incomplete')
    require(bytes(m[0x0200DF28:0x0200E888])==inventory and m.u32[hero+0x60]==gold and g.snapshot().battery==fixture.battery,'Step/stairs menu changed inventory/gold/battery')
    results.append({'case':case,'kind':kind,'choice':choice,'inputs':g.inputs,'overrides':overrides,'reads':c.reads,'returns':returns,'creations':creations,'caller_guard_abi_preserved':True,'visible_pixels_checked':pixels,'images':images})
 report={'passed':True,'rom_sha256':digest(rom),'cases':results,'scope':'Ordinary A is explicitly redirected to full17854 Step or1787C Stairs owner with the original command pointer. Stairs mode12 selects the native two-choice variant. Each case checks two B cancellations/reopenings, both cursor positions, final B/Stay/Step-or-Descend selection, original command byte/result, exact visible pixels, geometry, caller ABI and unchanged inventory/gold/battery. Return result/command are restored after verification to exclude subsequent trap/floor execution. Ordinary prompt conditions and map outcomes remain separate.'}
 (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print('Step/stairs:',len(results),'passed')
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,default=ROOT/'build/english');run(p.parse_args().source)
