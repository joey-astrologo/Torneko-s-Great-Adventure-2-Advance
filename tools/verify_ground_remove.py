"""Native Remove entry and its original floor-index fragment queue."""
import argparse,json,struct
from pathlib import Path
import mgba.log
from tools.rom import ROOT,digest,require
from tools.emulator import Session,Debugger,ffi
from tools.verify_inventory_action_prototype import ActionCheck
from tools import verify_player_status_prototype as status

def run(source):
 out=source/'ground-remove-validation';rom=(source/'torneko-2-english.gba').read_bytes();build=json.loads((source/'build.json').read_text());require(digest(rom)==build['output_sha256'],'Ground Remove ROM differs');mgba.log.silence();prior=status.OUT
 try:status.OUT=out;fixture=status.ready(rom,build)
 finally:status.OUT=prior
 row=build['ground_remove']['entries'][0];target=row['offset']+0x08000000;raw=bytes.fromhex(row['encoded_hex']);cases=[]
 for value in (50,255):
  case='floor-index-'+str(value);print('Ground Remove:',case,flush=True)
  with Session(rom,out/case) as g:
   g.restore(fixture);m=g.core.memory;overrides=[];entries=[];returns=[];queues=[];c=ActionCheck(g,raw[:-1],0x0802492F,0,b'')
   def write(at,data):
    overrides.append(dict(address=at,before=bytes(m[at:at+len(data)]).hex(),after=data.hex()))
    for i,v in enumerate(data):m.u8[at+i]=v
   for i in range(20):
    at=0x0200DF28+i*120
    if m.u32[at]&0x800000:write(at,struct.pack('<I',m.u32[at]&~0x800000))
   item=bytearray(120);struct.pack_into('<I',item,0,0xC8800000);item[4]=item[5]=1;item[8]=bytes(m[0x020013D0:0x020014D0]).index(1);write(0x0200DF28,item);at=0x02003BAC+20;write(at,struct.pack('<I',m.u32[at]|0x40000000));inventory=bytes(m[0x0200DF28:0x0200E888]);hero=m.u32[0x02001624];gold=m.u32[hero+0x60]
   def cb(e):
    a,r=e['address'],e['registers']
    if a==0x08024918:entries.append(e|dict(guard=bytes(m[r[13]:r[13]+32]).hex()))
    if entries and not returns:
     if a==0x0802491E:overrides.append(dict(event=e,register=0,after=value,reason='Controlled compared command byte; execute native >49 predicate'));g.core.cpu.gprs[0]=value
     if a==0x0801588C:require(r[0]==target and r[1]==1 and r[14]==0x0802492F,'Wrong original floor-fragment queue');queues.append(e)
     c.callback(e)
     if a==0x080249D4:
      old=entries[0]['registers'];require(r[4:12]==old[4:12] and r[13]==old[13] and r[0]==old[14] and bytes(m[r[13]:r[13]+32]).hex()==entries[0]['guard'],'Ground Remove owner ABI/guard differs');returns.append(e)
    elif entries and not c.complete:c.callback(e)
   with Debugger(g,cb,max_events=100000) as d:
    for a in (0x08024918,0x0802491E,0x080249D4,0x0801588C,0x080158CE,0x0802492E,0x08001BC4,0x08001C14,0x08001C68):d.breakpoint(a)
    g.press('B',hold=8,wait=30);g.press('A',wait=30);g.press('A',wait=30);actions=[]
    for i in range(7):
     a=m.u16[0x0200CDD0+i*2]
     if not a:break
     actions.append(a)
    require(6 in actions,'Native Remove action absent')
    for _ in range(actions.index(6)):g.press('DOWN',wait=20)
    g.press('A',wait=0)
    for _ in range(360):
     if returns and c.complete and c.returned:break
     g.frames(1)
    require(len(entries)==len(returns)==len(queues)==1 and c.complete and c.returned and c.queued['one_line'],'Ground Remove queue/render incomplete');g.capture('result')
   require(bytes(m[0x0200DF28:0x0200E888])==inventory and m.u32[hero+0x60]==gold and g.snapshot().battery==fixture.battery,'Ground Remove changed items/gold/save');cases.append(dict(case=case,command_byte=value,inputs=g.inputs,overrides=overrides,entries=entries,returns=returns,queues=queues,queue=c.queued,glyphs=len(c.draws),draws=c.draws,caller_guard_abi_preserved=True,inventory_gold_save_preserved=True,images={'result.png':digest((g.output/'result.png').read_bytes())}))
 report=dict(passed=True,rom_sha256=digest(rom),cases=cases,scope='Ordinary native item-action selection with controlled equipped item; original Remove owner and >49 branch, compared values50/255. Owned immutable source and mode1 queue, complete one-line glyph sequence/bitmap/cursor checks, queue/owner ABI/guard and unchanged items/gold/battery. Original fragment meaning preserved. Natural availability of Remove for floor indices excluded.');(out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print('Ground Remove:',len(cases),'passed')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--source',type=Path,default=ROOT/'build/english');run(p.parse_args().source)
