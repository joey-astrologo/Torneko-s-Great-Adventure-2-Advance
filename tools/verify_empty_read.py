"""Native Drop/Floor/Read with no carried items; no execution redirects."""
import argparse,json,struct
from pathlib import Path
import mgba.log
from tools.rom import ROOT,digest,require
from tools.emulator import Session,Debugger
from tools.verify_inventory_action_prototype import ActionCheck

def run(source):
 out=source/'empty-read-validation';rom=(source/'torneko-2-english.gba').read_bytes();build=json.loads((source/'build.json').read_text());require(digest(rom)==build['output_sha256'],'Stale empty-read ROM');mgba.log.silence()
 from tools import verify_player_status_prototype as status
 prior=status.OUT
 try:status.OUT=out;fixture=status.ready(rom,build)
 finally:status.OUT=prior
 row=build['empty_read']['entries'][0];results=[]
 for ident in (117,128,132,133):
  case=str(ident);print('Empty read:',case,flush=True)
  with Session(rom,out/case) as g:
   g.restore(fixture);m=g.core.memory;overrides=[];drops=[];initial=[];returns=[];checks=[];colours=[];images={};pixels=0;reading=False
   def write(at,data):
    overrides.append({'address':at,'before':bytes(m[at:at+len(data)]).hex(),'after':data.hex()})
    for i,v in enumerate(data):m.u8[at+i]=v
   item=bytearray(120);struct.pack_into('<I',item,0,0xC8000000);item[5]=1;item[8]=bytes(m[0x020013D0:0x020014D0]).index(ident);write(0x0200DF28,item)
   at=0x02003BAC+20*ident;write(at,struct.pack('<I',m.u32[at]|0x40000000));hero=m.u32[0x02001624];gold=m.u32[hero+0x60]
   def callback(e):
    a,r=e['address'],e['registers']
    if a==0x08024F12:drops.append(m.u32[r[0]+16])
    if not reading:return
    if a==0x080175B4:initial.append(e|{'guard':bytes(m[r[13]:r[13]+32]).hex(),'command':bytes(m[r[0]:r[0]+8]).hex()})
    if a==0x0801588C and r[0]==row['offset']+0x08000000:
     require(r[14]==0x08017639 and not checks,'Empty-read queue owner differs');checks.append(ActionCheck(g,bytes.fromhex(row['encoded_hex'])[:-1],r[14],0,b''))
    if checks and not (checks[0].complete and checks[0].returned):
     if a==0x08001C14 and checks[0].pending_glyph:
      w=r[5];bank=m.u16[m.u32[w+12]]>>12;v=m.u16[0x05000000+2*(bank*16+m.u8[0x020000C2])];colours.append(tuple(((v>>s)&31)*255//31 for s in (0,5,10)))
     checks[0].callback(e)
    if a==0x0801775A:
     old=initial[-1]['registers'];require(r[4:12]==old[4:12] and r[13]==old[13] and r[1]==old[14] and bytes(m[r[13]:r[13]+32]).hex()==initial[-1]['guard'],'Empty-read caller ABI differs');require(m.u8[old[0]+1]==1,'Empty-read native command did not cancel the read');returns.append(e)
   def select(action):
    actions=[]
    for i in range(7):
     n=m.u16[0x0200CDD0+2*i]
     if not n:break
     actions.append(n&127)
    require(action in actions,'Empty-read action absent: '+repr((action,actions)))
    for _ in range(actions.index(action)):g.press('DOWN',wait=20)
   with Debugger(g,callback,max_events=100000) as d:
    for a in (0x08024F12,0x080175B4,0x0801775A,0x0801588C,0x080158CE,0x08001BC4,0x08001C14,0x08001C68,0x08017638):d.breakpoint(a)
    g.press('B',hold=8,wait=30);g.press('A',wait=30);g.press('A',wait=30);select(7);g.press('A',wait=180);require(len(drops)==1,'Native drop missing')
    floor=drops[0];floor_before=bytes(m[floor:floor+120])
    for i in range(20):write(0x0200DF28+i*120,bytes(120))
    g.press('B',hold=8,wait=60);g.press('DOWN',wait=30);g.press('A',wait=60);select(12);g.capture('floor-read');images['floor-read.png']=digest((g.output/'floor-read.png').read_bytes());reading=True;g.press('A',hold=1,wait=0)
    for _ in range(600):
     if returns and checks and checks[0].complete and checks[0].returned:break
     g.frames(1)
    require(len(initial)==len(returns)==len(checks)==1 and checks[0].complete and checks[0].returned,'Empty-read native route incomplete')
    g.frames(3);pic=g.capture('refusal');images['refusal.png']=digest((g.output/'refusal.png').read_bytes());c=checks[0];require(len(c.draws)==len(colours),'Empty-read colour observations differ')
    for draw,colour in zip(c.draws,colours):
     glyph=c.font['glyphs'][chr(draw['code']&255)]
     for y,line in enumerate(glyph['rows']):
      for x,bit in enumerate(line):require((pic.getpixel((m.u8[c.window]+draw['x']+x,m.u8[c.window+1]+draw['y']*16+y))==colour)==(bit=='#'),'Empty-read pixels differ');pixels+=1
   require(bytes(m[floor:floor+120])==floor_before and all(not m.u32[0x0200DF28+i*120]&0x80000000 for i in range(20)),'Refused read consumed floor scroll or changed inventory')
   require(m.u32[hero+0x60]==gold and g.snapshot().battery==fixture.battery,'Refused read changed gold/save')
   results.append({'case':case,'item_id':ident,'inputs':g.inputs,'overrides':overrides,'initial':initial,'returns':returns,'queue':checks[0].queued,'caller_guard_abi_preserved':True,'native_refusal_preserves_floor_scroll':True,'visible_pixels_checked':pixels,'images':images})
 report={'passed':True,'rom_sha256':digest(rom),'cases':results,'scope':'Four controlled known scroll IDs and empty carried inventory after native Drop. Ordinary Floor/Read, complete175B4 gates/refusal and command cancellation execute without PC/register changes. ROM source, queue/caller ABI, one-line pixels and unchanged floor scroll/gold/battery checked. Natural acquisition and other action states remain separate.'};(out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print('Empty read:',len(results),'passed')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--source',type=Path,default=ROOT/'build/english');run(p.parse_args().source)
