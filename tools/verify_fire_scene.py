"""Full fixed-stride fire-scene dispatcher, native indexed reads and consecutive blocks."""
import argparse,json,struct
from pathlib import Path
import mgba.log
from tools.rom import ROOT,digest,require
from tools.emulator import Session,Debugger,ffi
from tools.bakery_playtest import service_ready
from tools.dialogue_checks import TextChecks,player_layout_cases
from tools.name_entry import HERO
GROUPS=[(2,2),(6,3),(15,3),(21,4),(25,4),(30,2),(33,2),(36,2),(38,2)]

def run(source,only=None):
 out=source/'fire-scene-validation';rom=(source/'torneko-2-english.gba').read_bytes();b=json.loads((source/'build.json').read_text());require(digest(rom)==b['output_sha256'],'Fire scene ROM differs');mgba.log.silence();fixture=service_ready(rom,out);rows={e['index']:e for e in b['fire_scene']['entries']};resources={e['offset']+0x08000000:e for e in rows.values()};results=[]
 cases=[]
 for i,e in rows.items():
  for profile,player in (player_layout_cases() if '{player}' in e['english'] else [('ordinary',None)]):cases.append((f'{i}-{profile}',i,1,player))
 cases += [(f'sequence-{i}-{n}',i,n,None) for i,n in GROUPS]+[('zero-count',0,0,None)]
 for case,index,count,player in cases:
  if only is not None and not case.startswith(only):continue
  print('Fire scene:',case,flush=True)
  with Session(rom,out/case) as g:
   g.restore(fixture);m=g.core.memory;c=TextChecks(g,dict(resources));initial=[];returns=[];overrides=[];modals=[];modal_returns=[];draws=[];images={};pixels=0
   inventory=bytes(m[0x0200DF28:0x0200E888]);hero=m.u32[0x02001624];gold=m.u32[hero+0x60]
   if player:
    overrides.append(dict(address=HERO,before=bytes(m[HERO:HERO+16]).hex(),after=player.ljust(16,b'\0').hex(),reason='Maximum compatible player-name glyph profile.'))
    for i,v in enumerate(player.ljust(16,b'\0')):m.u8[HERO+i]=v
   def cb(e):
    a,r=e['address'],e['registers']
    if a==0x0801DFAC and not initial:
     initial.append(e|dict(guard=bytes(m[r[13]:r[13]+32]).hex()));overrides.append(dict(event=e,pc_after=0x08052DD8,r0_r1_after=[index,count],reason='Controlled bank entry into complete original scene text dispatcher; native literal/stride loads, modal and loop execute.'))
     g.core.cpu.gprs[0]=index;g.core.cpu.gprs[1]=count;require(g.core._core.writeRegister(g.core._core,b'pc',ffi.new('uint32_t*',0x08052DD8)),'Fire scene redirect failed');return
    if not initial or returns:return
    if a==0x08015A34:
     expected=rows[index+len(modals)];require(r[0]==expected['offset']+0x08000000 and r[2]==0 and bytes(m[r[3]:r[3]+16])==rom[0x6CF28:0x6CF38] and m.u32[r[13]]==m.u32[r[13]+4]==0,'Fire scene source/descriptor differs');modals.append(e|dict(id=expected['id']))
    if a==0x08052E18:
     old=modals[-1]['registers'];require(r[4:12]==old[4:12] and r[13]==old[13],'Fire scene modal ABI differs');modal_returns.append(e)
    if a==0x08052E26:
     old=initial[0]['registers'];require(r[4:12]==old[4:12] and r[13]==old[13] and r[0]==old[14] and bytes(m[r[13]:r[13]+32]).hex()==initial[0]['guard'],'Fire scene owner caller ABI/guard differs');returns.append(e)
    if a in (0x08001750,0x08001888):draws[:]=[d for d in draws if d['window']!=r[0]]
    if a==0x080021B4 and r[1] in c.resources:require(bytes(m[r[0]+4:r[0]+6])==bytes((28,2)),'Fire scene original window differs: '+bytes(m[r[0]:r[0]+24]).hex())
    if a==0x08001BC4 and c.active:
     w=r[0];key=(w,r[1],r[13],r[14],m.u8[w+2],m.u8[w+3])
     if not draws or draws[-1]['key']!=key:draws.append(dict(key=key,window=w,code=r[1],x=m.u8[w+2],y=m.u8[w+3],origin=[m.u8[w],m.u8[w+1]],foreground=m.u8[0x020000C2],bank=m.u16[m.u32[w+12]]>>12))
    if a in c.ADDRESSES:c.callback(e)
   def capture(tag):
    nonlocal pixels
    g.frames(8);pic=g.capture(tag);images[tag+'.png']=digest((g.output/(tag+'.png')).read_bytes());require(draws,'Fire scene missing visible text')
    for d in draws:
     glyph,_=c.glyph_record(d['code']);colour=m.u16[0x05000000+2*(16*d['bank']+d['foreground'])];rgb=tuple(((colour>>s)&31)*255//31 for s in (0,5,10))
     for y,line in enumerate(glyph['rows']):
      for x,bit in enumerate(line):require((pic.getpixel((d['origin'][0]+d['x']+x,d['origin'][1]+16*d['y']+y))==rgb)==(bit=='#'),'Fire scene final pixels differ');pixels+=1
   with Debugger(g,cb,max_events=250000) as d:
    for a in set(c.ADDRESSES)|{0x0801DFAC,0x08015A34,0x08052E18,0x08052E26,0x08001750,0x08001888}:d.breakpoint(a)
    g.press('A',hold=1,wait=0);handled=set()
    for tick in range(5000):
     if returns:break
     state=(len(c.reads),c.active['page_waits'] if c.active else -1)
     if ((c.active and c.active['page_waits']) or (c.reads and not c.active and len(modals)>len(modal_returns))) and state not in handled:
      capture(f'page-{len(handled)}');handled.add(state);g.press('A',hold=1,wait=0)
     else:g.frames(1)
    require(len(initial)==len(returns)==1 and len(c.reads)==len(modals)==len(modal_returns)==count and not c.active and [e['id'] for e in c.reads]==['fire-scene.'+str(i) for i in range(index,index+count)],'Fire scene dispatcher incomplete')
    require(len(handled)==sum(len(rows[i]['layout']['pages']) for i in range(index,index+count)),'Fire scene page coverage incomplete')
   require(bytes(m[0x0200DF28:0x0200E888])==inventory and m.u32[hero+0x60]==gold and g.snapshot().battery==fixture.battery,'Fire scene changed inventory/gold/battery')
   results.append(dict(case=case,index=index,count=count,inputs=g.inputs,overrides=overrides,reads=c.reads,modals=modals,modal_returns=modal_returns,returns=returns,caller_guard_abi_preserved=True,visible_pixels_checked=pixels,images=images));(out/'partial.json').write_text(json.dumps(results,indent=2)+'\n')
 report=dict(passed=True,rom_sha256=digest(rom),cases=results,scope='Controlled bank entry with index/count into complete original52DD8..52E28 dispatcher. Native private-base/512-byte stride loads, original descriptor and216px two-row budget, all40 records, three compatible name profiles, nine native consecutive groups and zero-count branch, all page waits/final pixels, modal/owner ABI and caller guard. Original actor staging, scene trigger, timing between calls, fire animations, story progression and natural playback excluded; inventory/gold/battery unchanged. Record29 has a controlled read only; no original scene call asserted.')
 (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print('Fire scene:',len(results),'passed')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--source',type=Path,default=ROOT/'build/english');p.add_argument('--only');a=p.parse_args();run(a.source,a.only)
