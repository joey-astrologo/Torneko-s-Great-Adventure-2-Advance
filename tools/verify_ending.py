"""Ending source blocks with original descriptor loads, delays and auto pages."""
import argparse,json,struct,re
from pathlib import Path
import mgba.log
from tools.rom import ROOT,digest,require
from tools.emulator import Session,Debugger,ffi
from tools import dialogue_checks as checks
from tools.dialogue_checks import TextChecks,player_layout_cases
from tools.name_entry import HERO
SETUPS=[(0,0x557C8,0x55892,0x558AE,0x558B2),(18,0x55934,0x5597C,0x55996,0x5599A),(31,0x559CC,0x55A00,0x55A1A,0x55A1E),(35,0x55A50,0x55A98,0x55AB2,0x55AB6),(44,0x55AEC,0x55B3A,0x55B54,0x55B58)]
original_codes=checks.rendered_codes

def ending_codes(payload,player=None,foreground=None,saved=None):
 # Remove only this owner's verified nonprinting commands for expected ink.
 clean=bytearray();i=0
 while i<len(payload):
  c=payload[i]
  if c==64:
   require(payload[i+1] in (87,119) and payload[i+3]==64,'Unsupported ending delay');i+=4
  elif c==19:
   require(payload[i+1] in (48,49),'Unsupported ending mode');i+=2
  else:
   n=2 if c>128 and not 160<=c<=223 else 1;clean.extend(payload[i:i+n]);i+=n
 return original_codes(bytes(clean),player,foreground,saved)

class EndingChecks(TextChecks):
 def callback(self,e):
  prior=checks.rendered_codes
  try:checks.rendered_codes=ending_codes;super().callback(e)
  finally:checks.rendered_codes=prior

def run(source,only=None):
 out=source/'ending-validation';mgba.log.silence();rom=(source/'torneko-2-english.gba').read_bytes();build=json.loads((source/'build.json').read_text());require(digest(rom)==build['output_sha256'],'Stale ending ROM')
 from tools import verify_player_status_prototype as status
 prior=status.OUT
 try:status.OUT=out;fixture=status.ready(rom,build)
 finally:status.OUT=prior
 resources={r['offset']+0x08000000:r for r in build['ending_text']['entries']};results=[]
 for row in resources.values():
  index=row['index']
  if only is not None and index!=only:continue
  group,setup,load,setup_epilogue,setup_end=max((s for s in SETUPS if s[0]<=index),key=lambda s:s[0])
  for profile,player in (player_layout_cases() if '{player}' in row['english'] else [('ordinary',None)]):
   case=f'{index}-{profile}';print('Ending:',case,flush=True)
   with Session(rom,out/case) as g:
    g.restore(fixture);m=g.core.memory;initial=[];setup_returns=[];returns=[];overrides=[];draws=[];images={};pixels=0;modals=[];modal_returns=[];delays=[];modes=[];panel=EndingChecks(g,resources);pending=[];page_ready=[];captured=set();clock=0
    def write(a,data):
     overrides.append({'address':a,'before':bytes(m[a:a+len(data)]).hex(),'after':data.hex()})
     for i,v in enumerate(data):m.u8[a+i]=v
    def reg(e,i,v):overrides.append({'event':e,'register':i,'after':v});g.core.cpu.gprs[i]=v
    def jump(e,at,why):
     overrides.append({'event':e,'pc_after':at+0x08000000,'reason':why});require(g.core._core.writeRegister(g.core._core,b'pc',ffi.new('uint32_t*',at+0x08000000)),'Ending redirect failed')
    item=bytearray(120);struct.pack_into('<I',item,0,0xC8000000);item[4:6]=b'\1\1';item[8]=bytes(m[0x020013D0:0x020014D0]).index(177);write(0x0200DF28,item);at=0x02003BAC+20*177;write(at,struct.pack('<I',m.u32[at]|0x40000000))
    hero=m.u32[0x02001624];gold=m.u32[hero+0x60]
    if player:write(HERO,player.ljust(16,b'\0'))
    player=bytes(m[HERO:HERO+16]);chunks=bytes.fromhex(row['encoded_hex'])[:-1].split(b'\r');page_counts=[len(ending_codes(b'\r'.join(chunks[i:i+2])+b'\0',player)) for i in range(0,len(chunks),2)];cumulative=[]
    for n in page_counts:cumulative.append((cumulative[-1] if cumulative else 0)+n)
    require(len(page_counts)==len(row['layout']['pages']),'Ending expected page split differs')
    def abi(e,origin):
     r=e['registers'];old=origin['registers'];require(r[4:12]==old[4:12] and r[13]==old[13] and r[0]==old[14] and bytes(m[r[13]:r[13]+32]).hex()==origin['guard'],'Ending caller ABI/guard differs')
    def callback(e):
     a,r=e['address'],e['registers']
     if a==0x08015848 and not initial:
      initial.append(e|{'guard':bytes(m[r[13]:r[13]+32]).hex(),'inventory':bytes(m[0x0200DF28:0x0200E888]).hex()});jump(e,setup,'Controlled Drink entry into the complete original scene setup frame.');return
     if not initial or returns:return
     if a==setup+2+0x08000000:jump(e,load,'Skip actor staging; execute the original descriptor-literal load and store.')
     if a==load+6+0x08000000:jump(e,setup_epilogue,'Descriptor installed natively; remaining scene staging excluded.')
     if a==setup_end+0x08000000:
      abi(e,initial[0]);require(m.u32[0x02011BB4]==0x08000000+build['ending_text']['table_offset']+group*12,'Ending native setup descriptor differs');setup_returns.append(e)
      write(0x02011BB4,struct.pack('<I',m.u32[0x02011BB4]+12*(index-group)));write(0x02003B30,struct.pack('<I',1));write(0x0200C880,b'\1');reg(e,14,initial[0]['registers'][14]);jump(e,0x54F44,'Select controlled descriptor and ending auto-advance state, then full dispatcher frame.')
     if a==0x08054F48:jump(e,0x54FDE,'Original text dispatch block; actor sequencing and fades excluded.')
     if a==0x08015A50:
      require(r[0]==row['offset']+0x08000000 and r[2]==0 and m.u32[r[13]]==0x0805509D and m.u32[r[13]+4]==1 and m.u32[0x0200C87C]==row['timer'],'Ending original modal selection/callback/timer differs');modals.append(e);pending.append(e)
     if a==0x08001750:draws[:]=[d for d in draws if d['window']!=r[0]]
     if a==0x08001BC4 and panel.active:
      w=r[0];key=(w,r[1],r[13],r[14],m.u8[w+2],m.u8[w+3])
      if not draws or draws[-1]['key']!=key:draws.append({'key':key,'window':w,'code':r[1],'x':m.u8[w+2],'y':m.u8[w+3],'origin':[m.u8[w],m.u8[w+1]],'foreground':m.u8[0x020000C2],'bank':m.u16[m.u32[w+12]]>>12})
     if a in panel.ADDRESSES:
      panel.callback(e)
      if panel.active and a==0x08001C14 and panel.active['prepared'] in cumulative:
       p=cumulative.index(panel.active['prepared'])
       if not any(q['page']==p for q in page_ready):page_ready.append({'page':p,'frame':e['frame']})
     if a==0x0805509C:
      raw=bytes(m[r[0]:r[0]+4]);require(raw[0]==raw[3]==64 and raw[1] in (87,119),'Ending callback source differs');delays.append({'raw_hex':raw.hex(),'frames':raw[2]*(60 if raw[1]==87 else 10),'entry':e})
     if a==0x080550C2:
      require(r[0]==0x01000000+delays[-1]['frames'],'Ending callback delay result differs');delays[-1]['return']=e
     if a==0x08001E22 and delays:delays[-1]['wait_start_frame']=e['frame']
     if a==0x08001E46 and delays:
      d=delays[-1];require(e['frame']-d['wait_start_frame']==d['frames'],'Ending native timed delay differs');d['wait_end_frame']=e['frame']
     if a==0x08002110:modes.append(e|{'value':r[0]})
     if pending and a==(pending[-1]['registers'][14]&~1):
      old=pending.pop()['registers'];require(r[4:12]==old[4:12] and r[13]==old[13],'Ending modal ABI differs');modal_returns.append(e|{'mode':m.u8[0x0200C880]})
     if a==0x08055040 and modal_returns:jump(e,0x55090,'Text completed; actor sequencing and fades excluded, original dispatcher epilogue.')
     if a==0x08055096:abi(e,initial[0]);returns.append(e)
    def capture(p):
     nonlocal pixels
     tag='page-'+str(p);pic=g.capture(tag);images[tag+'.png']=digest((g.output/(tag+'.png')).read_bytes());require(draws,'Ending no visible text')
     require(draws[0]['origin']==[8,8 if row['flags']&255 else 120],'Ending native placement differs')
     for d in draws:
      glyph,_=panel.glyph_record(d['code']);colour=m.u16[0x05000000+2*(16*d['bank']+d['foreground'])];rgb=tuple(((colour>>s)&31)*255//31 for s in (0,5,10))
      for y,line in enumerate(glyph['rows']):
       for x,bit in enumerate(line):require((pic.getpixel((d['origin'][0]+d['x']+x,d['origin'][1]+16*d['y']+y))==rgb)==(bit=='#'),'Ending final pixels differ: '+repr((case,p,hex(d['code']),d['x'],d['y'],x,y)));pixels+=1
    addresses={0x08015848,setup+2+0x08000000,load+6+0x08000000,setup_end+0x08000000,0x08054F48,0x08015A50,0x08001750,0x08055010,0x08055040,0x08055096,0x0805509C,0x080550C2,0x08001E22,0x08001E46,0x08002110}
    with Debugger(g,callback,max_events=350000) as debug:
     for a in addresses|set(panel.ADDRESSES):debug.breakpoint(a)
     g.press('B',hold=8,wait=30);g.press('A',wait=30);g.press('A',wait=30);actions=[]
     for i in range(7):
      n=m.u16[0x0200CDD0+2*i]
      if not n:break
      actions.append(n)
     require(13 in actions,'Ending Drink trigger absent')
     for _ in range(actions.index(13)):g.press('DOWN',wait=20)
     g.press('A',hold=1,wait=0)
     for tick in range(12000):
      for q in page_ready:
       if q['page'] not in captured and g.core.frame_counter>=q['frame']+6:capture(q['page']);captured.add(q['page'])
      if returns:break
      g.frames(1)
     require(len(initial)==len(setup_returns)==len(returns)==len(modals)==len(modal_returns)==len(panel.reads)==1 and not panel.active and not pending,'Ending native route incomplete: '+repr((case,len(returns),len(panel.reads),page_ready)))
    require(len(images)==len(page_counts) and panel.reads[0]['id']==row['id'],'Ending pages/source incomplete')
    expected_delays=[c['raw_hex'] for c in row['layout']['ending_controls'] if c['token'].startswith('{wait:')];require([d['raw_hex'] for d in delays]==expected_delays and all('wait_end_frame' in d for d in delays),'Ending delay sequence incomplete')
    expected_mode=0 if index==0 else 1;require(modal_returns[0]['mode']==expected_mode,'Ending text mode differs')
    require(m.u32[hero+0x60]==gold and bytes(m[0x0200DF28:0x0200E888]).hex()==initial[0]['inventory'] and g.snapshot().battery==fixture.battery,'Ending text probe changed items/gold/save')
    results.append({'case':case,'index':index,'profile':profile,'inputs':g.inputs,'overrides':overrides,'reads':panel.reads,'modals':modals,'modal_returns':modal_returns,'setup_returns':setup_returns,'timed_delays':delays,'mode_events':modes,'caller_guard_abi_preserved':True,'inventory_stable_during_message_block':True,'automatic_pages_without_input':True,'visible_pixels_checked':pixels,'page_ready':page_ready,'images':images})
    (out/'partial.json').write_text(json.dumps(results,indent=2)+'\n')
 report={'passed':True,'rom_sha256':digest(rom),'cases':results,'scope':'Controlled Drink dispatch through full original scene-setup and ending-dispatcher frames, original relocated descriptor-literal load/store and native text blocks. All original descriptor flags/timers, W/w command values and actual elapsed native delay frames, mode0/1 commands, auto pages without advancing input, three name profiles, placement, pixels and helper/caller ABI. Actor staging, movement, fades and endgame/save/credit progression are excluded; selectors and global auto-advance state are recorded overrides. Inventory is stable across the message block after the Drink trigger consumes its herb; gold/battery unchanged.'};(out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print('Ending:',len(results),'passed')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--source',type=Path,default=ROOT/'build/english');p.add_argument('--only',type=int);a=p.parse_args();run(a.source,a.only)
