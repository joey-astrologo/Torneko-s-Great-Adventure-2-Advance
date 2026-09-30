"""Staged native dungeon-shop modal/confirmation rendering and original choices."""
import argparse,json,struct
from pathlib import Path
import mgba.log
from tools.rom import ROOT,digest,require
from tools.emulator import Session,Debugger,ffi
from tools.dialogue_checks import TextChecks
from tools.verify_result_ui import native_format
# source slot, message block, formatter return, modal return
OWNERS={'sell':(0x41C,0x243DC,0x243EC,0x24410),'buy':(0x424,0x244C2,0x244D8,0x244FC),'half-price':(0x464,0x24512,0x24520,0x2453A),'thank-zero':(0x420,0x2444C,None,0x245CE),'no-funds':(0x428,0x24568,None,0x245CE),'thank-paid':(0x420,0x245A4,None,0x245CE),'thank-credit':(0x420,0x245E0,None,0x2460A)}

def run(source,only=None):
 out=source/'dungeon-shop-validation';mgba.log.silence();rom=(source/'torneko-2-english.gba').read_bytes();build=json.loads((source/'build.json').read_text());require(digest(rom)==build['output_sha256'],'Stale shop ROM')
 from tools import verify_player_status_prototype as status
 prior=status.OUT
 try:status.OUT=out;fixture=status.ready(rom,build)
 finally:status.OUT=prior
 rows={r['table_offset']:r for r in build['dungeon_shop']['entries']};results=[]
 for owner,(slot,start,formatted,modal_end) in OWNERS.items():
  if only and only!=owner:continue
  for amount in ((17,0,999999,0x7FFFFFFF) if formatted else (None,)):
   case=owner+(f'-{amount}' if amount is not None else '');print('Dungeon shop:',case,flush=True);row=rows[slot]
   with Session(rom,out/case) as g:
    g.restore(fixture);m=g.core.memory;initial=[];returns=[];formats=[];pending={};overrides=[];draws=[];images={};pixels=0;modals=[];modal_returns=[];panel=TextChecks(g,{} if formatted else {row['offset']+0x08000000:row|{'layout':{'pages':[[row['id']]]}}})
    def write(a,data):
     overrides.append({'address':a,'before':bytes(m[a:a+len(data)]).hex(),'after':data.hex()})
     for i,v in enumerate(data):m.u8[a+i]=v
    def reg(e,index,value):overrides.append({'event':e,'register':index,'after':value});g.core.cpu.gprs[index]=value
    def jump(e,address,reason):overrides.append({'event':e,'pc_after':address+0x08000000,'reason':reason});require(g.core._core.writeRegister(g.core._core,b'pc',ffi.new('uint32_t*',address+0x08000000)),'Shop dispatch failed')
    item=bytearray(120);struct.pack_into('<I',item,0,0xC8000000);item[4:6]=b'\1\1';item[8]=bytes(m[0x020013D0:0x020014D0]).index(177);write(0x0200DF28,item);at=0x02003BAC+20*177;write(at,struct.pack('<I',m.u32[at]|0x40000000))
    hero=m.u32[0x02001624];gold_before=m.u32[hero+0x60]
    def callback(e):
     nonlocal pending
     a,r=e['address'],e['registers']
     if a==0x08015848 and not initial:
      initial.append(e|{'guard':bytes(m[r[13]:r[13]+32]).hex()});jump(e,0x243C0,'Controlled dispatch from native Drink; actual shop prologue executes.');return
     if not initial or returns:return
     if a==0x080243CC:
      if owner=='sell':reg(e,2,amount)
      elif owner=='buy':reg(e,3,amount)
      elif owner=='half-price':
       for index,value in ((4,amount),(5,0),(6,0x200),(7,m.u32[0x0802454C]),(8,m.u32[0x08024550]),(9,m.u32[0x08024544])):reg(e,index,value)
      else:reg(e,3,0)
      jump(e,start,'Original text block with recorded price/flags; commerce calculations excluded.')
     if formatted and a==0x08000FB8 and r[14]==formatted+0x08000001:
      require(r[1]==row['offset']+0x08000000 and r[0]==r[13]+4 and r[2]==amount,'Shop native format/source/number differs');raw=native_format(bytes.fromhex(row['encoded_hex']),[r[2]],m)
      require(len(raw)<=row['maximum_bytes']<=256,'Shop output exceeds capacity');pending={'regs':r,'raw':raw,'guard':bytes(m[r[0]+256:r[0]+272])}
     if formatted and a==formatted+0x08000000 and pending:
      old=pending['regs'];p=old[0];raw=pending['raw'];require(bytes(m[p:p+len(raw)])==raw and bytes(m[p+256:p+272])==pending['guard'] and r[4:12]==old[4:12] and r[13]==old[13],'Shop output/guard/ABI differs')
      formats.append({'id':row['id'],'hex':raw.hex(),'bytes':len(raw),'guard_abi_preserved':True});panel.resources[p]=row|{'encoded_hex':raw.hex(),'layout':{'pages':[[row['id']]]}};pending={}
     if a==0x08015A18:
      require(r[14]==modal_end+0x08000001 and r[0] in panel.resources and r[2]==int(formatted is not None),'Shop native modal source/choice mode differs');modals.append(e)
     if a==0x08001BC4 and panel.active:
      w=r[0];key=(w,r[1],r[13],r[14],m.u8[w+2],m.u8[w+3])
      if not draws or draws[-1]['key']!=key:draws.append({'key':key,'window':w,'code':r[1],'x':m.u8[w+2],'y':m.u8[w+3],'origin':[m.u8[w],m.u8[w+1]],'foreground':m.u8[0x020000C2],'bank':m.u16[m.u32[w+12]]>>12})
     if a in panel.ADDRESSES:panel.callback(e)
     if a==modal_end+0x08000000:
      require(modals,'Shop modal return without entry');old=modals[0]['registers'];require(r[4:12]==old[4:12] and r[13]==old[13],'Shop modal ABI differs');modal_returns.append(e)
      if modal_end!=0x2460A:jump(e,0x2460A,'Keep actual modal result but exclude commerce side effects; original epilogue executes.')
     if a==0x0802461A:
      old=initial[0]['registers'];require(r[4:12]==old[4:12] and r[13]==old[13] and r[0]==old[14] and bytes(m[r[13]:r[13]+32]).hex()==initial[0]['guard'],'Shop caller ABI/guard differs');returns.append(e)
    with Debugger(g,callback,max_events=150000) as debug:
     for a in {0x08015848,0x080243CC,0x08000FB8,0x08015A18,0x0802461A,modal_end+0x08000000}|set(panel.ADDRESSES)|({formatted+0x08000000} if formatted else set()):debug.breakpoint(a)
     g.press('B',hold=8,wait=30);g.press('A',wait=30);g.press('A',wait=30);actions=[]
     for i in range(7):
      n=m.u16[0x0200CDD0+i*2]
      if not n:break
      actions.append(n)
     require(13 in actions,'Shop Drink trigger absent')
     for _ in range(actions.index(13)):g.press('DOWN',wait=20)
     g.capture('menu');images['menu.png']=digest((g.output/'menu.png').read_bytes());g.press('A',wait=0);captured=False
     for _ in range(1200):
      g.frames(1)
      if panel.reads and not panel.active and not captured:
       g.frames(8);pic=g.capture('message');images['message.png']=digest((g.output/'message.png').read_bytes())
       for d in draws:
        glyph,_=panel.glyph_record(d['code']);colour=m.u16[0x05000000+2*(16*d['bank']+d['foreground'])];rgb=tuple(((colour>>s)&31)*255//31 for s in (0,5,10))
        for y,line in enumerate(glyph['rows']):
         for x,bit in enumerate(line):require((pic.getpixel((d['origin'][0]+d['x']+x,d['origin'][1]+d['y']*16+y))==rgb)==(bit=='#'),'Shop final pixels differ');pixels+=1
       captured=True;g.press('B' if formatted else 'A',wait=0)
      if returns:break
     require(len(initial)==len(returns)==len(modals)==len(modal_returns)==len(panel.reads)==1 and len(formats)==int(bool(formatted)) and captured and not pending,'Shop route incomplete: '+repr((case,len(modals),len(modal_returns),len(panel.reads),len(returns))))
    require(g.snapshot().battery==fixture.battery and m.u32[hero+0x60]==gold_before,'Shop render probe changed gold/battery')
    results.append({'case':case,'owner':owner,'id':row['id'],'amount':amount,'inputs':g.inputs,'overrides':overrides,'formats':formats,'reads':panel.reads,'modals':modals,'modal_returns':modal_returns,'caller_guard_abi_preserved':True,'visible_pixels_checked':pixels,'images':images})
 report={'passed':True,'rom_sha256':digest(rom),'cases':results,'scope':'Original243C0 frame, three quote/half-price confirmations, three thank-you blocks and insufficient-funds block. Recorded controlled message-block dispatch; original modal choices, numeric colours,256-byte output and full caller/formatter/panel ABI, glyphs/pixels and battery checked. Prices17/0/999999/2147483647 are rendering bounds. Actual shop transactions, floor-item accounting and source468 remain separate.'}
 (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print('Dungeon shop:',len(results),'passed',flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,default=ROOT/'build/english');p.add_argument('--only');a=p.parse_args();run(a.source,a.only)
