"""Ordinary English castle quest progression with adaptive dialogue completion."""
import json,mgba.log
from tools.rom import ROOT,digest,require
from tools.emulator import Session,Snapshot,Debugger
from tools.build_english import build_rom
from tools.verify_mansion import QuestTrace,attach
from tools.trace_mansion import finish
from tools.town_playtest import position
from tools.research_mansion import status
from tools.mansion_playtest import walk_to_stairs
OUT=ROOT/'build/english/holy-flame-validation'

def run():
 mgba.log.silence();rom,build=build_rom();recipe=json.loads((ROOT/'config/routes/storage-japanese.json').read_text());error=None
 with Session(rom,OUT) as g:
  g.restore(Snapshot.load(ROOT/'build/english/mansion-validation/family-1-1/morning'));c=QuestTrace(g,'holy-flame-ordinary',build,save_fixture=False)
  try:
   with Debugger(g,c.callback,max_events=350000) as d:
    attach(d,c)
    for i,a in enumerate(recipe['inputs'][:22],1):
     g.press(a['key'],hold=a['hold'],wait=a['released'])
     if i in (10,13,16,19,22):g.capture(f'approach-{i}');print('Approach',i,position(g),c.completed[-2:],flush=True)
    finish(g,c,'event-bank-1.6a74','accepted');g.press('A',wait=120);g.capture('accepted');g.snapshot().save(OUT/'accepted')
    for i,a in enumerate(recipe['inputs'][42:60],43):
     g.press(a['key'],hold=a['hold'],wait=a['released']);g.capture(f'entrance-{i}')
    print('Dungeon entry',status(g),flush=True);require(g.core.memory.u16[0x02005674]==1,'Castle dungeon entry missing')
    g.snapshot().save(OUT/'floor-1')
    for floor in range(1,7):
     g.snapshot().save(OUT/f'floor-{floor}');print('Walking floor',floor,status(g),flush=True)
     walk_to_stairs(g);g.capture(f'stairs-{floor}');g.press('A',wait=600)
    finish(g,c,'rom.00061998','flame');g.capture('flame');g.snapshot().save(OUT/'flame')
  except Exception as exc:
   error=str(exc)+(f': {exc.__cause__}' if exc.__cause__ else '');print('Quest research:',error,flush=True)
  g.capture('end');g.snapshot().save(OUT/'end')
  report={'passed':error is None,'error':error,'rom_sha256':digest(rom),'reads':c.reads,'choices':c.choices,'glyph_checks':c.glyph_checks,'inputs':g.inputs,'status':status(g)}
  (OUT/'progress.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
 if error:raise ValueError(error)
if __name__=='__main__':run()
