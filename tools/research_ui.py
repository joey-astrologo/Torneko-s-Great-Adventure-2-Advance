"""Original-ROM discovery of dungeon options and their child screens."""
import json
import mgba.log
from tools.emulator import Session,Snapshot,Debugger
from tools.audit_menu_layouts import Observer
from tools.rom import ROOT,load_base,digest

OUT=ROOT/'build/services/ui-original'
def run():
 mgba.log.silence();rom=load_base();fixture=Snapshot.load(ROOT/'build/mansion/native/quest-room-entrance');rows=[]
 for name,index in [('controls',0),('sound',1),('auto-turn',2),('map',3),('suspend',4),('sleep',5)]:
  with Session(rom,OUT/name) as game:
   game.restore(fixture);o=Observer(game);formats=[]
   def cb(e):
    o.callback(e)
    if e['address']==0x08000fb8:
     r=e['registers'];formats.append({'frame':e['frame'],'dest':r[0],'template':r[1],'args':r[2:4],'caller':r[14]})
   with Debugger(game,cb,max_events=60000) as d:
    for a in o.ADDRESSES+(0x08000fb8,):d.breakpoint(a)
    game.press('B',hold=8,wait=120);game.press('DOWN',wait=30);game.press('DOWN',wait=30);game.press('A',wait=120)
    game.capture('options')
    for _ in range(index):game.press('DOWN',wait=20)
    game.press('A',wait=120);game.capture('selected')
    if index in (1,2,3):game.press('RIGHT',wait=60);game.capture('changed')
    game.press('B',wait=120);game.capture('cancel')
   rows.append({'case':name,'reads':o.reads,'creates':o.creates,'callers':o.callers,'formats':formats,'inputs':game.inputs})
 (OUT/'report.json').write_text(json.dumps({'source_rom_sha256':digest(rom),'cases':rows},ensure_ascii=False,indent=2)+'\n')
 for row in rows:
  print(row['case'])
  for r in row['reads'][11:]:print(hex(r['source']),r['window_width'],r['initial_x'],repr(r['text']))
if __name__=='__main__':run()
