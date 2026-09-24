"""Native bank transactions and explicitly controlled financial boundary cases."""
import json
import mgba.log
from tools.numeric_checks import NumericChecks
from tools.rom import ROOT,require,digest
from tools.emulator import Session,Snapshot,Debugger
from tools.dialogue_checks import TextChecks
from tools.audit_menu_layouts import Observer
from tools.verify_service_ui import materialize

OUT=ROOT/'build/english/bank-validation'
CAP=99999999
class BankChecks(TextChecks):
 ADDRESSES=TextChecks.ADDRESSES+(0x08000fb8,0x0801dff2,0x0801e03a,0x0801e070,0x0801e0a0,0x0801e0ee,0x0801e118,0x0801e144,0x0801e206,0x0801e248,0x0801e30c,0x0801e352,0x08015ce8,0x08015e28)
 def __init__(self,g,build):
  self.rows={r['offset']+0x8000000:r for r in build['dialogue']['town_resource']['service_entries']}
  resources={p:{'id':r['id'],'encoded_hex':r['encoded_hex'],'layout':r['layout']} for p,r in self.rows.items() if b'%' not in bytes.fromhex(r['encoded_hex'])}
  choice=next(r for r in build['dialogue']['entries'] if r['id']=='rom.0006309c');resources[choice['rom_offset']+0x8000000]=choice
  super().__init__(g,resources);self.pending=None;self.formats=[];self.choice_active=False;self.choices=[]
 def callback(self,e):
  a,r=e['address'],e['registers'];m=self.game.core.memory
  if a==0x08015ce8:self.choice_active=True
  if a==0x08015e28 and self.choice_active:self.choices.append(r[0]);self.choice_active=False
  if a==0x08000fb8 and r[1] in self.rows:
   row=self.rows[r[1]];raw=bytes.fromhex(row['encoded_hex']);args=r[2:4]+[m.u32[r[13]+i*4] for i in range(8)]
   expected=materialize(raw,args,m);dest=r[0]
   if row['index']==91:
    from tools.verify_service_ui import cstring
    base=r[13]+4;prefix=cstring(m,base) if dest!=base else b''
    require(dest==base+len(prefix) and r[14]==0x0801e30d,'Unexpected bank reward composition owner')
    expected=prefix+expected;dest=base
    row=row|{'layout':row['layout']|{'pages':row['layout']['pages']*((prefix.count(b'\r')+1)//2+1)}}
   require(len(expected)<=384,'Bank stream exceeds owned buffer')
   self.pending=(r[14]&~1,dest,expected,bytes(m[dest+384:dest+400]),row,r[4:12],r[13])
  if self.pending and a==self.pending[0]:
   _,dest,expected,guard,row,regs,sp=self.pending
   require(bytes(m[dest:dest+len(expected)])==expected,'Bank format output differs')
   require(bytes(m[dest+384:dest+400])==guard and r[4:12]==regs and r[13]==sp,'Bank stack guard changed')
   self.resources[dest]={'id':row['id'],'encoded_hex':expected.hex(),'layout':row['layout']}
   self.formats.append({'id':row['id'],'bytes':len(expected),'guard_preserved':True,'expected_hex':expected.hex()});self.pending=None
  if a in TextChecks.ADDRESSES:super().callback(e)

def balance(g):
 m=g.core.memory;return (m.u32[m.u32[0x02001624]+0x60],m.u32[0x02002c1c])
def open_bank(g):
 g.press('UP',hold=8,wait=120);g.press('A',wait=120);g.press('A',wait=120)
def choice(g,c,yes):
 for _ in range(8):
  if c.choice_active:break
  g.press('A',wait=120)
 require(c.choice_active,'Bank confirmation missing');g.capture('confirmation')
 g.press('A' if yes else 'B',wait=120)
def next_menu(g,c):
 for _ in range(8):
  g.press('A',wait=120)
  if c.reads[-1]['id']=='bank.81' and not c.active:return
 raise ValueError('Bank menu did not return')

def run():
 from tools.build_english import build_rom
 mgba.log.silence();rom,build=build_rom();fixture=Snapshot.load(ROOT/'build/english/mansion-validation/family-1-1/morning');rows=[]
 cases=[('roundtrip',None,None),('amount-cancel',None,None),('empty-withdraw',None,None),('empty-deposit',0,0),
        ('deposit-insufficient-no',20,0),('deposit-insufficient-yes',20,0),
        ('withdraw-insufficient-no',0,20),('withdraw-insufficient-yes',0,20),
        ('deposit-overflow-no',20,CAP-2),('deposit-overflow-yes',20,CAP-2),
        ('withdraw-overflow-no',CAP-2,20),('withdraw-overflow-yes',CAP-2,20)]
 for name,wallet,bank in cases:
  with Session(rom,OUT/name) as g:
   print('Bank',name,flush=True);g.restore(fixture);m=g.core.memory
   if wallet is not None:m.u32[m.u32[0x02001624]+0x60]=wallet;m.u32[0x02002c1c]=bank
   before=balance(g);c=BankChecks(g,build);o=Observer(g);numbers=NumericChecks(g)
   def cb(e):o.callback(e);c.callback(e);numbers.callback(e)
   with Debugger(g,cb,max_events=100000) as d:
    for a in set(c.ADDRESSES+o.ADDRESSES):d.breakpoint(a)
    open_bank(g);g.capture('menu')
    if name.startswith('withdraw') or name=='empty-withdraw':g.press('DOWN',wait=30)
    g.press('A',wait=120);g.capture('amount-or-empty')
    if name.startswith('empty'):
     require(c.completed('bank.94' if name=='empty-withdraw' else 'bank.88'),'Empty balance message missing')
     require(balance(g)==before,'Empty operation changed gold')
    elif name=='amount-cancel':
     # Exercise all ten digit shapes and move through all eight fixed cells.
     for digit in range(10):
      g.press('UP',wait=30);g.capture(f'amount-digit-{digit}')
     for _ in range(7):g.press('LEFT',wait=30)
     g.capture('amount-leftmost')
     for _ in range(7):g.press('RIGHT',wait=30)
     g.capture('amount-rightmost')
     require(set(range(0x824f,0x8259)) <= {s['code'] for s in numbers.samples},'Bank did not render all compact digits')
     g.press('B',wait=120);require(balance(g)==before,'Amount cancellation changed gold')
    elif name=='roundtrip':
     g.press('A',wait=120);require(balance(g)==(0,before[0]),'Natural deposit failed');g.capture('deposited')
     next_menu(g,c);g.press('DOWN',wait=30);g.press('A',wait=120);g.press('A',wait=120)
     require(balance(g)==before,'Natural withdrawal failed');g.capture('withdrawn');next_menu(g,c);g.press('B',wait=120)
    else:
     if 'insufficient' in name:g.press('UP',wait=30)
     g.press('A',wait=120);g.capture('warning-first-page')
     require(balance(g)==before,'Gold changed before confirmation')
     yes=name.endswith('-yes');choice(g,c,yes);after=balance(g)
     if not yes:require(after==before,'Declined transaction changed gold')
     elif name.startswith('deposit'):require(after==(0,min(CAP,sum(before))),'Confirmed deposit result differs')
     else:require(after==(min(CAP,sum(before)),0),'Confirmed withdrawal result differs')
     g.capture('result')
   require(not c.pending and not c.active,'Bank text verification incomplete')
   require(g.snapshot().battery==fixture.battery,'Bank test wrote a save unexpectedly')
   rows.append({'case':name,'controlled_balances':None if wallet is None else [wallet,bank],'before':before,'after':balance(g),
                'reads':c.reads,'formats':c.formats,'choices':c.choices,'native':o.reads,'glyph_checks':c.glyph_checks,'inputs':g.inputs,'numeric_checks':numbers.samples})
 report={'passed':True,'rom_sha256':digest(rom),'cases':rows,'scope':'Three natural-input cases from the earned bank-opening checkpoint; nine controlled balance/overflow cases. Transfers change disposable RAM only. Gift/reward text and persisted transaction saves are not covered.'}
 (OUT/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print('Bank checks:',len(rows));return report
if __name__=='__main__':run()
