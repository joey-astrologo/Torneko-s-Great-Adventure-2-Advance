"""All original availability masks for the older town and dungeon travel lists."""
import argparse,json,struct
from pathlib import Path
import mgba.log
from tools.rom import ROOT,digest,require,load_base
from tools.emulator import Session,Debugger,Snapshot,ffi
from tools.dialogue_checks import TextChecks,player_layout_cases
from tools.town_playtest import position
from tools.name_entry import HERO

def run(source,only=None):
 out=source/'town-routes-validation';rom=(source/'torneko-2-english.gba').read_bytes();b=json.loads((source/'build.json').read_text());require(digest(rom)==b['output_sha256'],'Town routes ROM differs');mgba.log.silence();fixture=Snapshot.load(source/'castle-validation/audience-complete');original=load_base();resources={e['offset']+0x08000000:e for e in b['town_routes']['entries']};indices={i:e for e in b['town_routes']['entries'] for i in e['table_indices']}
 for i in b['town_routes']['inherited']:
  e=next(e for e in b['dialogue']['entries'] if e['id']==i['id']);indices[i['index']]=e;resources[e['rom_offset']+0x08000000]=e
 heading=next(e for e in b['dialogue']['entries'] if e['id']=='rom.0006c524');resources[heading['rom_offset']+0x08000000]=heading
 def mask(kind,state,count):return original[0x14BE33+min(state,7)*6+count] if kind=='town' else original[0x14BE8A+count]
 def positions(kind,bits):return [i for i in range(8 if kind=='town' else 4) if bits&((128 if kind=='town' else 8)>>i)]
 cases=[(f'town-{s}-{n}','town',s,n,None,None,None) for s in range(8) for n in range(6)]+[(f'dungeon-{n}','dungeon',0,n,None,None,None) for n in range(4)]
 for kind,num in [('town',7),('dungeon',3)]:
  for target in range(num):
   state,count=next((s,n) for s in range(8 if kind=='town' else 1) for n in range(6 if kind=='town' else 4) if target in positions(kind,mask(kind,s,n)));cases.append((f'{kind}-select-{target}',kind,state,count,target,None,None))
 cases += [('town-retained-cancel','town',0,0,7,None,1),('dungeon-retained-cancel','dungeon',0,0,3,None,1),('town-clamped-state','town',255,5,None,None,None)]
 cases += [('town-home-'+profile,'town',0,0,None,player,None) for profile,player in player_layout_cases() if profile!='required-English']
 results=[]
 for case,kind,state,count,target,player,forced in cases:
  if only and case!=only:continue
  bits=mask(kind,state,count) if forced is None else forced;labels=positions(kind,bits);offset=1 if kind=='town' else 9;heading_id=heading['id'] if kind=='town' else indices[0]['id'];entry,end,flagret,maskready=(0x4CB10,0x4CC4E,0x4CB5A,0x4CBB4) if kind=='town' else (0x4CC70,0x4CD9A,0x4CCBA,0x4CD00);result_table=0x14BE74 if kind=='town' else 0x14BE8E;print('Town routes:',case,flush=True)
  with Session(rom,out/case) as g:
   g.restore(fixture);m=g.core.memory;c=TextChecks(g,resources);initial=[];returns=[];overrides=[];draws=[];creates=[];closes=[];images={};pixels=0;cycle=0;selectors=[];inventory=bytes(m[0x0200DF28:0x0200E888]);hero=m.u32[0x02001624];gold=m.u32[hero+0x60];original_state=m.u8[0x0200FED8]
   def write(at,data):
    overrides.append(dict(address=at,before=bytes(m[at:at+len(data)]).hex(),after=data.hex()))
    for i,v in enumerate(data):m.u8[at+i]=v
   def reg(e,i,v,reason):overrides.append(dict(event=e,register=i,after=v,reason=reason));g.core.cpu.gprs[i]=v
   if player:write(HERO,player.ljust(16,b'\0'))
   def cb(e):
    a,r=e['address'],e['registers']
    if a==0x0804CB10 and len(initial)==len(returns):
     initial.append(e|dict(guard=bytes(m[r[13]:r[13]+32]).hex()));draws.clear();write(0x0200FED8,bytes([state]))
     if kind=='dungeon':
      overrides.append(dict(event=e,pc_after=entry+0x08000000,reason='Controlled town travel invocation into complete original dungeon-list owner.'))
      require(g.core._core.writeRegister(g.core._core,b'pc',ffi.new('uint32_t*',entry+0x08000000)),'Town routes dispatch failed')
     return
    if len(initial)==len(returns):return
    if a==flagret+0x08000000:reg(e,0,int(r[5]<count),'Controlled original flag-reader result; actual count/mask table lookup remains native.')
    if a==maskready+0x08000000:
     require(r[9]==mask(kind,state,count),'Town route native mask lookup differs')
     if forced is not None:reg(e,9,forced,'Retained Cancel label not emitted by the original masks; explicit display/selection probe only.')
     selectors.append(e|dict(mask_after=bits))
    if a==0x08001798:creates.append(e)
    if a in (0x08001750,0x08001888):
     if a==0x08001888:closes.append(e)
     draws[:]=[d for d in draws if d['window']!=r[0]]
    if a==0x080021B4 and r[1] in resources:
     w=r[0];isheading=resources[r[1]]['id']==heading_id;origin=(8,24) if isheading else ((80,24) if kind=='town' else (128,24));shape=((7 if kind=='town' else 13),1) if isheading else ((19,6) if kind=='town' else (11,3));require(bytes(m[w:w+2])==bytes(origin) and bytes(m[w+4:w+6])==bytes(shape),'Town route existing geometry differs')
    if a==0x08001BC4 and c.active:
     w=r[0];key=(w,r[1],r[13],r[14],m.u8[w+2],m.u8[w+3])
     if not draws or draws[-1]['key']!=key:draws.append(dict(key=key,window=w,code=r[1],x=m.u8[w+2],y=m.u8[w+3],origin=[m.u8[w],m.u8[w+1]],foreground=m.u8[0x020000C2],bank=m.u16[m.u32[w+12]]>>12,id=c.active['id']))
    if a in c.ADDRESSES:c.callback(e)
    if a==end+0x08000000:
     old=initial[-1]['registers'];require(r[4:12]==old[4:12] and r[13]==old[13] and r[1]==old[14] and bytes(m[r[13]:r[13]+32]).hex()==initial[-1]['guard'],'Town route caller ABI/guard differs');expected=255 if cycle<2 or target is None else struct.unpack_from('<H',original,result_table+2*target)[0];require(r[0]==expected,'Town route native result differs');returns.append(e|dict(native_result_checked=True));write(0x0200FED8,bytes([original_state]))
     if expected!=255:reg(e,0,255,'Actual selected native result checked above; suppress travel outside the menu owner for this controlled selector probe.')
   def capture(tag):
    nonlocal pixels
    g.frames(8);pic=g.capture(tag);images[tag+'.png']=digest((g.output/(tag+'.png')).read_bytes());require(draws and not c.active,'Town route render incomplete: '+repr((len(initial),len(returns),len(creates),len(closes),[e['id'] for e in c.reads],c.active,selectors)))
    for d in draws:
     glyph,_=c.glyph_record(d['code']);colour=m.u16[0x05000000+2*(16*d['bank']+d['foreground'])];rgb=tuple(((colour>>s)&31)*255//31 for s in (0,5,10))
     if d['id']!=heading_id:require(d['x']>=12 and d['x']+glyph['advance']<=(152 if kind=='town' else 88),'Town route cursor/edge collision')
     for y,line in enumerate(glyph['rows']):
      for x,bit in enumerate(line):require((pic.getpixel((d['origin'][0]+d['x']+x,d['origin'][1]+16*d['y']+y))==rgb)==(bit=='#'),'Town route final pixels differ');pixels+=1
   with Debugger(g,cb,max_events=200000) as d:
    for a in set(c.ADDRESSES)|{0x0804CB10,end+0x08000000,flagret+0x08000000,maskready+0x08000000,0x08001798,0x08001750,0x08001888}:d.breakpoint(a)
    for cycle in range(3):
     start=len(c.reads)
     for _ in range(100):
      g.press('DOWN',hold=3,wait=4)
      if len(initial)>len(returns):break
     else:raise ValueError('Ordinary castle exit did not enter the travel menu')
     g.frames(120);require(m.u8[0x020101A1]==0,'Town route initial selection differs');capture('opened-'+str(cycle));require([r['id'] for r in c.reads[start:]]==[heading_id]+[indices[offset+i]['id'] for i in labels],'Town route original selected rows differ')
     if labels:
      g.press('UP',wait=20);require(m.u8[0x020101A1]==len(labels)-1,'Town route up-wrap differs');capture('last-'+str(cycle));g.press('DOWN',wait=20);require(m.u8[0x020101A1]==0,'Town route down-wrap differs')
     if cycle<2 or target is None:g.press('B',hold=1,wait=120)
     else:
      for _ in range(labels.index(target)):g.press('DOWN',wait=20)
      capture('selected');g.press('A',hold=1,wait=120)
     require(len(returns)==cycle+1 and len(closes)==2*(cycle+1),'Town route return/window closure differs')
     before=position(g);g.press('UP',hold=16,wait=60);require(position(g)[1]<before[1],'Town route cancellation did not resume ordinary town movement');g.capture('closed-'+str(cycle));images['closed-'+str(cycle)+'.png']=digest((g.output/('closed-'+str(cycle)+'.png')).read_bytes())
   require(bytes(m[0x0200DF28:0x0200E888])==inventory and m.u32[hero+0x60]==gold and g.snapshot().battery==fixture.battery,'Town routes changed items/gold/save');results.append(dict(case=case,kind=kind,state=state,flag_count=count,mask=bits,labels=labels,target=target,retained_cancel_probe=forced is not None,inputs=g.inputs,overrides=overrides,reads=c.reads,selectors=selectors,returns=returns,creates=creates,closures=closes,caller_guard_abi_preserved=True,visible_pixels_checked=pixels,images=images));(out/'partial.json').write_text(json.dumps(results,indent=2)+'\n')
 report=dict(passed=True,rom_sha256=digest(rom),cases=results,scope='Complete original4CB10 town and4CC70 dungeon menu owners from ordinary castle-exit entry with controlled availability (and dungeon owner dispatch), original48/4 availability-table cells and clamped-state branch, recorded flag-reader results, all native rows and ten selections, two explicit retained-Cancel mask probes, two maximum player-name profiles, original geometry/8px outer-border gaps, cursor wrapping, B cancellation, twice reopening, exact pixels and caller ABI/guard. Positive native selection IDs are checked before suppressing actual travel; natural unlocking remains separate; inventory/gold/battery unchanged.');(out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print('Town routes:',len(results),'passed')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--source',type=Path,default=ROOT/'build/english');p.add_argument('--only');a=p.parse_args();run(a.source,a.only)
