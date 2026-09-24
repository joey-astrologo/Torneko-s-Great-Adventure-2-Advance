"""Native UI rendering, format bounds and normal-button option navigation."""
import json
import mgba.log
from tools.numeric_checks import NumericChecks
from tools.rom import ROOT,require,digest
from tools.emulator import Session,Debugger,Snapshot
from tools.audit_menu_layouts import Observer
from tools.dialogue_checks import TextChecks
from tools.service_fixtures import dungeon

OUT=ROOT/'build/english/dungeon-ui-validation'

def cstring(memory,ptr,limit=512):
 data=bytes(memory[ptr:ptr+limit]);return data[:data.index(0)]

def materialize(template,args,memory):
 result=bytearray();i=0;n=0
 while i<len(template):
  if template[i]!=37:result.append(template[i]);i+=1;continue
  kind=template[i+1];value=args[n];n+=1;i+=2
  if kind==99:result.append(value&255)
  elif kind==100:result.extend(str(value if value<0x80000000 else value-0x100000000).encode())
  elif kind==115:result.extend(cstring(memory,value))
  else:raise ValueError('Unexpected format conversion')
 return bytes(result)

class UiChecks(TextChecks):
 ADDRESSES=TextChecks.ADDRESSES+(0x08000fb8,0x08019b12,0x08019bca,0x08019c5c,0x0801a68c,0x0801a6ea,0x0801a712)
 def __init__(self,g,ui):
  self.rows={r['offset']+0x8000000:r for r in ui['entries']}
  super().__init__(g,{p:{'id':r['id'],'encoded_hex':r['encoded_hex'],'layout':{'pages':[[r['id']]]}} for p,r in self.rows.items() if r['kind']=='plain'})
  self.pending=None;self.formats=[]
 def callback(self,e):
  a,r=e['address'],e['registers'];m=self.game.core.memory
  if a==0x08000fb8 and r[1] in self.rows:
   row=self.rows[r[1]];raw=bytes.fromhex(row['encoded_hex']);args=r[2:4]+[m.u32[r[13]+i*4] for i in range(8)]
   expected=materialize(raw,args,m);cap=64 if row['kind']=='status' else 36
   require(len(expected)<=cap,'UI formatter exceeds owned buffer')
   self.pending=(r[14]&~1,r[0],expected,cap,bytes(m[r[0]+cap:r[0]+cap+16]),row['id'],r[4:12],r[13])
  if self.pending and a==self.pending[0]:
   _,dest,expected,cap,guard,ident,regs,sp=self.pending
   require(bytes(m[dest:dest+len(expected)])==expected,'UI formatter output differs')
   require(bytes(m[dest+cap:dest+cap+16])==guard and r[4:12]==regs and r[13]==sp,'UI formatter overwrote buffer/stack guard')
   self.resources[dest]={'id':ident,'encoded_hex':expected.hex(),'layout':{'pages':[[ident]]}}
   self.formats.append({'id':ident,'bytes':len(expected),'capacity':cap,'expected_hex':expected.hex(),'guard_preserved':True});self.pending=None
  if a in TextChecks.ADDRESSES:super().callback(e)

def run():
 from tools.build_english import build_rom
 mgba.log.silence();rom,build=build_rom()
 fixture=dungeon(rom,build);rows=[]
 for name,index in [('controls',0),('sound',1),('auto-turn',2),('map',3),('give-up',4),('sleep',5)]:
  with Session(rom,OUT/name) as game:
   game.restore(fixture);o=Observer(game);c=UiChecks(game,build['ui']);numbers=NumericChecks(game)
   def cb(e):o.callback(e);c.callback(e);numbers.callback(e)
   with Debugger(game,cb,max_events=60000) as d:
    for a in set(o.ADDRESSES+c.ADDRESSES):d.breakpoint(a)
    game.press('B',hold=8,wait=120);game.capture('status');game.press('DOWN',wait=30);game.press('DOWN',wait=30);game.press('A',wait=120);game.capture('options')
    for _ in range(index):game.press('DOWN',wait=20)
    if index in (1,2,3):
     literal={1:0x1a8e4,2:0x1a930,3:0x1a958}[index]
     address=int.from_bytes(rom[literal:literal+4],'little');m=game.core.memory;before=m.u8[address]
     game.press('RIGHT',wait=60);game.capture('changed');require(m.u8[address]==1-before,'Option did not toggle')
     game.press('LEFT',wait=60);game.capture('restored');require(m.u8[address]==before,'Option did not restore')
    else:game.press('A',wait=120);game.capture('selected')
    game.press('B',wait=120);game.capture('cancel')
   require(c.reads and not c.active and not c.pending,'Incomplete UI verification')
   rows.append({'case':name,'reads':c.reads,'formats':c.formats,'glyph_checks':c.glyph_checks,'native':o.reads,'inputs':game.inputs,'numeric_checks':numbers.samples})
 report={'passed':True,'rom_sha256':digest(rom),'cases':rows,'scope':'Cold native suspend continuation, ordinary option navigation; no RAM injection.'}
 (OUT/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print('Dungeon UI:',len(rows),'routes')
if __name__=='__main__':run()
