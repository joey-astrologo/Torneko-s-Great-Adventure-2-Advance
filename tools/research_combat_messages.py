"""Observe additional combat formats through ordinary attacks on a native route."""
import json,mgba.log
from tools.rom import ROOT,digest,require
from tools.emulator import Session,Snapshot,Debugger
from tools.extract_shared_text import extract
from tools.verify_service_ui import cstring
from tools.mansion_playtest import walk_to_stairs

def run():
 mgba.log.silence();out=ROOT/'build/shared-text/native-combat'
 rom=(ROOT/'build/english/torneko-2-english.gba').read_bytes()
 fixture=Snapshot.load(ROOT/'build/english/mansion-validation/battle-start')
 require(fixture.rom_sha256==digest(rom),'Current combat checkpoint is stale')
 sources={r['source']['offset']+0x8000000:r for r in extract()['entries']};formats={};queues=[];miss=False
 with Session(rom,out) as g:
  g.restore(fixture)
  def callback(event):
   nonlocal miss
   a,r=event['address'],event['registers'];m=g.core.memory
   if a==0x08000fb8 and r[1] in sources:
    source=sources[r[1]];key=f"shared.{source['table_offset']:03x}"
    if key not in formats:
     formats[key]={'source':source,'frame':event['frame'],'arguments':r[:4],
                   'stack':r[13],'return':r[14],'stack_argument_hex':bytes(m[r[13]:r[13]+24]).hex()}
     g.snapshot().save(out/key)
    if source['table_offset']==0x208:miss=True
   if a==0x0801588c:
    raw=cstring(m,r[0],512)
    queues.append({'frame':event['frame'],'pointer':r[0],'return':r[14],'raw_hex':raw.hex()})
  with Debugger(g,callback,max_events=30000) as debug:
   debug.breakpoint(0x08000fb8);debug.breakpoint(0x0801588c)
   for step in range(20):
    g.press('A',wait=240)
    if miss:break
   navigation_error=None
   if not miss:
    try:walk_to_stairs(g)
    except ValueError as exc:navigation_error=str(exc)
  g.capture('end')
  report={'rom_sha256':digest(rom),'source_fixture_sha256':digest(fixture.state),
          'formats':formats,'queues':queues,'miss_observed':miss,'navigation_error':navigation_error,'inputs':g.inputs,
          'scope':'Ordinary attacks and existing read-only navigation decisions from the current native mansion battle checkpoint. No actor, inventory, RNG or quest-state overrides. A defeat is not a completed playthrough; captures only establish reached formatter contexts.'}
  (out/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
 print('Additional combat formats:',list(formats),'miss observed:',miss);return report

if __name__=='__main__':run()
