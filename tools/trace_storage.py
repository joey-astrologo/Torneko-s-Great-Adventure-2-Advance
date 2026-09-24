"""Reproduce the quest-earned repaired warehouse and native book save."""
import json,mgba.log
from tools.emulator import Session,Snapshot,Debugger
from tools.rom import ROOT,load_base,digest,require
from tools.trace_mansion import SourceTrace
from tools.holy_flame_playtest import items
from tools.town_playtest import position
OUT=ROOT/'build/services/storage-native'
RECIPE=ROOT/'config/routes/storage-japanese.json'

def run():
 mgba.log.silence();rom=load_base();recipe=json.loads(RECIPE.read_text());saved=[]
 require(recipe['source_rom_sha256']==digest(rom),'Storage route base differs')
 with Session(rom,OUT) as g:
  g.restore(Snapshot.load(ROOT/recipe['start_fixture']));c=SourceTrace(g,'storage-unlock')
  require(g.core.frame_counter==recipe['start_frame'],'Storage route start timing differs')
  def cb(e):
   c.callback(e)
   if e['address']==0x08015354:saved.append(e['frame'])
  milestones={s['end_input']:s['name'] for s in recipe['segments']}
  with Debugger(g,cb,max_events=100000) as d:
   for a in c.ADDRESSES+(0x08015354,):d.breakpoint(a)
   for index,action in enumerate(recipe['inputs'],1):
    if 'frames' in action:g.frames(action['frames'])
    else:g.press(action.get('keys',action.get('key')),hold=action['hold'],wait=action['released'])
    if index in milestones:
     name=milestones[index];g.capture(name);print('Storage route:',name,flush=True)
  require(position(g)==(288,224) and [i for _,i,_ in items(g)]==[204,51],'Storage route did not retain naturally carried items')
  battery=g.snapshot().battery
  require(saved and digest(battery)==recipe['expected_save_sha256'],'Native storage save differs from recorded route')
  (OUT/'storage-ready.sav').write_bytes(battery);g.snapshot().save(OUT/'saved');g.capture('saved')
  report={'passed':True,'source_rom_sha256':digest(rom),'recipe_sha256':digest(RECIPE.read_bytes()),
          'save_sha256':digest(battery),'native_save_frames':saved,'inputs':g.inputs,
          'entries':list({r['id']:r for r in c.entries}.values()),'reads':c.reads,'scope':recipe['scope']}
  (OUT/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
 print('Native repaired-storage save reproduced')
if __name__=='__main__':run()
