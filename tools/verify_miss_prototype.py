"""Isolated one-line miss prototype with an ordinarily reached formatter context."""
import argparse,json,mgba.log
from tools.rom import ROOT,digest,require
from tools.emulator import Session,Snapshot,Debugger
from tools.compact_font import encode,measure
from tools.extract_shared_text import extract
from tools.verify_mansion import QuestTrace,attach
from tools.trace_mansion import finish
from tools.name_entry_playtest import MAP
from tools.mansion_playtest import walk_to_stairs
from tools.verify_combat_prototype import CombatCheck
from tools.verify_service_ui import materialize
from tools.dialogue_checks import player_layout_cases

OUT=ROOT/'build/combat-miss-prototype'

def candidate():
 import tools.combat_text as combat
 from tools.build_english import build_rom
 catalog=json.loads(combat.CATALOG.read_text())
 src=next(r for r in extract()['entries'] if r['table_offset']==0x208)['source']
 if not any(r['id']=='combat.208' for r in catalog['entries']):catalog['entries'].append({'id':'combat.208','table_offset':0x208,'source':src,
  'english':'{actor} misses!','status':'reviewed',
  'review':'T2 source says the named actor misses an attack. Complete one-line English; widest supported actor/name/level fits without removing meaning. Native 0800BCBC consumers at C044 and C5B2 use its 256-byte stack message region.'})
 OUT.mkdir(parents=True,exist_ok=True);path=OUT/'combat-review.json';path.write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n')
 prior=combat.CATALOG
 try:combat.CATALOG=path;rom,build=build_rom()
 finally:combat.CATALOG=prior
 (OUT/'game.gba').write_bytes(rom);(OUT/'build.json').write_text(json.dumps(build,indent=2)+'\n')
 return rom,build

def context(rom,build):
 path=OUT/'native/miss';meta=OUT/'native/provenance.json'
 if path.with_suffix('.json').exists() and meta.exists() and (OUT/'native/player-attack-entry.json').exists():
  snap=Snapshot.load(path)
  if snap.rom_sha256==digest(rom):return snap
 target=next(r for r in build['combat']['entries'] if r['id']=='combat.208')['offset']+0x8000000
 saved=[];attacks=[];error=None;battery=(ROOT/'build/mansion/native/floor-five-native.sav').read_bytes()
 with Session(rom,OUT/'native',initial_save=battery) as g:
  c=QuestTrace(g,'miss-native-route',build,save_fixture=False)
  def callback(event):
   c.callback(event);r=event['registers']
   if event['address']==0x0800bcbc and r[2]==0 and not attacks:
    g.snapshot().save(OUT/'native/player-attack-entry');attacks.append({'frame':event['frame'],'arguments':r[:4]})
   if event['address']==0x08000fb8 and r[1]==target and not saved:
    g.snapshot().save(path);saved.append({'frame':event['frame'],'registers':r})
  with Debugger(g,callback,max_events=150000) as d:
   attach(d,c);d.breakpoint(0x08000fb8);d.breakpoint(0x0800bcbc)
   g.frames(600);g.press('START',wait=180);g.frames(204)
   finish(g,c,'rom.0006afe0','floor-six-voice');g.press('A',wait=120)
   targets=[(x,y+1) for x in range(56) for y in range(31) if g.core.memory.u32[MAP+(x*32+y)*28+20]&0x800000]
   require(len(targets)==1,'Ambiguous native quest-room entrance')
   walk_to_stairs(g,targets[0]);g.press('UP',wait=240)
   finish(g,c,'rom.00061a08','imp-introduction');g.press('A',wait=120)
   for _ in range(20):g.press('A',wait=240)
   if not saved:
    try:walk_to_stairs(g)
    except ValueError as exc:error=str(exc)
  g.capture('end');meta.write_text(json.dumps({'rom_sha256':digest(rom),'source_save_sha256':digest(battery),
   'saved':saved,'player_attacks':attacks,'navigation_error':error,'inputs':g.inputs,
   'scope':'Native cold resume, ordinary quest-room approach, attacks and navigation. No RNG, actor or quest overrides. A later defeat does not claim quest completion.'},indent=2)+'\n')
 require(saved,'Native route did not reach the miss formatter');return Snapshot.load(path)

def player_miss_context(rom,build):
 fixture=Snapshot.load(OUT/'native/player-attack-entry');target=next(r for r in build['combat']['entries'] if r['id']=='combat.208')['offset']+0x8000000
 saved=[];path=OUT/'native/miss-player'
 with Session(rom,OUT/'player-branch') as g:
  g.restore(fixture);original=int(g.core.cpu.gprs[3]);g.core.cpu.gprs[3]=100
  def callback(event):
   r=event['registers']
   if r[1]==target and not saved:
    require(r[14]==0x0800c049,'Unexpected player miss call site')
    g.snapshot().save(path);saved.append({'frame':event['frame'],'registers':r})
  with Debugger(g,callback,max_events=10000) as d:
   d.breakpoint(0x08000fb8);d.run_until(lambda _:bool(saved),max_steps=1000000)
  (OUT/'player-branch/provenance.json').write_text(json.dumps({'rom_sha256':digest(rom),'source_state_sha256':digest(fixture.state),
   'controlled_argument':{'register':'r3','original':original,'replacement':100},'saved':saved,
   'scope':'Controlled miss probability at an ordinarily reached attack resolver entry. Original RNG and native miss branch execute; this does not claim a naturally rolled player miss.'},indent=2)+'\n')
 return Snapshot.load(path)

def run(cumulative=False):
 global OUT
 mgba.log.silence()
 if cumulative:
  OUT=ROOT/'build/english/combat-validation/misses'
  OUT.mkdir(parents=True,exist_ok=True)
  rom=(ROOT/'build/english/torneko-2-english.gba').read_bytes()
  build=json.loads((ROOT/'build/english/build.json').read_text())
  require(build['output_sha256']==digest(rom),'Cumulative miss build is stale')
 else:rom,build=candidate()
 fixture=context(rom,build)
 player_fixture=player_miss_context(rom,build)
 row=next(r for r in build['combat']['entries'] if r['id']=='combat.208');results=[]
 names=[(str(r['id']),encode(r['english'])) for r in build['monsters']['entries']]
 names.extend([('wide-level',encode('Crack-billed platypunk Lv32767'))]+[(label,name) for label,name in player_layout_cases()])
 cases=[(label,name,fixture) for label,name in names]+[('player-branch-'+label,name,player_fixture) for label,name in names[-4:]]
 for label,name,selected_fixture in cases:
  with Session(rom,OUT/label) as g:
   g.restore(selected_fixture);m=g.core.memory;r=g.core.cpu.gprs;dest=int(r[0]);formatter_return=int(r[14])
   require(formatter_return in (0x0800c049,0x0800c5b7),'Unowned miss formatter return')
   queue_return=0x0800c051 if formatter_return==0x0800c049 else 0x0800c5bf
   require(len(name)<=64,'Miss actor exceeds original name scratch')
   for i,v in enumerate(name.ljust(64,b'\0')):m.u8[0x02008d08+i]=v
   r[2]=0x02008d08;expected=materialize(bytes.fromhex(row['encoded_hex']),[0x02008d08],m)[:-1]
   c=CombatCheck(g,expected,queue_return,256,bytes(m[dest+256:dest+272]))
   with Debugger(g,c.callback,max_events=20000) as d:
    for a in (0x0801588c,0x080158ce,0x08001bc4,0x08001c14,0x08001c68,queue_return&~1):d.breakpoint(a)
    for _ in range(180):
     g.frames(1)
     if c.complete and c.returned:break
    require(c.complete and c.returned and c.queued['one_line'],'Miss must render completely on one line')
    g.capture('rendered')
   results.append({'case':label,'name_hex':name.hex(),'formatter_return':formatter_return,'queue':c.queued,'glyphs':len(c.draws),'guard_and_abi_preserved':True})
 report={'passed':True,'rom_sha256':digest(rom),'cases':results,'scope':('Cumulative ROM display checks. ' if cumulative else 'Isolated candidate, not cumulative acceptance. ')+'Enemy miss formatter reached with ordinary inputs; a controlled probability argument exercises the second player-miss caller. Controlled names cover all 141 actor names, maximum level suffix and player-name extremes. One line, pixels, exact queue, buffer, ABI and unchanged formatting-time actor/inventory state checked.'}
 (OUT/'report.json').write_text(json.dumps(report,indent=2)+'\n');print('One-line miss cases:',len(results));return report

if __name__=='__main__':
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--cumulative',action='store_true');run(parser.parse_args().cumulative)
