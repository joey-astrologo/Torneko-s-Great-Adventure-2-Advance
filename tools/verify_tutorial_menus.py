"""Native soldier/adventurer help menus and their complete direct prose."""
import argparse,json,struct
from pathlib import Path
import mgba.log
from tools.rom import ROOT,digest,require
from tools.emulator import Session,Debugger,ffi
from tools.dialogue_checks import TextChecks
from tools.bakery_playtest import service_ready

def run(source,only=None):
 out=source/'tutorial-all-menu-validation';rom=(source/'torneko-2-english.gba').read_bytes();b=json.loads((source/'build.json').read_text());require(digest(rom)==b['output_sha256'],'Stale tutorial-help ROM');mgba.log.silence();fixture=service_ready(rom,out);rows={r['offset']+0x08000000:r for r in b['tutorial_help']['entries']};by_src={r['source']['offset']:r for r in rows.values()};groups={g['index']:g for g in b['tutorial_help']['groups']};results=[]
 for index,group in groups.items():
  if only is not None and index!=only:continue
  case=str(index);print('Tutorial help:',case,flush=True)
  with Session(rom,out/case) as g:
   g.restore(fixture);m=g.core.memory;c=TextChecks(g,rows);initial=[];returns=[];overrides=[];draws=[];images={};pixels=0;cycle=0;modals=[];modal_returns=[];pending=[];seen_pages=[];current_group=group
   def reg(e,i,v):overrides.append({'event':e,'register':i,'after':v});g.core.cpu.gprs[i]=v
   def jump(e,at,why):
    overrides.append({'event':e,'pc_after':at+0x08000000,'reason':why});require(g.core._core.writeRegister(g.core._core,b'pc',ffi.new('uint32_t*',at+0x08000000)),'Tutorial redirect failed')
   inventory=bytes(m[0x0200DF28:0x0200E888]);hero=m.u32[0x02001624];gold=m.u32[hero+0x60]
   def callback(e):
    a,r=e['address'],e['registers']
    if a==0x0801DFAC and len(initial)==len(returns):
     initial.append(e|{'guard':bytes(m[r[13]:r[13]+32]).hex()});draws.clear();jump(e,0x4F8F4,'Controlled bank invocation into full script-reader frame.');return
    if len(initial)==len(returns):return
    if a==0x0804F8F8:
     reg(e,4,index);jump(e,0x4F9AA,'Select owned menu configuration; original descriptor/outer-table loads execute, event-bank prelude excluded.')
    if a==0x08015A18:
     require(r[0] in rows and rows[r[0]]['kind']=='prose','Tutorial selected an unowned prose source');modals.append(e|{'id':rows[r[0]]['id']});pending.append(e)
    if a in (0x08001750,0x08001888):draws[:]=[d for d in draws if d['window']!=r[0]]
    if a==0x080021B4 and r[1] in rows:
     row=rows[r[1]];w=r[0]
     if row['kind']=='heading':require(bytes(m[w:w+2])==bytes((8,24)) and bytes(m[w+4:w+6])==bytes((28,1)),'Tutorial header geometry differs')
     if row['kind']=='label':require(bytes(m[w:w+2])==bytes((8,56)) and m.u8[w+4]*8==(224 if current_group['menu'] in(10,13,14) else min(current_group['descriptor'][6]*16,224)) and m.u8[w+5]==current_group['rows'],'Tutorial topic geometry differs')
    if a==0x08001BC4 and c.active:
     w=r[0];key=(w,r[1],r[13],r[14],m.u8[w+2],m.u8[w+3])
     if not draws or draws[-1]['key']!=key:draws.append({'key':key,'window':w,'code':r[1],'x':m.u8[w+2],'y':m.u8[w+3],'origin':[m.u8[w],m.u8[w+1]],'foreground':m.u8[0x020000C2],'bank':m.u16[m.u32[w+12]]>>12,'id':c.active['id']})
    if a in c.ADDRESSES:c.callback(e)
    if pending and a==(pending[-1]['registers'][14]&~1):
     old=pending.pop()['registers'];require(r[4:12]==old[4:12] and r[13]==old[13],'Tutorial modal ABI differs');modal_returns.append(e)
    if a==0x0804FA44:jump(e,0x4FA52,'Native menu returned; script pointer advancement excluded, original epilogue.')
    if a==0x0804FA58:
     old=initial[-1]['registers'];require(r[4:12]==old[4:12] and r[13]==old[13] and r[0]==old[14] and bytes(m[r[13]:r[13]+32]).hex()==initial[-1]['guard'],'Tutorial caller ABI/guard differs');returns.append(e)
   def capture(tag):
    nonlocal pixels
    g.frames(8);pic=g.capture(tag);images[tag+'.png']=digest((g.output/(tag+'.png')).read_bytes());require(draws,'Tutorial missing visible text')
    for d in draws:
     glyph,_=c.glyph_record(d['code']);colour=m.u16[0x05000000+2*(16*d['bank']+d['foreground'])];rgb=tuple(((colour>>s)&31)*255//31 for s in (0,5,10))
     if by_src[int(d['id'].split('.')[-1],16)]['kind']=='label':require(d['x']>=6,'Tutorial label in cursor reserve')
     for y,line in enumerate(glyph['rows']):
      for x,bit in enumerate(line):require((pic.getpixel((d['origin'][0]+d['x']+x,d['origin'][1]+16*d['y']+y))==rgb)==(bit=='#'),'Tutorial final pixels differ: '+repr((case,tag,d['id'],hex(d['code']),d['x'],d['y'])));pixels+=1
   def move(target):
    for _ in range(8):
     if m.u8[0x020101A1]==target:return
     g.press('DOWN',wait=20)
    raise ValueError('Tutorial cursor failed to reach topic')
   def check_menu(start):
    expected=[by_src[current_group['prose'][0]['source']['offset']]['id']]+[by_src[e['offset']]['id'] for e in current_group['labels']]
    require([r['id'] for r in c.reads[start:]]==expected,'Tutorial native header/labels differ')
   with Debugger(g,callback,max_events=600000) as debug:
    for a in set(c.ADDRESSES)|{0x0801DFAC,0x0804F8F8,0x0804FA44,0x0804FA58,0x08015A18,0x08050E6E,0x080510CE,0x08001750,0x08001888}:debug.breakpoint(a)
    for cycle in range(3):
     current_group=group;start=len(c.reads);g.press('A',hold=1,wait=120);check_menu(start);capture('opened-'+str(cycle));g.press('UP',wait=20);require(m.u8[0x020101A1]<current_group['descriptor'][7],'Tutorial upward cursor out of bounds');capture('last-'+str(cycle));g.press('DOWN',wait=20);require(m.u8[0x020101A1]<current_group['descriptor'][7],'Tutorial downward cursor out of bounds')
     positions={m.u8[0x020101A1]};expected_count=current_group['descriptor'][7]
     for column in range(2 if current_group['menu'] in(10,13,14) else 1):
      for step in range(expected_count):
       g.press('DOWN',wait=16);positions.add(m.u8[0x020101A1])
      if current_group['menu'] in(10,13,14):g.press('RIGHT',wait=16);positions.add(m.u8[0x020101A1])
     require(positions==set(range(expected_count)),'Tutorial all cursor coverage incomplete: '+repr((index,positions,expected_count)))
     capture('cursor-tour-'+str(cycle));g.press('B',hold=1,wait=120)
     require(len(returns)==cycle+1,'Tutorial menu did not exit')
   require(len(modals)==len(modal_returns) and not c.active and not pending,'Tutorial modal remained active');require(bytes(m[0x0200DF28:0x0200E888])==inventory and m.u32[hero+0x60]==gold and g.snapshot().battery==fixture.battery,'Tutorial browsing changed items/gold/save');results.append({'case':case,'group':index,'inputs':g.inputs,'overrides':overrides,'reads':c.reads,'modals':modals,'modal_returns':modal_returns,'returns':returns,'pages':seen_pages,'caller_guard_abi_preserved':True,'visible_pixels_checked':pixels,'images':images});(out/'partial.json').write_text(json.dumps(results,indent=2)+'\n')
 report={'passed':True,'rom_sha256':digest(rom),'cases':results,'scope':'RENDER/CURSOR-ONLY prototype: all27 configurations, three openings, original text source/geometry, full cursor coverage, B return and unchanged items/gold/save. No topic selections or bank/prose outcomes are claimed by this probe. Original malformed legacy mappings remain unresolved. Prior six-group proof is separate. Original verifier scope for the base family: six controlled bank-call entries into full original4F8F4 script-reader frame and owned menu dispatch blocks. Native private outer/inner pointer loads, complete50DD0/50FB8 menus, original header/list geometry, all topics/prose pages, cursor wrap, Cancel/B and twice reopening, both soldier pages/Left/Right, exact pixels and modal/caller ABI. Script prelude/progression and natural NPC access are excluded; inventory/gold/battery remain unchanged.'};(out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print('Tutorial help:',len(results),'passed')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--source',type=Path,default=ROOT/'build/english');p.add_argument('--only',type=int);a=p.parse_args();run(a.source,a.only)
