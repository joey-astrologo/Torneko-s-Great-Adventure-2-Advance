"""Explicitly controlled native story-reader checks, separate from quest gameplay."""
import json,mgba.log
from tools.rom import ROOT,digest,require
from tools.emulator import Session,Snapshot,Debugger
from tools.build_english import build_rom
from tools.verify_mansion import QuestTrace,attach
from tools.dialogue_checks import player_layout_cases
from tools.name_entry import HERO
OUT=ROOT/'build/english/holy-flame-text-validation'

def run():
 mgba.log.silence();rom,build=build_rom();fixture=Snapshot.load(ROOT/'build/english/mansion-validation/acquisition-entry');require(fixture.rom_sha256==digest(rom),'Story reader fixture is stale')
 targets=[r for r in build['dialogue']['entries'] if r['batch']=='holy-flame-quest'];results=[]
 for row in targets:
  payload=bytes.fromhex(row['encoded_hex']);names=player_layout_cases() if b'\x7e' in payload else [('native',None)]
  for label,name in names:
   with Session(rom,OUT/(row['id']+'-'+label)) as g:
    g.restore(fixture);original=int(g.core.cpu.gprs[1])&0xffffffff;target=0x8000000+row['rom_offset'];g.core.cpu.gprs[1]=target
    if name:
     for i,v in enumerate(name.ljust(16,b'\0')):g.core.memory.u8[HERO+i]=v
    c=QuestTrace(g,row['id']+'-'+label,build,save_fixture=False)
    with Debugger(g,c.callback,max_events=40000) as d:
     attach(d,c);g.frames(240);g.capture('page-0')
     for page in range(40):
      if row['id'] in c.completed and c.active is None:break
      g.press('A',wait=120);g.capture(f'page-{page+1}')
     require(c.completed==[row['id']] and c.active is None,'Controlled story source failed to finish')
    require(g.snapshot().battery==fixture.battery,'Controlled text display wrote save')
    results.append({'id':row['id'],'case':label,'controlled_register_override':{'r1_before':original,'r1_after':target},'controlled_name_hex':name.hex() if name else None,'reads':c.reads,'glyph_checks':c.glyph_checks,'centers':c.centers,'inputs':g.inputs})
 report={'passed':True,'rom_sha256':digest(rom),'source_fixture_sha256':digest(fixture.state),'sources':len(targets),'cases':results,'scope':'Controlled replacement of the source argument at an existing native two-row story-reader call. All holy-flame translations, paging, colors and player-name extremes checked. This is rendering evidence, not ordinary quest progression or branch-outcome coverage.'}
 (OUT/'report.json').write_text(json.dumps(report,indent=2)+'\n');print('Holy-flame text:',len(targets),'sources;',len(results),'controlled reader cases');return report
if __name__=='__main__':run()
