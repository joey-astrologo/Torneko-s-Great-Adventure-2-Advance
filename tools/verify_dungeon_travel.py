"""Native dungeon destination picker: unlock rows, selection, cancel/reopen."""
import argparse,json,struct
from pathlib import Path
import mgba.log
from tools.rom import ROOT,digest,require,load_base
from tools.emulator import Session,Debugger,ffi
from tools.dialogue_checks import TextChecks
from tools.bakery_playtest import service_ready

def run(source,only=None):
 out=source/'dungeon-travel-validation';rom=(source/'torneko-2-english.gba').read_bytes();b=json.loads((source/'build.json').read_text());require(digest(rom)==b['output_sha256'],'Stale dungeon-travel ROM');mgba.log.silence();fixture=service_ready(rom,out);rows={r['offset']+0x08000000:r for r in b['dungeon_travel']['entries']};results=[];original=load_base()
 cases=[(f'state-{s}-unlocked',s,True,False,None,False) for s in range(8)]+[(f'state-{s}-locked',s,False,False,None,False) for s in range(2,7)]+[('state-6-more',6,True,True,None,False)]+[(f'select-{s}-{t}',s,True,False,t,False) for s in (5,7) for t in range(5)]+[('stored-meadow',0,True,False,None,True)]
 for case,state,unlocked,more,target,meadow in cases:
  if only and case!=only:continue
  print('Dungeon travel:',case,flush=True);group=state if unlocked or state==0 else state-1
  if group==6 and more:group=7
  ids=[x for x in original[0x14D3E3+8*group:0x14D3E3+8*group+7] if x];labels=[3 if x==3 else 2 if x==4 else x-1 for x in ids]
  if meadow:labels[0]=1
  with Session(rom,out/case) as g:
   g.restore(fixture);m=g.core.memory;c=TextChecks(g,rows);initial=[];returns=[];overrides=[];draws=[];creates=[];closes=[];images={};pixels=0;cycle=0;selectors=[]
   def write(at,data):
    overrides.append({'address':at,'before':bytes(m[at:at+len(data)]).hex(),'after':data.hex()})
    for i,v in enumerate(data):m.u8[at+i]=v
   def reg(e,i,v):overrides.append({'event':e,'register':i,'after':v});g.core.cpu.gprs[i]=v
   inventory=bytes(m[0x0200DF28:0x0200E888]);hero=m.u32[0x02001624];gold=m.u32[hero+0x60]
   def callback(e):
    a,r=e['address'],e['registers']
    if a==0x0801DFAC and len(initial)==len(returns):
     initial.append(e|{'guard':bytes(m[r[13]:r[13]+32]).hex()});draws.clear();write(0x020101F0,bytes([state]));write(0x020101A0,b'\0')
     overrides.append({'event':e,'pc_after':0x08052304,'reason':'Controlled bank invocation enters complete original dungeon picker; progression/unlocking excluded.'});require(g.core._core.writeRegister(g.core._core,b'pc',ffi.new('uint32_t*',0x08052304)),'Dungeon picker redirect failed');return
    if len(initial)==len(returns):return
    if a==0x08052354:reg(e,0,int(unlocked))
    if a==0x0805236E:reg(e,0,int(not more))
    if a==0x08052378:reg(e,0,int(more))
    if a==0x080523DE:
     if meadow and r[4]==0:reg(e,5,1)
     selectors.append(e|{'selected_after':1 if meadow and r[4]==0 else r[5]})
    if a==0x08001798:creates.append(e)
    if a in (0x08001750,0x08001888):
     if a==0x08001888:closes.append(e)
     draws[:]=[d for d in draws if d['window']!=r[0]]
    if a==0x080021B4 and r[1] in rows:
     w=r[0];row=rows[r[1]];require(bytes(m[w:w+2])==bytes((40,24) if row['index']==7 else (48,56)) and bytes(m[w+4:w+6])==bytes((20,1) if row['index']==7 else (18,5)),'Dungeon picker original geometry differs')
    if a==0x08001BC4 and c.active:
     w=r[0];key=(w,r[1],r[13],r[14],m.u8[w+2],m.u8[w+3])
     if not draws or draws[-1]['key']!=key:draws.append({'key':key,'window':w,'code':r[1],'x':m.u8[w+2],'y':m.u8[w+3],'origin':[m.u8[w],m.u8[w+1]],'foreground':m.u8[0x020000C2],'bank':m.u16[m.u32[w+12]]>>12,'id':c.active['id']})
    if a in c.ADDRESSES:c.callback(e)
    if a==0x080524EE:
     old=initial[-1]['registers'];require(r[4:12]==old[4:12] and r[13]==old[13] and r[1]==old[14] and bytes(m[r[13]:r[13]+32]).hex()==initial[-1]['guard'],'Dungeon picker caller ABI/guard differs');expected=255 if cycle<2 or target is None else 2 if target==1 else 1 if target==2 else target;require(r[0]==expected,'Dungeon picker native selection differs');returns.append(e|{'native_result_checked':True})
   def capture(tag):
    nonlocal pixels
    g.frames(8);pic=g.capture(tag);images[tag+'.png']=digest((g.output/(tag+'.png')).read_bytes());require(draws and not c.active,'Dungeon picker incomplete render')
    for d in draws:
     glyph,_=c.glyph_record(d['code']);colour=m.u16[0x05000000+2*(16*d['bank']+d['foreground'])];rgb=tuple(((colour>>s)&31)*255//31 for s in (0,5,10))
     if d['id']!='dungeon-travel.heading':require(d['x']>=6 and d['x']+glyph['advance']<=144,'Dungeon picker cursor/edge collision')
     for y,line in enumerate(glyph['rows']):
      for x,bit in enumerate(line):require((pic.getpixel((d['origin'][0]+d['x']+x,d['origin'][1]+16*d['y']+y))==rgb)==(bit=='#'),'Dungeon picker final pixels differ: '+repr((case,tag,d['id'],hex(d['code']))));pixels+=1
   with Debugger(g,callback,max_events=200000) as debug:
    for a in set(c.ADDRESSES)|{0x0801DFAC,0x080524EE,0x08052354,0x0805236E,0x08052378,0x080523DE,0x08001798,0x08001750,0x08001888}:debug.breakpoint(a)
    for cycle in range(3):
     start=len(c.reads);g.press('A',hold=1,wait=120);capture('opened-'+str(cycle));require([r['id'] for r in c.reads[start:]]==['dungeon-travel.heading']+['dungeon-travel.'+str(i) for i in labels],'Dungeon picker original selected rows differ')
     g.press('UP',wait=20);require(m.u8[0x020101A1]==len(labels)-1,'Dungeon picker upward wrap differs');capture('last-'+str(cycle));g.press('DOWN',wait=20);require(m.u8[0x020101A1]==0,'Dungeon picker downward wrap differs')
     if cycle<2 or target is None:g.press('B',hold=1,wait=120)
     else:
      for _ in range(target):g.press('DOWN',wait=20)
      capture('selected');g.press('A',hold=1,wait=120)
     require(len(returns)==cycle+1,'Dungeon picker failed to return');require(len(closes)==2*(cycle+1),'Dungeon picker windows not both closed')
   require(bytes(m[0x0200DF28:0x0200E888])==inventory and m.u32[hero+0x60]==gold and g.snapshot().battery==fixture.battery,'Dungeon picker changed items/gold/save');results.append({'case':case,'state':state,'effective_group':group,'labels':labels,'target':target,'stored_meadow_controlled_selector':meadow,'inputs':g.inputs,'overrides':overrides,'reads':c.reads,'selectors':selectors,'returns':returns,'creates':creates,'closures':closes,'caller_guard_abi_preserved':True,'visible_pixels_checked':pixels,'images':images});(out/'partial.json').write_text(json.dumps(results,indent=2)+'\n')
 report={'passed':True,'rom_sha256':digest(rom),'cases':results,'scope':'Controlled bank-call entry to complete52304 owner with recorded progression/unlock-return overrides. All eight original availability rows, locked fallbacks and BA/BB alternate, original160px heading/144px five-row list, native cursor wrapping, ten positive selections, cancellation/twice reopening, full pixels and ABI, unchanged items/gold/battery. Stored meadow label has one explicit selector override because the immutable availability rows do not emit it. Actual travel and natural unlocking remain separate.'};(out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print('Dungeon travel:',len(results),'passed')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--source',type=Path,default=ROOT/'build/english');p.add_argument('--only');a=p.parse_args();run(a.source,a.only)
