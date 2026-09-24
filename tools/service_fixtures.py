"""Fresh native checkpoints for the current cumulative ROM; no state rewriting."""
import json
from tools.rom import ROOT,digest,require
from tools.emulator import Session,Snapshot,Debugger
from tools.verify_mansion import QuestTrace,attach
from tools.trace_mansion import finish

def dungeon(rom,build):
 out=ROOT/'build/services/current-dungeon';path=out/'ready'
 if path.with_suffix('.json').exists():
  snap=Snapshot.load(path)
  if snap.rom_sha256==digest(rom):return snap
 battery=(ROOT/'build/mansion/native/floor-five-native.sav').read_bytes()
 with Session(rom,out,initial_save=battery) as g:
  c=QuestTrace(g,'service-checkpoint',build,save_fixture=False)
  with Debugger(g,c.callback,max_events=30000) as d:
   attach(d,c);g.frames(600);g.press('START',wait=180);g.frames(204)
   finish(g,c,'rom.0006afe0','resume');g.press('A',wait=120)
   require(g.core.memory.u16[0x02005674]==6,'Service checkpoint failed to reach 6F')
  snap=g.snapshot();snap.save(path);g.capture('ready')
  (out/'inputs.json').write_text(json.dumps({'rom_sha256':digest(rom),'source_battery_sha256':digest(battery),'inputs':g.inputs},indent=2)+'\n')
 return snap
