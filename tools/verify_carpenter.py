"""Full native warehouse repair owner: prose, choices, charges and capacity changes."""
import argparse,json,struct
from pathlib import Path
import mgba.log
from tools.rom import ROOT,digest,require
from tools.emulator import Session,Debugger,ffi
from tools.dialogue_checks import TextChecks
from tools.bakery_playtest import service_ready
from tools.verify_result_ui import native_format

def run(source,only=None):
 out=source/'carpenter-validation';rom=(source/'torneko-2-english.gba').read_bytes();b=json.loads((source/'build.json').read_text());require(digest(rom)==b['output_sha256'],'Carpenter ROM differs');mgba.log.silence();fixture=service_ready(rom,out);rows={e['id'].split('.')[-1]:e for e in b['carpenter']['entries']};resources={e['offset']+0x08000000:e for e in rows.values() if e['id']!='carpenter.capacity'};results=[]
 cases=[('working',0x20,20,1000,'dismiss',['working']),('finished',0x80,250,1000,'dismiss',['finished']),('complete',0x40,170,1000,'dismiss',['complete']),('capacity30',0x40,20,1000,'dismiss',['capacity','more']),('capacity170',0x40,160,1000,'dismiss',['capacity','more']),('capacity255-boundary',0x40,245,1000,'dismiss',['capacity','more']),('pay-exact',0,20,1000,'yes',['offer','accepted']),('pay-surplus',0,20,1001,'yes',['offer','accepted']),('pay-maximum',0,20,99999999,'yes',['offer','accepted']),('pay-signed-boundary',0,20,2147483647,'yes',['offer','accepted']),('no',0,20,1000,'no',['offer','declined']),('cancel',0,20,1000,'cancel',['offer','declined']),('empty',0,20,0,'yes',['offer','insufficient']),('short',0,20,999,'yes',['offer','insufficient'])]
 for name,flags,capacity,gold,choice,sequence in cases:
  if only is not None and name!=only:continue
  for layout in (0,2):
   case=f'{name}-layout{layout}';print('Carpenter:',case,flush=True)
   with Session(rom,out/case) as g:
    g.restore(fixture);m=g.core.memory;c=TextChecks(g,dict(resources));initial=[];returns=[];overrides=[];modals=[];modal_returns=[];helpers=[];helper_returns=[];pending={};formats=[];draws=[];images={};pixels=0;selector_returns=[];hero=m.u32[0x02001624];inventory=bytes(m[0x0200DF28:0x0200E888]);storage=bytes(m[0x0200F008:0x0200FBC0]);flag_address=0x020101B0
    def write(a,raw,reason):
     overrides.append(dict(address=a,before=bytes(m[a:a+len(raw)]).hex(),after=raw.hex(),reason=reason))
     for i,v in enumerate(raw):m.u8[a+i]=v
    def jump(e,a,reason):overrides.append(dict(event=e,pc_after=a+0x08000000,reason=reason));require(g.core._core.writeRegister(g.core._core,b'pc',ffi.new('uint32_t*',a+0x08000000)),'Carpenter redirect failed')
    def callback(e):
     a,r=e['address'],e['registers']
     if a==0x0801DFAC and not initial:
      initial.append(e|dict(guard=bytes(m[r[13]:r[13]+32]).hex()));write(flag_address,bytes([(m.u8[flag_address]&0x1F)|flags]),'Controlled native construction/completion flags37,38,39.');write(0x02010208,bytes([capacity]),'Controlled current warehouse capacity byte.');write(0x02002C2A,struct.pack('<H',capacity),'Matching native storage capacity halfword.');write(hero+0x60,struct.pack('<I',gold),'Controlled player funds; actual debit remains native.');jump(e,0x502BC,'Full original carpenter function; only entry routing is controlled.');return
     if not initial or returns:return
     if a==0x08051278:
      selector_returns.append(e);overrides.append(dict(event=e,register=3,after=layout,reason='Controlled original display-layout selector result; original table lookup and modal geometry execute.'));g.core.cpu.gprs[3]=layout
     if a==0x080503F8:helpers.append(e)
     if a==0x08050436:
      old=helpers[len(helper_returns)]['registers'];require(r[4:12]==old[4:12] and r[13]==old[13] and r[0]==old[14],'Carpenter text helper ABI differs');helper_returns.append(e)
     if a==0x08000FB8 and r[1]==rows['capacity']['offset']+0x08000000:
      require(r[0]==0x0202F44C and r[2]==(capacity+10)&255 and r[14]==0x08050345,'Carpenter count formatter arguments differ');raw=native_format(bytes.fromhex(rows['capacity']['encoded_hex']),[r[2]],m);require(len(raw)<=rows['capacity']['layout']['maximum_formatted_bytes']<=128,'Carpenter formatter exceeds scratch');pending.update(regs=r,raw=raw,guard=bytes(m[r[0]+128:r[0]+160]))
     if pending and a==0x08050344:
      old=pending['regs'];raw=pending['raw'];require(bytes(m[old[0]:old[0]+len(raw)])==raw and bytes(m[old[0]+128:old[0]+160])==pending['guard'] and r[4:12]==old[4:12] and r[13]==old[13],'Carpenter count bytes/guard/ABI differ');c.resources[old[0]]=rows['capacity']|dict(encoded_hex=raw.hex());formats.append(dict(raw_hex=raw.hex(),bytes=len(raw),capacity=128,value=old[2],guard_abi_preserved=True));pending.clear()
     if a==0x08015A34:
      require(r[0] in c.resources,'Carpenter selected unowned text');row=c.resources[r[0]];require(row['id']=='carpenter.'+sequence[len(modals)] and r[2]==int(row['id']=='carpenter.offer'),'Carpenter branch/message sequence differs');modals.append(e|dict(id=row['id']))
     if a in (0x08001750,0x08001888):draws[:]=[d for d in draws if d['window']!=r[0]]
     if a==0x080021B4 and r[1] in c.resources:require(bytes(m[r[0]+4:r[0]+6])==bytes((28,2)),'Carpenter original window differs')
     if a==0x08001BC4 and c.active:
      w=r[0];key=(w,r[1],r[13],r[14],m.u8[w+2],m.u8[w+3])
      if not draws or draws[-1]['key']!=key:draws.append(dict(key=key,window=w,code=r[1],x=m.u8[w+2],y=m.u8[w+3],origin=[m.u8[w],m.u8[w+1]],foreground=m.u8[0x020000C2],bank=m.u16[m.u32[w+12]]>>12))
     if a in c.ADDRESSES:c.callback(e)
     if a in (0x08050430,0x08050396):
      old=modals[len(modal_returns)]['registers'];require(r[4:12]==old[4:12] and r[13]==old[13],'Carpenter modal ABI differs');require(a!=0x08050396 or r[0]==int(choice=='yes'),'Carpenter choice result differs');modal_returns.append(e)
     if a==0x080503F0:
      old=initial[0]['registers'];require(r[4:12]==old[4:12] and r[13]==old[13] and r[0]==old[14] and bytes(m[r[13]:r[13]+32]).hex()==initial[0]['guard'],'Carpenter owner caller guard/ABI differs');returns.append(e)
    def capture(tag):
     nonlocal pixels
     g.frames(8);pic=g.capture(tag);images[tag+'.png']=digest((g.output/(tag+'.png')).read_bytes());require(draws,'Carpenter missing visible text')
     for d in draws:
      glyph,_=c.glyph_record(d['code']);colour=m.u16[0x05000000+2*(16*d['bank']+d['foreground'])];rgb=tuple(((colour>>s)&31)*255//31 for s in (0,5,10))
      for y,line in enumerate(glyph['rows']):
       for x,bit in enumerate(line):require((pic.getpixel((d['origin'][0]+d['x']+x,d['origin'][1]+16*d['y']+y))==rgb)==(bit=='#'),'Carpenter final pixels differ');pixels+=1
    with Debugger(g,callback,max_events=300000) as debug:
     for a in set(c.ADDRESSES)|{0x0801DFAC,0x08051278,0x080503F8,0x08050436,0x08000FB8,0x08050344,0x08015A34,0x08001750,0x08001888,0x08050430,0x08050396,0x080503F0}:debug.breakpoint(a)
     g.press('A',hold=1,wait=0);handled=set()
     for tick in range(6000):
      if returns:break
      state=(len(c.reads),c.active['page_waits'] if c.active else -1)
      ready=(c.active and c.active['page_waits']) or (c.reads and not c.active and len(modals)>len(modal_returns))
      if ready and state not in handled:
       capture(f'page-{len(handled)}');handled.add(state)
       choosing=not c.active and modals[-1]['id']=='carpenter.offer'
       if choosing and choice=='no':g.press('RIGHT',wait=20);capture('no-selected')
       g.press('B' if choosing and choice=='cancel' else 'A',hold=1,wait=0)
      else:g.frames(1)
     require(len(initial)==len(returns)==1 and len(c.reads)==len(modals)==len(modal_returns)==len(sequence) and [e['id'] for e in c.reads]==['carpenter.'+k for k in sequence] and len(helpers)==len(helper_returns)==sum(k!='offer' for k in sequence) and len(formats)==int('capacity' in sequence) and not pending and not c.active,'Carpenter branch incomplete')
     require(len(handled)==sum(len(rows[k]['layout']['pages']) for k in sequence),'Carpenter page capture coverage incomplete')
    new_capacity=250 if name=='complete' else (capacity+10)&255 if 'capacity' in sequence else capacity;new_flags=0xC0 if name=='complete' else 0 if 'capacity' in sequence else 0x20 if 'accepted' in sequence else flags;new_gold=min(gold-1000,struct.unpack_from('<I',rom,0x41F9C)[0]) if 'accepted' in sequence else gold
    require(m.u8[0x02010208]==m.u16[0x02002C2A]==new_capacity and m.u8[flag_address]&0xE0==new_flags and m.u32[hero+0x60]==new_gold,f'Carpenter native payment/capacity/flags differ: {m.u8[0x02010208]}/{m.u16[0x02002C2A]}/{hex(m.u8[flag_address])}/{m.u32[hero+0x60]}, expected{new_capacity}/{new_flags}/{new_gold}');require(bytes(m[0x0200DF28:0x0200E888])==inventory and bytes(m[0x0200F008:0x0200FBC0])==storage and g.snapshot().battery==fixture.battery,'Carpenter changed inventory/storage contents/battery')
    results.append(dict(case=case,layout=layout,sequence=sequence,inputs=g.inputs,overrides=overrides,reads=c.reads,formats=formats,modals=modals,modal_returns=modal_returns,returns=returns,helpers=helpers,helper_returns=helper_returns,caller_guard_abi_preserved=True,visible_pixels_checked=pixels,images=images,capacity_before=capacity,capacity_after=new_capacity,flags_before=flags,flags_after=new_flags,gold_before=gold,gold_after=new_gold));(out/'partial.json').write_text(json.dumps(results,indent=2)+'\n')
 report=dict(passed=True,rom_sha256=digest(rom),cases=results,scope='Controlled bank entry into complete original502BC function; native state flags, capacity and gold are explicit inputs, with both original modal layout-selector results. Original branch selection, full prose/page waits, Yes/No/B,1000-gold debit, construction/completion flags and capacity changes execute unmodified.128-byte formatter bound/guard, helper/modal/owner ABI and exact visible pixels pass; inventory, stored item contents and battery unchanged.255 capacity and signed-maximum starting funds are boundary probes, not naturally available states; the native gold cap is preserved. Natural carpenter access, construction completion trigger and save persistence are separate.')
 (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print('Carpenter:',len(results),'passed')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--source',type=Path,default=ROOT/'build/english');p.add_argument('--only');a=p.parse_args();run(a.source,a.only)
