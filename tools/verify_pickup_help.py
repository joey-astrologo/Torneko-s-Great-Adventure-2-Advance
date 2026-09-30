"""Original walking pickup dispatch and all tutorial item selectors."""
import argparse,json,struct
import mgba.log
from tools.rom import ROOT,digest,require
from tools.emulator import Session,Debugger
from tools.name_entry_playtest import position,MAP
from tools.verify_inventory_action_prototype import ActionCheck
from tools.verify_pickup_prototype import QUEUES
from tools.verify_service_ui import materialize,cstring
from tools.numeric_font import ALIASES

def run(root):
 mgba.log.silence();out=root/'pickup-help-validation';rom=(root/'torneko-2-english.gba').read_bytes();build=json.loads((root/'build.json').read_text());require(digest(rom)==build['output_sha256'],'Pickup help ROM differs')
 from tools import verify_player_status_prototype as status
 previous=status.OUT
 try:status.OUT=out;fixture=status.ready(rom,build)
 finally:status.OUT=previous
 tips={r['offset']+0x08000000:r for r in build['pickup_help']['entries']};items={i:r for r in tips.values() for i in r['item_ids']};pickups={r['offset']+0x08000000:r for r in build['pickup']['entries']};results=[]
 for ident,mode in [(i,11) for i in items]+[(1,0),(2,11)]:
  name=f'item-{ident}-mode-{mode}';print('Pickup help:',name,flush=True)
  with Session(rom,out/name) as g:
   g.restore(fixture);m=g.core.memory;overrides=[];entries=[];ends=[];drops=[];walks=[];checks=[];formats=[];pending={};mode_records=[];tabs=[];returning=False;restored=False;captures=[];steps=[];mode_before=m.u32[0x02003B6C];slot=0x0200DF28;actor=m.u32[0x02001624];prior_count=None;prior_gold=None
   count=lambda:sum(bool(m.u32[slot+i*120]&0x80000000) for i in range(20))
   def write(a,data):
    overrides.append(dict(address=a,before=bytes(m[a:a+len(data)]).hex(),after=data.hex()))
    for i,v in enumerate(data):m.u8[a+i]=v
   def callback(e):
    nonlocal restored
    a,r=e['address'],e['registers']
    if a==0x08024F12:drops.append(m.u32[r[0]+16])
    if not returning:return
    if a==0x080249DC:walks.append(e)
    if a==0x08024AD8:entries.append(e)
    if a==0x08024DAE:
     require(len(entries)==1,'Tutorial selector entered without pickup');write(0x02003B6C,struct.pack('<I',mode))
    if a==0x08024DB2:
     require(r[0]==mode,'Original tutorial mode load differs');mode_records.append(e)
     # Restore immediately after the original load; no other engine owner observes the controlled mode.
     write(0x02003B6C,struct.pack('<I',mode_before));restored=True
    if a==0x08000FB8 and r[1] in pickups:
     row=pickups[r[1]];ret=r[14]&~1;require(row['table_offset']==0x9C and ret==0x08024DA6 and not pending and not formats,'Unexpected tutorial pickup formatter');require(r[0]==r[13] and r[2]==r[13]+192,'Pickup output/item buffer owner differs')
     payload=materialize(bytes.fromhex(row['encoded_hex']),[r[2]],m);require(len(payload)<=row['maximum_bytes']<=192,'Pickup format too long');pending.update(regs=r,payload=payload,guard=bytes(m[r[0]+192:r[0]+256]),ret=ret)
     checks.append(ActionCheck(g,payload[:-1],0x08024DAF,192,pending['guard'][:16]))
    if pending and a==pending['ret']:
     old=pending['regs'];raw=pending['payload'];require(bytes(m[old[0]:old[0]+len(raw)])==raw and bytes(m[old[0]+192:old[0]+256])==pending['guard'] and r[4:12]==old[4:12] and r[13]==old[13],'Pickup formatter bytes/guard/ABI differ');formats.append(dict(hex=raw.hex(),bytes=len(raw),capacity=192));pending.clear()
    if a==0x0801588C and r[0] in tips:
     row=tips[r[0]];require(mode==11 and ident in row['item_ids'] and r[14]==0x08024E53 and len(checks)==1 and checks[-1].complete and checks[-1].returned,'Tutorial item dispatch differs');checks.append(ActionCheck(g,bytes.fromhex(row['encoded_hex'])[:-1],r[14],0,b''))
    if len(checks)==2 and a==0x0800231C:
     require(m.u32[r[1]]==1 and m.u8[r[5]+2]==0,'Tutorial control09 flag/line position differs')
     record=dict(glyph_index=len(checks[-1].draws),x=m.u8[r[5]+2],y=m.u8[r[5]+3],flag_address=r[1],flag_value=m.u32[r[1]])
     if not tabs or tabs[-1]!=record:tabs.append(record)
    if checks and not(checks[-1].complete and checks[-1].returned):checks[-1].callback(e)
    if a==0x08024E6A:
     old=entries[0]['registers'];require(r[4:12]==old[4:12] and r[13]==old[13] and r[1]==old[14] and r[0]==1,'Tutorial pickup owner ABI differs');require(restored and m.u32[0x02003B6C]==mode_before and count()==prior_count+1 and m.u32[actor+0x60]==prior_gold,'Tutorial pickup outcome differs');ends.append(e)
   addresses={0x08024F12,0x080249DC,0x08024AD8,0x08024DAE,0x08024DB2,0x08024E6A,0x08000FB8,0x08024DA6,0x0801588C,0x080158CE,0x08024E52,0x0800231C,0x08001BC4,0x08001C14,0x08001C68}
   with Debugger(g,callback,max_events=200000) as debug:
    for a in addresses:debug.breakpoint(a)
    g.press('B',hold=8,wait=30);g.press('A',wait=30);g.press('A',wait=30);actions=[]
    for i in range(7):
     n=m.u16[0x0200CDD0+i*2]
     if not n:break
     actions.append(n)
    require(7 in actions,'Drop unavailable')
    for _ in range(actions.index(7)):g.press('DOWN',wait=20)
    g.press('A',wait=180);require(len(drops)==1,'Native drop floor allocation differs');floor=drops[0];data=bytearray(m[floor:floor+120]);mapping=bytes(m[0x020013D0:0x020014D0]);struct.pack_into('<I',data,0,0xC8000000);data[4]=data[5]=1;data[8]=mapping.index(ident);data[24:]=bytes(96);write(floor,data);known=0x02003BAC+20*ident;write(known,struct.pack('<I',m.u32[known]|0x40000000))
    g.press('B',hold=8,wait=30);g.press('B',hold=8,wait=30);start=position(g);prior_count=count();prior_gold=m.u32[actor+0x60];g.capture('dropped');captures.append('dropped.png')
    for key,back,dx,dy in [('LEFT','RIGHT',-1,0),('RIGHT','LEFT',1,0),('UP','DOWN',0,-1),('DOWN','UP',0,1)]:
     if not m.u32[MAP+((start[0]+dx)*32+start[1]+dy)*28+20]&0x4000:continue
     g.press(key,wait=90);steps.append(dict(key=key,position=position(g)))
     if position(g)!=start:
      returning=True;g.press(back,wait=0);steps.append(dict(key=back));break
    seen=[];expected_checks=2 if mode==11 and ident in items else 1
    for frame in range(1200):
     g.frames(1)
     if checks:
      signature=[len(c.draws) for c in checks]
      if signature!=seen and checks[-1].draws:
       label=f'text-{frame:04d}';g.capture(label);captures.append(label+'.png');seen=signature
     if ends and len(checks)==expected_checks and all(c.complete and c.returned for c in checks):break
     if frame%60==59:g.press('A',hold=1,wait=0)
    require(len(entries)==len(ends)==len(walks)==len(formats)==len(mode_records)==1 and not pending and len(checks)==expected_checks and all(c.complete and c.returned for c in checks),f'Pickup tutorial incomplete: entries{len(entries)} ends{len(ends)} checks{[(c.complete,c.returned,len(c.draws),len(c.expected)) for c in checks]}')
    require(position(g)==start and walks[0]['registers'][14]==0x080324C7 and entries[0]['registers'][14]==0x08024AD1,'Pickup was not entered through real directional walking')
    for c in checks:
     require(all(0xF020<=d['code']<=0xF07E or d['code'] in ALIASES or 0x20<=d['code']<=0x7E for d in c.draws),f'Tutorial pickup retained an unclassified glyph: {[(hex(d["code"])) for d in c.draws if not(0xF020<=d["code"]<=0xF07E or d["code"] in ALIASES or 0x20<=d["code"]<=0x7E)]}')
    if expected_checks==2:require(len(tabs)==items[ident]['english'].count('\t'),f'Tutorial control09 count differs: {tabs}; first glyph {checks[-1].draws[:1]}')
    g.capture('result');captures.append('result.png')
   require(g.snapshot().battery==fixture.battery,'Pickup tutorial changed battery')
   results.append(dict(case=name,item_id=ident,mode=mode,overrides=overrides,mode_before=mode_before,mode_reads=mode_records,inputs=g.inputs,steps=steps,formats=formats,tabs=tabs,queues=[c.queued for c in checks],draws=[c.draws for c in checks],entry=entries[0],end=ends[0],inventory_before=prior_count,inventory_after=count(),gold_before=prior_gold,gold_after=m.u32[actor+0x60],images={p:digest((g.output/p).read_bytes()) for p in captures}))
 report=dict(passed=True,rom_sha256=digest(rom),fixture_state_sha256=digest(fixture.state),cases=results,scope='Real Drop and directional step-away/return enter original automatic pickup without PC/register overrides. Controlled floor identities and a mode11/0 load isolate all11 tutorial selectors, mode-off and unrelated-item negatives; mode is restored immediately after original load. Native item transfer, formatter bounds, queue/owner ABI, full glyph pixels,original09 flag writes and retained waits pass. No claim that these are naturally reached tutorial-mode routes or all dungeon messages.')
 (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print('Pickup help:',len(results),'passed')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--source',type=__import__('pathlib').Path,default=ROOT/'build/english');run(p.parse_args().source)
