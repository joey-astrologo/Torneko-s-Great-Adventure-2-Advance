"""Native bank transfers followed by book saves and cold reloads."""
import json,mgba.log
from tools.rom import ROOT,digest,require
from tools.emulator import Session,Debugger
from tools.build_english import build_rom
from tools.verify_storage import SAVE
from tools.verify_bank import BankChecks,balance,next_menu
from tools.town_playtest import position
OUT=ROOT/'build/english/bank-persistence-validation'

def run():
 mgba.log.silence();rom,build=build_rom();original=SAVE.read_bytes();battery=original;cases=[];starting=None
 for mode in ['deposit','withdraw','reload']:
  with Session(rom,OUT/mode,initial_save=battery) as g:
   g.frames(600);g.press('START',wait=180);g.press('A',wait=300);require(position(g)==(288,224),'Native book save did not resume')
   before=balance(g)
   if starting is None:starting=before;require(before[0]>0 and before[1]==0,'Expected naturally earned gold and empty bank')
   else:require(before==((0,sum(starting)) if mode=='withdraw' else starting),'Bank balance did not persist across cold reload')
   if mode=='reload':g.capture('restored');cases.append({'case':mode,'balances':before,'inputs':g.inputs});break
   c=BankChecks(g,build);saves=[]
   def cb(e):
    c.callback(e)
    if e['address']==0x08015354:saves.append(e['frame'])
   with Debugger(g,cb,max_events=150000) as d:
    for a in set(c.ADDRESSES+(0x08015354,)):d.breakpoint(a)
    # Leave the house through its actual doorway before walking to the banker.
    for key,hold in [('RIGHT',16),('DOWN',32),('LEFT',32),('DOWN',32),('LEFT',32),('DOWN',3),('DOWN',16),('RIGHT',64),('DOWN',16),('RIGHT',16),('UP',3)]:
     g.press(key,hold=hold,wait=120)
    g.capture('bank-approach')
    print(mode,'bank approach',position(g),before,flush=True)
    g.press('A',wait=150);g.press('A',wait=150);require(c.completed('bank.81'),'Bank menu missing after ordinary walk')
    if mode=='withdraw':g.press('DOWN',wait=30)
    g.press('A',wait=150);g.press('A',wait=150);expected=(0,sum(starting)) if mode=='deposit' else starting
    require(balance(g)==expected,'Native bank transfer differs');g.capture('transferred')
    next_menu(g,c);g.press('B',wait=150);g.press('A',wait=150)
    for key,hold in [('DOWN',8),('LEFT',72),('UP',24),('UP',56),('RIGHT',32),('UP',24),('RIGHT',32),('UP',32),('LEFT',16),('UP',3)]:
     g.press(key,hold=hold,wait=120)
     print('return',key,position(g),flush=True)
    print(mode,'book approach',position(g),flush=True);require(position(g)==(288,224),'Did not return to book')
    g.press('A',wait=150)
    for _ in range(3):g.press('DOWN',wait=30)
    g.press('A',wait=180);g.press('A',wait=300);require(saves,'Native book save was not written')
    battery=g.snapshot().battery;(OUT/f'{mode}.sav').write_bytes(battery);g.capture('saved')
   cases.append({'case':mode,'before':before,'after':balance(g),'inputs':g.inputs,'reads':c.reads,'formats':c.formats,'native_save_frames':saves,'save_sha256':digest(battery)})
 report={'passed':True,'rom_sha256':digest(rom),'source_save_sha256':digest(original),'cases':cases,'scope':'Ordinary movement and native bank transfers of naturally earned gold. Deposit/save/cold reload, withdrawal/save/cold reload. No RAM overrides.'}
 (OUT/'report.json').write_text(json.dumps(report,indent=2)+'\n');print('Bank persisted deposit and withdrawal passed')
if __name__=='__main__':run()
