"""Staged native save-error panel routing, original height and complete consequences."""
import argparse,json,struct
from pathlib import Path
import mgba.log
from tools.rom import ROOT,digest,require
from tools.emulator import Session,Debugger,ffi
from tools.dialogue_checks import TextChecks
from tools.verify_result_ui import native_format
# source slot, message block, formatter return, modal return
OWNERS={'suspend':(0x5C4,0x14DAA,None,0x14DD4),'corrupt':(0x598,0x15030,None,0x15184)}

def run(source,only=None):
 out=source/'save-notices-validation';mgba.log.silence();rom=(source/'torneko-2-english.gba').read_bytes();build=json.loads((source/'build.json').read_text());require(digest(rom)==build['output_sha256'],'Stale save-notice ROM')
 from tools import verify_player_status_prototype as status
 prior=status.OUT
 try:status.OUT=out;fixture=status.ready(rom,build)
 finally:status.OUT=prior
 rows={r['table_offset']:r for r in build['save_notices']['entries']};results=[]
 for owner,(slot,start,formatted,modal_end) in OWNERS.items():
  if only and only!=owner:continue
  for amount in (None,):
   entry,prologue,epilogue,end=(0x14780,0x1478C,0x14E4A,0x14E58) if owner=='suspend' else (0x14F04,0x14F0C,0x1519A,0x151A4)
   case=owner+(f'-{amount}' if amount is not None else '');print('Save notice:',case,flush=True);row=rows[slot]
   with Session(rom,out/case) as g:
    g.restore(fixture);m=g.core.memory;initial=[];returns=[];formats=[];pending={};overrides=[];draws=[];images={};pixels=0;modals=[];modal_returns=[];panel=TextChecks(g,{} if formatted else {row['offset']+0x08000000:row|{'layout':{'pages':[[row['id']]]*(2 if slot==0x5C4 else 1)}}})
    def write(a,data):
     overrides.append({'address':a,'before':bytes(m[a:a+len(data)]).hex(),'after':data.hex()})
     for i,v in enumerate(data):m.u8[a+i]=v
    def reg(e,index,value):overrides.append({'event':e,'register':index,'after':value});g.core.cpu.gprs[index]=value
    def jump(e,address,reason):overrides.append({'event':e,'pc_after':address+0x08000000,'reason':reason});require(g.core._core.writeRegister(g.core._core,b'pc',ffi.new('uint32_t*',address+0x08000000)),'Save notice dispatch failed')
    item=bytearray(120);struct.pack_into('<I',item,0,0xC8000000);item[4:6]=b'\1\1';item[8]=bytes(m[0x020013D0:0x020014D0]).index(177);write(0x0200DF28,item);at=0x02003BAC+20*177;write(at,struct.pack('<I',m.u32[at]|0x40000000))
    hero=m.u32[0x02001624];gold_before=m.u32[hero+0x60]
    def callback(e):
     nonlocal pending
     a,r=e['address'],e['registers']
     if a==0x08015848 and not initial:
      initial.append(e|{'guard':bytes(m[r[13]:r[13]+32]).hex()});jump(e,entry,'Controlled dispatch from native Drink; actual save-handler prologue executes.');return
     if not initial or returns:return
     if a==prologue+0x08000000:
      reg(e,3,0)
      jump(e,start,'Original immutable-ROM save-error text block; save validation excluded.')
     if formatted and a==0x08000FB8 and r[14]==formatted+0x08000001:
      require(r[1]==row['offset']+0x08000000 and r[0]==r[13]+4 and r[2]==amount,'Save notice native format/source/number differs');raw=native_format(bytes.fromhex(row['encoded_hex']),[r[2]],m)
      require(len(raw)<=row['maximum_bytes']<=256,'Save notice output exceeds capacity');pending={'regs':r,'raw':raw,'guard':bytes(m[r[0]+256:r[0]+272])}
     if formatted and a==formatted+0x08000000 and pending:
      old=pending['regs'];p=old[0];raw=pending['raw'];require(bytes(m[p:p+len(raw)])==raw and bytes(m[p+256:p+272])==pending['guard'] and r[4:12]==old[4:12] and r[13]==old[13],'Save notice output/guard/ABI differs')
      formats.append({'id':row['id'],'hex':raw.hex(),'bytes':len(raw),'guard_abi_preserved':True});panel.resources[p]=row|{'encoded_hex':raw.hex(),'layout':{'pages':[[row['id']]]*(2 if slot==0x5C4 else 1)}};pending={}
     if a==0x08015A18:
      require(r[14]==modal_end+0x08000001 and r[0] in panel.resources and r[2]==int(formatted is not None),'Save notice native modal source/choice mode differs');modals.append(e)
     if a==0x08001BC4 and panel.active:
      w=r[0];key=(w,r[1],r[13],r[14],m.u8[w+2],m.u8[w+3])
      if not draws or draws[-1]['key']!=key:draws.append({'key':key,'window':w,'code':r[1],'x':m.u8[w+2],'y':m.u8[w+3],'origin':[m.u8[w],m.u8[w+1]],'foreground':m.u8[0x020000C2],'bank':m.u16[m.u32[w+12]]>>12})
     if a in panel.ADDRESSES:panel.callback(e)
     if a==modal_end+0x08000000:
      require(modals,'Save notice modal return without entry');old=modals[0]['registers'];require(r[4:12]==old[4:12] and r[13]==old[13],'Save notice modal ABI differs');modal_returns.append(e)
      if modal_end!=epilogue:jump(e,epilogue,'Keep actual modal result but exclude save-reset side effects; original epilogue executes.')
     if a==end+0x08000000:
      old=initial[0]['registers'];require(r[4:12]==old[4:12] and r[13]==old[13] and r[1]==old[14] and bytes(m[r[13]:r[13]+32]).hex()==initial[0]['guard'],'Save notice caller ABI/guard differs');returns.append(e)
    with Debugger(g,callback,max_events=150000) as debug:
     for a in {0x08015848,prologue+0x08000000,0x08000FB8,0x08015A18,end+0x08000000,modal_end+0x08000000}|set(panel.ADDRESSES)|({formatted+0x08000000} if formatted else set()):debug.breakpoint(a)
     g.press('B',hold=8,wait=30);g.press('A',wait=30);g.press('A',wait=30);actions=[]
     for i in range(7):
      n=m.u16[0x0200CDD0+i*2]
      if not n:break
      actions.append(n)
     require(13 in actions,'Save notice Drink trigger absent')
     for _ in range(actions.index(13)):g.press('DOWN',wait=20)
     g.capture('menu');images['menu.png']=digest((g.output/'menu.png').read_bytes());g.press('A',wait=0);captured=False;advanced=0
     for _ in range(1200):
      g.frames(1)
      waiting=panel.active and panel.active['page_waits']>advanced
      if waiting or (panel.reads and not panel.active and not captured):
       g.frames(8);picture=f'page-{advanced}';pic=g.capture(picture);images[picture+'.png']=digest((g.output/(picture+'.png')).read_bytes())
       for d in draws:
        glyph,_=panel.glyph_record(d['code']);colour=m.u16[0x05000000+2*(16*d['bank']+d['foreground'])];rgb=tuple(((colour>>s)&31)*255//31 for s in (0,5,10))
        for y,line in enumerate(glyph['rows']):
         for x,bit in enumerate(line):require((pic.getpixel((d['origin'][0]+d['x']+x,d['origin'][1]+d['y']*16+y))==rgb)==(bit=='#'),'Save notice final pixels differ');pixels+=1
       if waiting:advanced+=1;draws.clear()
       else:captured=True
       g.press('A',wait=0)
      if returns:break
     require(len(initial)==len(returns)==len(modals)==len(modal_returns)==len(panel.reads)==1 and len(formats)==int(bool(formatted)) and captured and not pending,'Save notice route incomplete: '+repr((case,len(modals),len(modal_returns),len(panel.reads),len(returns))))
    require(g.snapshot().battery==fixture.battery and m.u32[hero+0x60]==gold_before,'Save notice render probe changed gold/battery')
    results.append({'case':case,'owner':owner,'id':row['id'],'amount':amount,'inputs':g.inputs,'overrides':overrides,'formats':formats,'reads':panel.reads,'modals':modals,'modal_returns':modal_returns,'caller_guard_abi_preserved':True,'visible_pixels_checked':pixels,'images':images})
 report={'passed':True,'rom_sha256':digest(rom),'cases':results,'scope':'Two original save-error message blocks execute after their full native prologues and return via original epilogues. Four-row improper suspension and two-row damaged adventure-log messages keep every stated consequence. Immutable-ROM routing, original two-row panel and native page waits, all glyphs/pixels, modal/caller ABI, gold and battery checked. No corruption or improper suspend is manufactured; the probes exclude save validation and its subsequent inventory/gold reset.'}
 (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print('Save notice:',len(results),'passed',flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,default=ROOT/'build/english');p.add_argument('--only');a=p.parse_args();run(a.source,a.only)
