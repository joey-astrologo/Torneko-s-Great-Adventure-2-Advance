"""Original action prologue, both refusal blocks, formatter and complete modal."""
import argparse,json
from pathlib import Path
import mgba.log
from tools.rom import ROOT,digest,require
from tools.emulator import Session,Debugger,ffi
from tools.dialogue_checks import TextChecks,player_layout_cases
from tools.name_entry import HERO
from tools.compact_font import encode
from tools.verify_service_ui import materialize
def run(source=ROOT/'build/english'):
 out=source/'cannot-talk-validation';mgba.log.silence()
 rom=(source/'torneko-2-english.gba').read_bytes();build=json.loads((source/'build.json').read_text());require(digest(rom)==build['output_sha256'],'Stale talk ROM')
 from tools import verify_player_status_prototype as status
 prior=status.OUT
 try:status.OUT=out;fixture=status.ready(rom,build)
 finally:status.OUT=prior
 row=build['cannot_talk']['entries'][0];cases=[]
 configs=[(label,player,None) for label,player in player_layout_cases()]+[(label,None,raw) for label,raw in [('actor-width',encode('W'*31)),('actor-bytes',encode('i'*31)),('actor-colour',b'\x03\x05'+encode('W'*27)[:-1]+b'\x05\0')]]
 for branch,start,formatted in [('priest',0x23D4E,0x23D68),('companion',0x23DDE,0x23DF8)]:
  for label,player,actor_raw in configs:
   name=branch+'-'+label;print('Talk refusal:',name,flush=True)
   with Session(rom,out/name) as g:
    g.restore(fixture);m=g.core.memory;panel=TextChecks(g,{});initial=[];returns=[];formats=[];pending={};overrides=[];draws=[];images={};pixels=0;modals=[];modal_returns=[];dispatched=[]
    hero=m.u32[0x02001624];gold=m.u32[hero+0x60];inventory=bytes(m[0x0200DF28:0x0200E888])
    def write(a,data):
     overrides.append({'address':a,'before':bytes(m[a:a+len(data)]).hex(),'after':data.hex()})
     for i,v in enumerate(data):m.u8[a+i]=v
    def callback(e):
     nonlocal pending
     a,r=e['address'],e['registers']
     if a==0x08023C14 and not initial:
      initial.append(e|{'guard':bytes(m[r[13]:r[13]+32]).hex()})
      if player:write(HERO,player.ljust(16,b'\0'))
     if not initial or returns:return
     if a==0x08023CB6 and not dispatched:
      dispatched.append(e);overrides.append({'event':e,'pc_after':start+0x08000000,'reason':'Original action prologue and literal initialization complete; isolate each refusal block, excluding NPC/gating conditions.'});require(g.core._core.writeRegister(g.core._core,b'pc',ffi.new('uint32_t*',start+0x08000000)),'Talk dispatch failed')
     if a==0x08000FB8 and r[14]==formatted+0x08000001:
      require(r[1]==row['offset']+0x08000000 and r[0]==r[13]+8,'Talk native source/buffer differs');regs=list(r)
      if actor_raw:
       write(0x02008D08,actor_raw.ljust(64,b'\0'));g.core.cpu.gprs[2]=0x02008D08;regs[2]=0x02008D08;overrides.append({'event':e,'r2_after':0x02008D08,'reason':'Existing64byte actor scratch for formatter bounds; player16byte field is not widened.'})
      raw=materialize(bytes.fromhex(row['encoded_hex']),[regs[2]],m);require(len(raw)<=row['maximum_bytes']<=256,'Talk output exceeds capacity');pending={'regs':regs,'raw':raw,'guard':bytes(m[r[0]+256:r[0]+272]),'field':bytes(m[regs[2]:regs[2]+len(actor_raw or player or b'')])}
     if a==formatted+0x08000000 and pending:
      old=pending['regs'];p=old[0];raw=pending['raw'];require(bytes(m[p:p+len(raw)])==raw and bytes(m[p+256:p+272])==pending['guard'] and r[4:12]==old[4:12] and r[13]==old[13] and bytes(m[old[2]:old[2]+len(pending['field'])])==pending['field'],'Talk output/guard/ABI/field differs')
      formats.append({'id':row['id'],'hex':raw.hex(),'bytes':len(raw),'guard_abi_preserved':True});panel.resources[p]=row|{'encoded_hex':raw.hex(),'layout':{'pages':[[row['id']]]}};pending={}
     if a==0x08015A18:
      require(r[14]==0x08024375 and r[0] in panel.resources and r[2]==0,'Talk modal source/mode differs');modals.append(e)
     if a==0x08001750:draws[:]=[d for d in draws if d['window']!=r[0]]
     if a==0x08001BC4 and panel.active:
      w=r[0];key=(w,r[1],r[13],r[14],m.u8[w+2],m.u8[w+3])
      if not draws or draws[-1]['key']!=key:draws.append({'key':key,'window':w,'code':r[1],'x':m.u8[w+2],'y':m.u8[w+3],'origin':[m.u8[w],m.u8[w+1]],'foreground':m.u8[0x020000C2],'bank':m.u16[m.u32[w+12]]>>12})
     if a in panel.ADDRESSES:panel.callback(e)
     if a==0x08024374:
      old=modals[0]['registers'];require(r[4:12]==old[4:12] and r[13]==old[13],'Talk modal ABI differs');modal_returns.append(e)
     if a==0x080243BA:
      old=initial[0]['registers'];require(r[4:12]==old[4:12] and r[13]==old[13] and r[0]==old[14] and bytes(m[r[13]:r[13]+32]).hex()==initial[0]['guard'],'Talk caller ABI/guard differs');returns.append(e)
    with Debugger(g,callback,max_events=160000) as debug:
     for a in set(panel.ADDRESSES)|{0x08023C14,0x08023CB6,0x08000FB8,formatted+0x08000000,0x08015A18,0x08001750,0x08024374,0x080243BA}:debug.breakpoint(a)
     g.press('A',hold=1,wait=0);captured=False
     for _ in range(1200):
      g.frames(1)
      if panel.reads and not panel.active and not captured:
       g.frames(3);pic=g.capture('message');images['message.png']=digest((g.output/'message.png').read_bytes())
       for d in draws:
        glyph,_=panel.glyph_record(d['code']);colour=m.u16[0x05000000+2*(16*d['bank']+d['foreground'])];rgb=tuple(((colour>>s)&31)*255//31 for s in (0,5,10))
        for y,line in enumerate(glyph['rows']):
         for x,bit in enumerate(line):require((pic.getpixel((d['origin'][0]+d['x']+x,d['origin'][1]+d['y']*16+y))==rgb)==(bit=='#'),'Talk final pixels differ');pixels+=1
       captured=True;g.press('B',hold=1,wait=0)
      if captured and not returns and _%20==0:g.press('B',hold=1,wait=0)
      if returns:break
     require(len(initial)==len(returns)==len(modals)==len(modal_returns)==len(panel.reads)==len(formats)==len(dispatched)==1 and captured and not pending,'Talk route incomplete: '+repr((name,len(dispatched),len(formats),len(modals),len(modal_returns),len(panel.reads),len(returns))))
    require(m.u32[hero+0x60]==gold and bytes(m[0x0200DF28:0x0200E888])==inventory and g.snapshot().battery==fixture.battery,'Talk changed inventory/gold/battery')
    cases.append({'case':name,'branch':branch,'field':label,'id':row['id'],'inputs':g.inputs,'overrides':overrides,'formats':formats,'reads':panel.reads,'modals':modals,'modal_returns':modal_returns,'caller_guard_abi_preserved':True,'visible_pixels_checked':pixels,'images':images})
 report={'passed':True,'rom_sha256':digest(rom),'cases':cases,'scope':'Ordinary A enters original23C14 prologue, then explicit controlled jump after literal initialization selects each original talk refusal block. Native player getter, formatter, modal and full epilogue execute. Three player-name profiles and three actor formatter bounds per block;256byte output, field/guard/ABI, full visible pixels and unchanged inventory/gold/battery. Natural NPC proximity, state/interaction gates and successful conversations excluded.'}
 (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print('Talk refusals:',len(cases),'passed')

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,default=ROOT/'build/english');run(p.parse_args().source)
