"""Storage sale/pot/capacity paths on disposable native states."""
import json,struct
import mgba.log
from tools.rom import ROOT,digest,require
from tools.emulator import Session,Debugger
from tools.build_english import build_rom
from tools.verify_items import ItemChecks
from tools.verify_service_ui import materialize
from tools.verify_bank import balance,choice
from tools.numeric_checks import NumericChecks
from tools.audit_menu_layouts import Observer
from tools.holy_flame_playtest import items
from tools.town_playtest import position
from tools.verify_storage import SAVE
OUT=ROOT/'build/english/storage-services-validation'

class StorageChecks(ItemChecks):
 ADDRESSES=ItemChecks.ADDRESSES+(0x0801f438,0x0801f4f4,0x0801f588,0x0801f8b2,0x0801fa10,0x08015ce8,0x08015e28)
 def __init__(self,g,build):
  super().__init__(g,build)
  self.storage={r['offset']+0x8000000:r for r in build['dialogue']['town_resource']['storage_entries']}
  self.pending=None;self.service_formats=[];self.choice_active=False;self.choices=[]
  self.materialized.update({p:r for p,r in self.storage.items() if b'%' not in bytes.fromhex(r['encoded_hex'])})
  self.materialized.update({r['rom_offset']+0x8000000:r for r in build['dialogue']['entries'] if r.get('bank')=='town-common'})
 def callback(self,e):
  a,r=e['address'],e['registers'];m=self.game.core.memory
  if a==0x08015ce8:self.choice_active=True
  if a==0x08015e28 and self.choice_active:self.choice_active=False;self.choices.append(r[0])
  if a==0x08000fb8 and r[1] in self.storage:
   row=self.storage[r[1]];raw=bytes.fromhex(row['encoded_hex']);args=r[2:4]+[m.u32[r[13]+i*4] for i in range(8)]
   expected=materialize(raw,args,m);require(len(expected)<=256,'Storage output exceeds native stack buffer')
   require((r[14]&~1) in self.ADDRESSES,'Unverified storage format caller')
   self.pending=(r[14]&~1,r[0],expected,bytes(m[r[0]+256:r[0]+272]),row,r[4:12],r[13],args)
  if self.pending and a==self.pending[0]:
   _,dest,raw,guard,row,regs,sp,args=self.pending
   require(bytes(m[dest:dest+len(raw)])==raw,'Storage formatted output differs')
   require(bytes(m[dest+256:dest+272])==guard and r[4:12]==regs and r[13]==sp,'Storage formatter clobbered buffer/ABI')
   self.materialized[dest]=row|{'encoded_hex':raw.hex()}
   self.service_formats.append({'id':row['id'],'return':a,'bytes':len(raw),'capacity':256,'guard_preserved':True,'hex':raw.hex(),'args':args})
   self.pending=None
  super().callback(e)

def stored(g):
 m=g.core.memory
 return [bytes(m[0x0200f008+i*12:0x0200f014+i*12]).hex() for i in range(250) if m.u32[0x0200f008+i*12]&0x80000000]

def run():
 mgba.log.silence();rom,build=build_rom();battery=SAVE.read_bytes();results=[]
 with Session(rom,OUT/'cold',initial_save=battery) as g:
  g.frames(600);g.press('START',wait=180);g.press('A',wait=300)
  require(position(g)==(288,224),'Storage save did not resume at blue book');fixture=g.snapshot()
 names=['sell-carried-no','sell-carried-yes','sell-stored-no','sell-stored-yes','empty-carried','full-storage','partial-capacity','full-inventory','filled-pot-no','filled-pot-yes']
 for name in names:
  print('Storage service',name,flush=True)
  with Session(rom,OUT/name) as g:
   g.restore(fixture);m=g.core.memory;c=StorageChecks(g,build);o=Observer(g);n=NumericChecks(g);before=items(g);gold=balance(g);overrides=[]
   def put(address,data):
    overrides.append({'address':address,'before':bytes(m[address:address+len(data)]).hex(),'after':data.hex()})
    for j,v in enumerate(data):m.u8[address+j]=v
   if name.startswith('filled-pot'):
    mapping=bytes(m[0x020013d0:0x020014d0]);pot=bytearray(120);struct.pack_into('<I',pot,0,0xc8000000);pot[8]=mapping.index(154);pot[4]=3;pot[5]=3
    pot[24:36]=bytes(m[0x0200df28:0x0200df34]);put(0x0200df28,bytes(pot))
    put(0x02003bac+154*20,struct.pack('<I',m.u32[0x02003bac+154*20]|0x40000000));before=items(g)
   def cb(e):o.callback(e);c.callback(e);n.callback(e)
   with Debugger(g,cb,max_events=200000) as d:
    for a in set(c.ADDRESSES+o.ADDRESSES):d.breakpoint(a)
    def press(key):g.press(key,wait=150)
    press('A')
    if name.startswith('sell-stored') or name in ('full-storage','partial-capacity','full-inventory'):
     press('A');press('R');press('A');require(c.completed('storage.deposited'),'Setup deposit failed');press('A')
     require(len(stored(g))==1,'Setup storage record missing')
    if name.startswith('sell'):
     if name.startswith('sell-stored'):press('RIGHT');press('DOWN')
     else:press('DOWN');press('DOWN')
     press('A');g.capture('list');press('R');press('A');g.capture('price')
     require(c.service_formats[-1]['id']=='storage.sale-confirmation','English sale price absent')
     price=c.service_formats[-1]['args'][0];choice(g,c,name.endswith('yes'));g.capture('result')
     require(c.completed('storage.sold' if name.endswith('yes') else 'storage.cancelled'),'Sale result absent')
     require(balance(g)==(gold[0]+(price if name.endswith('yes') else 0),gold[1]),'Sale gold result differs')
     if name.startswith('sell-carried'):require([i for _,i,_ in items(g)]==([51] if name.endswith('yes') else [204,51]),'Sale inventory differs')
     else:require(len(stored(g))==(0 if name.endswith('yes') else 1),'Sale changed wrong stored count')
    elif name=='empty-carried':
     press('A');press('START');press('A');press('A');press('DOWN');press('DOWN');press('A')
     require(c.completed('town-common.4090'),'Empty inventory message absent');require(not items(g),'Batch deposit failed');g.capture('empty')
    elif name=='full-storage':
     record=bytes(m[0x0200f008:0x0200f014])
     for i in range(1,20):put(0x0200f008+i*12,record)
     before_stored=stored(g);before=items(g);press('A');g.capture('full')
     require(c.service_formats[-1]['id']=='storage.full','Storage capacity warning absent')
     require(c.service_formats[-1]['args'][0]==20,'Expected earned 20-slot capacity')
     require(stored(g)==before_stored and items(g)==before,'Full storage altered items')
    elif name=='partial-capacity':
     record=bytes(m[0x0200f008:0x0200f014])
     for i in range(1,19):put(0x0200f008+i*12,record)
     # Two selected ordinary items exceed the one remaining storage slot.
     put(0x0200df28+120,bytes(m[0x0200df28:0x0200df28+120]))
     before_stored=stored(g);before=items(g)
     press('A');press('START');press('A');g.capture('batch-too-large')
     require(c.service_formats[-1]['id']=='storage.full' and c.service_formats[-1]['return']==0x0801F588,
             'Partial-capacity batch did not reach the second warning caller')
     require(c.service_formats[-1]['args'][0]==20 and stored(g)==before_stored and items(g)==before,
             'Rejected batch changed storage/inventory or capacity')
    elif name=='full-inventory':
     record=bytes(m[0x0200df28:0x0200dfa0])
     for i in range(1,20):put(0x0200df28+i*120,record)
     before=items(g);press('RIGHT');press('A');press('A');g.capture('full')
     require(c.completed('storage.inventory-full'),'Inventory capacity warning absent')
     require(items(g)==before and len(stored(g))==1,'Failed withdrawal altered items')
    else:
     press('A');press('R');press('A');g.capture('warning')
     require(c.service_formats[-1]['id']=='storage.filled-pot','Filled-pot destruction warning absent')
     choice(g,c,name.endswith('yes'));g.capture('result')
     if name.endswith('no'):require(items(g)==before and not stored(g),'Declining pot break altered inventory/storage')
     else:
      require([i for _,i,_ in items(g)]==[51] and len(stored(g))==1,'Pot break did not store its sole content')
      require(c.completed('storage.deposited'),'Pot contents deposit acknowledgement absent')
    # Complete only outstanding message pages, without initiating another action.
    for _ in range(8):
     if not c.active:break
     press('A')
    require(not c.pending and not c.active and not c.stack,'Storage checks left incomplete formatter/reader')
   require(g.snapshot().battery==fixture.battery,'Transaction probe unexpectedly changed save')
   results.append({'case':name,'controlled_overrides':overrides,'inputs':g.inputs,'choices':c.choices,'reads':c.reads,'formats':c.service_formats,'glyph_checks':c.glyph_checks,'numeric_checks':n.samples,'native':o.reads,'before_items':before,'after_items':items(g),'gold_before':gold,'gold_after':balance(g),'stored_after':stored(g)})
 report={'passed':True,'rom_sha256':digest(rom),'source_save_sha256':digest(battery),'cases':results,'scope':'Five ordinary sale/empty-inventory cases; five explicitly controlled full-storage/partial-capacity/full-inventory/filled-pot cases. Native game transactions, original 256-byte formatter buffers and shared glyph checks. Source save unchanged.'}
 (OUT/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print('Storage service cases:',len(results));return report
if __name__=='__main__':run()
