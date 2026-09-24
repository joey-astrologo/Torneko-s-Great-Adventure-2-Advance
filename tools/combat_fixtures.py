"""Reach core battle formatters using ordinary inputs on the current English ROM."""
import json
from tools.rom import ROOT,digest,require
from tools.emulator import Session,Debugger,Snapshot
from tools.service_fixtures import dungeon
from tools.mansion_playtest import walk_to_stairs
REQUIRED={'combat.19c','combat.1a0','combat.1b4','actor-getter'}

def create(rom,build,root):
 out=root/'native';path=out/'provenance.json'
 if path.exists():
  old=json.loads(path.read_text())
  if old['rom_sha256']==digest(rom) and REQUIRED<=set(old['saved_formats']):
   for ident in REQUIRED:require(Snapshot.load(out/ident).rom_sha256==digest(rom),'Combat fixture ROM differs')
   return old
 fixture=Snapshot.load(ROOT/'build/english/mansion-validation/battle-start') if 'dialogue' in build else Snapshot.load(root/'native/ready');require(fixture.rom_sha256==digest(rom),'Combat starting fixture stale');targets={r['offset']+0x8000000:r['id'] for r in build['combat']['entries']};saved=set();error=None
 with Session(rom,out) as g:
  g.restore(fixture)
  def callback(e):
   r=e['registers']
   if e['address']==0x08009acc:
    if r[0] and r[0]!=g.core.memory.u32[0x02001624] and 'actor-getter' not in saved:
     g.snapshot().save(out/'actor-getter');saved.add('actor-getter')
    return
   if r[1] in targets and targets[r[1]] not in saved:
    ident=targets[r[1]];g.snapshot().save(out/ident);saved.add(ident)
  with Debugger(g,callback,max_events=100000) as d:
   d.breakpoint(0x08000fb8);d.breakpoint(0x08009acc)
   try:
    if 'dialogue' in build:
     for _ in range(20):
      g.press('A',wait=240)
      if REQUIRED<=saved:break
    else:walk_to_stairs(g)
   except ValueError as exc:error=str(exc)
  g.capture('route-end')
  report={'rom_sha256':digest(rom),'starting_state_sha256':digest(fixture.state),'saved_formats':sorted(saved),'route_error':error,'inputs':g.inputs,'scope':'Ordinary combat from the current verified mansion battle checkpoint (or prototype cold continuation). Snapshot provenance only; a battle defeat does not invalidate reached formatter entries and is not claimed as a successful playthrough.'}
  path.write_text(json.dumps(report,indent=2)+'\n')
 require(REQUIRED<=saved,'Ordinary combat did not reach required formatter entries: '+repr(REQUIRED-saved))
 return report
