"""Repaired storage from a real quest-earned save; ordinary transactions only."""
import json,mgba.log
from tools.rom import ROOT,digest,require
from tools.emulator import Session,Debugger
from tools.build_english import build_rom
from tools.verify_items import ItemChecks
from tools.audit_menu_layouts import Observer,parent_image
from tools.numeric_checks import NumericChecks
from tools.holy_flame_playtest import items
from tools.town_playtest import position
OUT=ROOT/'build/english/storage-validation'
SAVE=ROOT/'build/services/storage-native/storage-ready.sav'

def run():
 mgba.log.silence();rom,build=build_rom();battery=SAVE.read_bytes();results=[];persisted=None
 with Session(rom,OUT/'cold',initial_save=battery) as g:
  g.frames(600);g.press('START',wait=180);g.press('A',wait=300);g.capture('resumed')
  require(position(g)==(288,224),'Repaired storage save did not cold-load at book')
  require([i for _,i,_ in items(g)]==[204,51],'Naturally carried bread/wand absent')
  fixture=g.snapshot();fixture.save(OUT/'ready')
 for name in ['single-roundtrip','batch-deposit','cancel']:
  with Session(rom,OUT/name) as g:
   g.restore(fixture);c=ItemChecks(g,build);o=Observer(g);n=NumericChecks(g);before=items(g)
   for row in build['dialogue']['town_resource']['storage_entries']:
    c.materialized[row['offset']+0x8000000]=row
   save_frames=[]
   def cb(e):
    o.callback(e);c.callback(e);n.callback(e)
    if e['address']==0x08015354:save_frames.append(e['frame'])
   with Debugger(g,cb,max_events=120000) as d:
    for a in set(c.ADDRESSES+o.ADDRESSES+(0x08015354,)):d.breakpoint(a)
    g.press('A',wait=120);g.capture('menu');g.press('A',wait=120);g.capture('carried')
    if name=='cancel':
     g.press('R',wait=60);g.press('B',wait=120);require(items(g)==before,'Cancelling marked items changed inventory')
     g.capture('cancelled')
    else:
     g.press('START' if name=='batch-deposit' else 'R',wait=60);g.capture('marked');g.press('A',wait=120)
     require([i for _,i,_ in items(g)]==([] if name=='batch-deposit' else [51]),'Native deposit did not remove selected items')
     require(c.completed('storage.deposited'),'English deposit acknowledgement absent');g.capture('deposited');g.press('A',wait=120)
     g.press('RIGHT',wait=30);g.press('A',wait=120);g.capture('stored')
     require(any(r['id']=='item-row.204' for r in c.reads),'Stored English bread row absent')
     if name=='single-roundtrip':
      g.press('A',wait=120);g.capture('withdrawn');require(sorted(i for _,i,_ in items(g))==[51,204],'Native withdrawal failed')
      require(c.completed('storage.withdrawn'),'English withdrawal acknowledgement absent');g.press('A',wait=120)
      g.press('DOWN',wait=30);g.press('A',wait=120);g.capture('empty');require(c.completed('storage.empty'),'Empty storage acknowledgement absent');g.press('A',wait=120)
     else:
      g.press('B',wait=120)
      for _ in range(3):g.press('DOWN',wait=30)
      g.press('A',wait=180);g.press('A',wait=300)
      require(save_frames,'Native storage book save was not called')
      persisted=g.snapshot().battery;require(persisted!=fixture.battery,'Deposited items were not saved')
      (OUT/'deposited-native.sav').write_bytes(persisted);g.capture('saved')
    require(not c.active and not c.stack,'Storage render/formatter not complete')
   if name!='batch-deposit':require(g.snapshot().battery==fixture.battery,'Storage case unexpectedly saved')
   results.append({'case':name,'before':before,'after':items(g),'reads':c.reads,'formats':c.formats,'native':o.reads,'numeric_checks':n.samples,'glyph_checks':c.glyph_checks,'inputs':g.inputs,'ordinary_inputs_only':True,'native_save_frames':save_frames})
 require(persisted is not None,'Missing persisted storage case')
 with Session(rom,OUT/'cold-deposit',initial_save=persisted) as g:
  g.frames(600);g.press('START',wait=180);g.press('A',wait=300)
  require(not items(g),'Stored items reappeared in carried inventory after reload')
  c=ItemChecks(g,build)
  with Debugger(g,c.callback,max_events=60000) as d:
   for a in c.ADDRESSES:d.breakpoint(a)
   g.press('A',wait=120);g.press('RIGHT',wait=30);g.press('A',wait=120);g.capture('stored-after-reload')
   require(any(r['id']=='item-row.204' for r in c.reads),'Stored bread missing after cold reload')
   row=next(r for r in c.reads if r['id']=='item-row.204')
   for _ in range(bytes.fromhex(row['window_hex'])[3]):g.press('DOWN',wait=30)
   g.press('A',wait=120)
   require([i for _,i,_ in items(g)]==[204],'Stored bread could not be withdrawn after cold reload')
   g.capture('withdrawn-after-reload')
   g.press('A',wait=120);g.press('RIGHT',wait=30);g.press('A',wait=120);g.press('A',wait=120)
   require(sorted(i for _,i,_ in items(g))==[51,204],'Saved wand/bread round trip lost an item')
  persistence={'passed':True,'save_sha256':digest(persisted),'inputs':g.inputs,'reads':c.reads,'glyph_checks':c.glyph_checks}
 report={'passed':True,'rom_sha256':digest(rom),'source_save_sha256':digest(battery),'cases':results,'persistence':persistence,'scope':'Cold import of a real Japanese book save after normal castle-quest/storage repair. Naturally carried bread/wand; single deposit/withdrawal/empty storage, marking and batch deposit, cancellation, saved deposit and cold reload/withdrawal. No RAM overrides. Sale/full-capacity/filled-pot prompts and bakery remain unlocalized/unvalidated.'}
 (OUT/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print('Repaired storage:',len(results),'ordinary-input cases')
if __name__=='__main__':run()
