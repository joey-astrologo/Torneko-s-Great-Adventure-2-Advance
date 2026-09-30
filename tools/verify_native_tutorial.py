"""Ordinary-input tutorial exploration; record every message and Japanese glyph lead."""
import argparse,json
from pathlib import Path
from collections import deque
import mgba.log
from tools.rom import ROOT,digest,require
from tools.emulator import Session,Snapshot,Debugger
from tools.name_entry_playtest import MAP,ACTORS,position,nearby_monsters,narrow_passage,walk_to_stairs
from tools.verify_service_ui import cstring
from tools.verify_inventory_action_prototype import ActionCheck
from tools.numeric_font import ALIASES

def run(root=ROOT/'build/english'):
 root=root.resolve()
 mgba.log.silence();out=root/'native-tutorial-validation';rom=(root/'torneko-2-english.gba').read_bytes();b=json.loads((root/'build.json').read_text());fixture_path=root/'dialogue-validation/yes/first-movement';fixture=Snapshot.load(fixture_path);require(fixture.rom_sha256==digest(rom)==b['output_sha256'],'Tutorial fixture/ROM differs');tips={e['offset']+0x08000000:e for e in b['pickup_help']['entries']};queues=[];pickups=[];checks=[];glyph_leads=[];steps=[];captures=[];lastqueue=None
 with Session(rom,out) as g:
  g.restore(fixture);m=g.core.memory;original_battery=fixture.battery
  def callback(e):
   nonlocal lastqueue
   a,r=e['address'],e['registers']
   if a==0x0801588C:
    raw=cstring(m,r[0]);record=dict(frame=e['frame'],source=r[0],return_pc=r[14],hex=raw.hex(),position=position(g),floor=m.u16[0x02005674],mode=m.u32[0x02003B6C]);queues.append(record);lastqueue=record
    if r[0] in tips:
     require(not checks or checks[-1].complete and checks[-1].returned,'Prior natural tutorial tip unfinished');checks.append(ActionCheck(g,bytes.fromhex(tips[r[0]]['encoded_hex'])[:-1],0x08024E53,0,b''));record['tip_id']=tips[r[0]]['id']
   if checks and not(checks[-1].complete and checks[-1].returned):checks[-1].callback(e)
   if a==0x08024AD8:
    x,y=position(g);p=m.u32[MAP+(x*32+y)*28+16];pickups.append(dict(frame=e['frame'],position=(x,y),floor=m.u16[0x02005674],mode=m.u32[0x02003B6C],item_id=m.u8[0x020013D0+m.u8[p+8]],item_hex=bytes(m[p:p+120]).hex(),caller=r[14]))
   if a==0x08001BC4 and r[1]>=0x80 and not(0xF020<=r[1]<=0xF07E or r[1] in ALIASES or r[1] in (0x8140,0x874E)):
    glyph_leads.append(dict(event=e,last_queue=lastqueue))
  def capture(label):g.capture(label);captures.append(label+'.png')
  def floor_items():
   items={}
   for x in range(56):
    for y in range(32):
     p=m.u32[MAP+(x*32+y)*28+16]
     if 0x02000000<=p<0x0203FF00 and m.u32[p]&0x80000000:items[x,y]=m.u8[0x020013D0+m.u8[p+8]]
   return items
  def path_to_items():
   start=position(g);targets=floor_items();q=deque([start]);previous={start:None}
   while q:
    point=q.popleft()
    if point in targets and point!=start:
     path=[];end=point
     while point!=start:path.append(point);point=previous[point]
     return path[::-1],targets[end]
    for dx,dy in ((1,0),(-1,0),(0,1),(0,-1)):
     x,y=point[0]+dx,point[1]+dy
     if not(0<=x<56 and 0<=y<32) or (x,y) in previous:continue
     flags=m.u32[MAP+(x*32+y)*28+20]
     if flags&0x4000 and not flags&0x20:previous[x,y]=point;q.append((x,y))
   return [],None
  def flush_tips():
   for k in range(12):
    if not checks or checks[-1].complete and checks[-1].returned:break
    capture(f'tip-{len(checks)}-page{k}');g.press('A',hold=1,wait=120)
   if checks:
    require(checks[-1].complete and checks[-1].returned,'Natural tutorial tip stalled')
    if f'tip-{len(checks)}-complete.png' not in captures:capture(f'tip-{len(checks)}-complete')
  def report(passed):
   data=dict(passed=passed,rom_sha256=digest(rom),fixture=str(fixture_path.relative_to(ROOT)),fixture_state_sha256=digest(fixture.state),opening_report_sha256=digest((fixture_path.parent/'report.json').read_bytes()),inputs=g.inputs,steps=steps,pickups=pickups,queues=queues,checks=[dict(queue=c.queued,complete=c.complete,returned=c.returned,draws=c.draws) for c in checks],japanese_glyph_leads=glyph_leads,images={p:digest((out/p).read_bytes()) for p in set(captures)},scope='Ordinary inputs from current-ROM fresh opening/name-entry route. Read-only map-guided walking and native attacks/acknowledgements; no ROM, RAM, register or save-state substitutions. Native floor-item identities, mode11 pickup tips and complete queued glyphs recorded. Arrival artwork is deferred and excluded from glyph audit; later dungeons and full game remain separate.');(out/'report.json').write_text(json.dumps(data,indent=2)+'\n')
  with Debugger(g,callback,max_events=500000) as debug:
   for a in (0x0801588C,0x080158CE,0x08024AD8,0x08024E52,0x08001BC4,0x08001C14,0x08001C68):debug.breakpoint(a)
   for floor in (1,2,3):
    require(m.u32[0x02003B6C]==11 and m.u16[0x02005674]==floor,'Tutorial floor differs');capture(f'floor-{floor}-start');print('Tutorial floor',floor,'items',floor_items(),flush=True)
    for tick in range(500):
     path,item_id=path_to_items()
     if not path:break
     before=position(g);actor=m.u32[ACTORS];hp=m.u16[actor+0x84];near=nearby_monsters(g)
     if near or hp<m.u16[actor+0x86]-2 and not nearby_monsters(g,3):key='A'
     else:key={(-1,0):'LEFT',(1,0):'RIGHT',(0,-1):'UP',(0,1):'DOWN'}[path[0][0]-before[0],path[0][1]-before[1]]
     count=len(pickups);g.press(key,wait=90);flush_tips()
     if position(g)==before and key!='A':g.press('A',wait=90);flush_tips()
     steps.append(dict(floor=floor,before=before,after=position(g),target=path[-1],item_id=item_id,key=key,nearby=near,hp_before=hp,hp_after=m.u16[actor+0x84]))
     if tick%30==29:print('Walk progress',steps[-1],flush=True)
     if len(pickups)>count:capture(f'floor-{floor}-pickup-{len(pickups)}');print('Natural pickup',pickups[-1]['item_id'],flush=True);report(False)
     require(m.u16[actor+0x84]>0,'Tutorial route defeated; evidence retained')
    else:
     g.snapshot().save(out/'stalled');report(False);raise ValueError('Tutorial item route stalled')
    steps.extend(walk_to_stairs(g));flush_tips();capture(f'floor-{floor}-stairs');g.press('A',wait=600)
    for k in range(6):g.press('A',wait=120)
   capture('after-tutorial');g.snapshot().save(out/'after-tutorial');require(not glyph_leads and len(pickups)==len(checks)==14 and {p['floor'] for p in pickups}=={1,2,3} and all(c.complete and c.returned for c in checks),'Fresh tutorial pickup coverage or English glyph audit failed');report(True)
  print('Natural pickups',len(pickups),'tips',len(checks),'Japanese glyph leads',len(glyph_leads),flush=True)
 
 from html import escape
 entries=''.join('<figure><img src="'+escape(p)+'"><figcaption>'+escape(p)+'</figcaption></figure>' for p in dict.fromkeys(captures))
 (out/'index.html').write_text('<!doctype html><meta charset="utf-8"><title>Torneko 2 native tutorial pickups</title><style>body{background:#182332;color:white;font:16px system-ui}figure{display:inline-block}img{width:480px;image-rendering:pixelated}</style><h1>Fresh tutorial: ordinary inputs</h1><p>14 pickups across three floors; all pickup tips completed. No Japanese glyph leads in monitored text. ROM '+digest(rom)+'. Arrival artwork is deferred. <a href="report.json">Exact inputs and scope</a></p>'+entries)

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--source',type=Path,default=ROOT/'build/english');run(p.parse_args().source)
