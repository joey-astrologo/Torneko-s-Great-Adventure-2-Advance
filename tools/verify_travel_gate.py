"""Original entry-refusal producer,128-byte scratch and native modal layouts."""
import argparse,json,struct
from pathlib import Path
import mgba.log
from tools.rom import ROOT,digest,require
from tools.emulator import Session,Debugger,ffi
from tools.dialogue_checks import TextChecks
from tools.verify_result_ui import native_format
def run(source):
 out=source/'travel-gate-validation';rom=(source/'torneko-2-english.gba').read_bytes();build=json.loads((source/'build.json').read_text());require(digest(rom)==build['output_sha256'],'Stale travel-gate ROM');mgba.log.silence()
 from tools import verify_player_status_prototype as status
 prior=status.OUT
 try:status.OUT=out;fixture=status.ready(rom,build)
 finally:status.OUT=prior
 rows={r['id'].split('.')[-1]:r for r in build['travel_gate']['entries']};results=[]
 for key,amount in [('limit',1),('limit',5),('limit',32767),('store',0),('sell',0),('level',None)]:
  for layout in ((0,2) if key!='level' else (2,)):
   case=f'{key}-{amount}-{layout}';print('Travel gate:',case,flush=True);row=rows[key];stop=0x5221E if key=='level' else 0x52188
   with Session(rom,out/case) as g:
    g.restore(fixture);m=g.core.memory;initial=[];returns=[];helpers=[];helper_returns=[];overrides=[];pending={};formats=[];modals=[];modal_returns=[];draws=[];images={};pixels=0;c=TextChecks(g,{})
    def write(at,data):
     overrides.append({'address':at,'before':bytes(m[at:at+len(data)]).hex(),'after':data.hex()})
     for i,v in enumerate(data):m.u8[at+i]=v
    def reg(e,i,v,reason):overrides.append({'event':e,'register':i,'after':v,'reason':reason});g.core.cpu.gprs[i]=v
    def jump(e,at,reason):overrides.append({'event':e,'pc_after':at+0x08000000,'reason':reason});require(g.core._core.writeRegister(g.core._core,b'pc',ffi.new('uint32_t*',at+0x08000000)),'Travel-gate redirect failed')
    item=bytearray(120);struct.pack_into('<I',item,0,0xC8000000);item[4:6]=b'\1\1';item[8]=bytes(m[0x020013D0:0x020014D0]).index(177);write(0x0200DF28,item);at=0x02003BAC+20*177;write(at,struct.pack('<I',m.u32[at]|0x40000000));hero=m.u32[0x02001624];gold=m.u32[hero+0x60]
    def callback(e):
     a,r=e['address'],e['registers']
     if a==0x08015848 and not initial:initial.append(e|{'guard':bytes(m[r[13]:r[13]+32]).hex(),'inventory':bytes(m[0x0200DF28:0x0200E888]).hex()});jump(e,0x52044,'Controlled Drink dispatch into full travel-owner frame.');return
     if not initial or returns:return
     if a==0x08052050:
      write(r[13]+8,struct.pack('<I',layout));reg(e,5,0,'Original successful travel-confirmation result for message-block setup.')
      if key=='level':reg(e,0,7,'Select native More Mystery level gate.');require(m.u16[hero+0x88]>1,'Native fixture level must exceed1')
      jump(e,0x521C6 if key=='level' else 0x5215E,'Execute original restriction producer/modal; menu routing and travel effects excluded.')
     if a==0x0804BCC0:helpers.append(e|{'guard':bytes(m[r[13]:r[13]+32]).hex()})
     if a==0x0804BCE2:reg(e,0,amount,'Controlled signed16-bit native item-limit result;32767 is the formatter boundary.')
     if a==0x0804BD0E:reg(e,0,1 if key=='store' else 0,'Select native storage-unlocked versus sale/discard branch.')
     if a==0x08000FB8 and r[1]==row['offset']+0x08000000:
      require(r[0]==0x0202F44C and r[14] in (0x0804BCF5,0x0804BD25,0x080521F7),'Travel-gate formatter/source differs');raw=native_format(bytes.fromhex(row['encoded_hex']),[amount] if key=='limit' else [],m);require(len(raw)<=row['maximum_bytes']<=128,'Travel-gate128-byte output exceeded');pending.update(regs=r,raw=raw,guard=bytes(m[r[0]+128:r[0]+144]))
     if pending and a==(pending['regs'][14]&~1):
      old=pending['regs'];raw=pending['raw'];require(bytes(m[old[0]:old[0]+len(raw)])==raw and bytes(m[old[0]+128:old[0]+144])==pending['guard'] and r[4:12]==old[4:12] and r[13]==old[13],'Travel-gate output/guard/ABI differs');c.resources[old[0]]=row|{'encoded_hex':raw.hex()};formats.append({'id':row['id'],'raw_hex':raw.hex(),'bytes':len(raw),'guard_abi_preserved':True});pending.clear()
     if a==0x0804BD28:
      old=helpers[-1]['registers'];require(r[4:12]==old[4:12] and r[13]==old[13] and r[0]==old[14] and bytes(m[r[13]:r[13]+32]).hex()==helpers[-1]['guard'],'Travel-gate producer caller ABI differs');helper_returns.append(e)
     if a==0x08015A34:require(r[0]==0x0202F44C and r[14]==stop+0x08000001,'Travel-gate native modal differs');modals.append(e)
     if a==0x08001BC4 and c.active:
      w=r[0];key_draw=(w,r[1],r[13],r[14],m.u8[w+2],m.u8[w+3])
      if not draws or draws[-1]['key']!=key_draw:draws.append({'key':key_draw,'code':r[1],'x':m.u8[w+2],'y':m.u8[w+3],'origin':[m.u8[w],m.u8[w+1]],'foreground':m.u8[0x020000C2],'bank':m.u16[m.u32[w+12]]>>12})
     if a in c.ADDRESSES:c.callback(e)
     if a==stop+0x08000000:
      old=modals[-1]['registers'];require(r[4:12]==old[4:12] and r[13]==old[13],'Travel-gate modal ABI differs');modal_returns.append(e);jump(e,0x522F4,'Native modal complete; skip subsequent travel/menu loop.')
     if a==0x08052302:
      old=initial[0]['registers'];require(r[4:12]==old[4:12] and r[13]==old[13] and r[1]==old[14] and bytes(m[r[13]:r[13]+32]).hex()==initial[0]['guard'],'Travel-gate owner caller ABI differs');returns.append(e)
    with Debugger(g,callback,max_events=120000) as d:
     for a in set(c.ADDRESSES)|{0x08015848,0x08052050,0x0804BCC0,0x0804BCE2,0x0804BD0E,0x08000FB8,0x0804BCF4,0x0804BD24,0x080521F6,0x0804BD28,0x08015A34,stop+0x08000000,0x08052302}:d.breakpoint(a)
     g.press('B',hold=8,wait=30);g.press('A',wait=30);g.press('A',wait=30);actions=[]
     for i in range(7):
      n=m.u16[0x0200CDD0+2*i]
      if not n:break
      actions.append(n)
     require(13 in actions,'Travel-gate Drink trigger missing')
     for _ in range(actions.index(13)):g.press('DOWN',wait=20)
     g.press('A',hold=1,wait=0);captured=False
     for _ in range(1200):
      if returns:break
      if c.reads and not c.active and not captured:
       g.frames(8);pic=g.capture('refusal');images['refusal.png']=digest((g.output/'refusal.png').read_bytes());captured=True
       for v in draws:
        glyph,_=c.glyph_record(v['code']);colour=m.u16[0x05000000+2*(16*v['bank']+v['foreground'])];rgb=tuple(((colour>>s)&31)*255//31 for s in (0,5,10))
        for y,line in enumerate(glyph['rows']):
         for x,bit in enumerate(line):require((pic.getpixel((v['origin'][0]+v['x']+x,v['origin'][1]+16*v['y']+y))==rgb)==(bit=='#'),'Travel-gate final pixels differ');pixels+=1
       g.press('A',hold=1,wait=0)
      else:g.frames(1)
     require(captured and len(returns)==len(c.reads)==len(formats)==len(modals)==len(modal_returns)==1 and len(helpers)==len(helper_returns)==int(key!='level') and not c.active and not pending,'Travel-gate route incomplete')
    require(m.u32[hero+0x60]==gold and bytes(m[0x0200DF28:0x0200E888]).hex()==initial[0]['inventory'] and g.snapshot().battery==fixture.battery,'Travel-gate text block changed inventory/gold/save')
    results.append({'case':case,'id':row['id'],'amount':amount,'layout':layout,'inputs':g.inputs,'overrides':overrides,'formats':formats,'reads':c.reads,'modals':modals,'modal_returns':modal_returns,'helpers':helpers,'caller_guard_abi_preserved':True,'visible_pixels_checked':pixels,'images':images})
 report={'passed':True,'rom_sha256':digest(rom),'cases':results,'scope':'Controlled Drink dispatch into complete52044 frame, original item/level restriction blocks and15A34 modals. Original4BCC0 producer clears/formats its128-byte global buffer and selects storage/sale branches; its signed16-bit limit result and storage flag are explicitly controlled. Both original message layouts, exact output/guard, native pixels and producer/modal/caller ABI pass. Level refusal executes actual fixture-level gate. Subsequent travel, progression and ordinary menu routing excluded. Inventory stable across message block; Drink consumes the trigger herb beforehand. Gold/battery unchanged.'};(out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print('Travel gate:',len(results),'passed')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--source',type=Path,default=ROOT/'build/english');run(p.parse_args().source)
