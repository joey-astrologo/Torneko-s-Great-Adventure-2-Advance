"""Controlled native core combat formatting/queue/glyph checks for the prototype."""
import json,mgba.log,argparse
from tools.rom import ROOT,digest,require
from tools.emulator import Session,Snapshot,Debugger
from tools.compact_font import encode
from tools.dialogue_checks import TextChecks,rendered_codes
from tools.verify_service_ui import cstring,materialize
OUT=ROOT/'build/combat-prototype/validation'

class CombatCheck(TextChecks):
 def __init__(self,g,expected,queue_return,capacity,guard):
  super().__init__(g,{})
  self.expected_payload=expected;self.queue_return=queue_return;self.capacity=capacity;self.guard=guard
  self.queued=None;self.draws=[];self.complete=False;self.pending_glyph=None;self.queue_abi=None;self.returned=False;self.fragment_returned=False;self.fragment_abi=None
 def gameplay(self):
  m=self.game.core.memory;actors=[]
  for i in range(56):
   p=m.u32[0x02001624+i*4]
   if 0x02000000<=p<0x0203ff00:actors.append((p,m.u32[p+0x5c],m.u16[p+0x84],m.u16[p+0x86],m.u16[p+0x88]))
  return actors,bytes(m[0x0200df28:0x0200df28+20*120])
 def width(self,data):return sum(self.glyph_record(c)[0]['advance'] for c in rendered_codes(data+b'\0'))
 def callback(self,e):
  a,r=e['address'],e['registers'];m=self.game.core.memory
  if a==0x0801588c and r[14]==self.queue_return and self.queued is None:
   self.queue_abi=(r[4:12],r[13]);self.dest=r[0];self.gameplay_before=self.gameplay()
  if a==0x0801588c and r[14]==0x0800c9f7:
   self.fragment_abi=(r[4:12],r[13])
  if a==0x0800c9f6 and self.fragment_abi:
   require((r[4:12],r[13])==self.fragment_abi,'Suppressed damage fragment changed ABI');self.fragment_returned=True
  if a==0x080158ce and r[14]==0x0800c9f7:
   raise ValueError('Incoming damage fragment was queued twice')
  if a==0x080158ce and r[14]==self.queue_return and self.queued is None:
   raw=cstring(m,r[6]);expected=self.expected_payload
   if self.width(expected)<=216:expected=expected.replace(b'\r',b'')
   require(raw==expected,'Combat queued text/one-line decision differs')
   require(len(raw)+1<=256 and bytes(m[r[6]+256:r[6]+272])==self.guard,'Combat buffer guard changed')
   widths=[self.width(line) for line in raw.split(b'\r')];require(max(widths)<=216,'Combat fallback line exceeds budget')
   self.queued={'hex':raw.hex(),'line_widths':widths,'one_line':b'\r' not in raw,'bytes':len(raw)+1}
   self.expected=rendered_codes(raw+b'\0');self.window=0x02000000
  if a==(self.queue_return&~1) and self.queue_abi:
   require((r[4:12],r[13])==self.queue_abi,'Combat queue changed saved registers/SP');require(self.gameplay()==self.gameplay_before,'Combat queue changed actor HP/level/EXP or inventory');self.returned=True
  if not self.queued or self.complete:return
  if a==0x08001bc4:
   require(r[0]==self.window,'Combat text used unexpected window');g,_=self.glyph_record(r[1]);x,y=m.u8[r[0]+2],m.u8[r[0]+3]
   key=(r[1],r[13],r[14],x,y)
   if self.pending_glyph and self.pending_glyph['key']==key:return
   require(self.pending_glyph is None,'Next combat glyph arrived before completion')
   require(r[1]==self.expected[len(self.draws)],'Combat glyph sequence differs')
   require(m.u8[r[0]+6]==m.u8[r[0]+8]==0,'Combat font spacing changed')

   self.pending_glyph={'key':key,'code':r[1],'x':x,'y':y,'advance':g['advance'],'prepared':False}
  if a==0x08001c14 and self.pending_glyph:
   p=self.pending_glyph;g,ptr=self.glyph_record(r[4]);require(r[4]==p['code'] and r[0]==ptr,'Combat glyph lookup differs')
   # 01BC4 is before the native scroll check (01BDA..01BEC). Check
   # actual drawing coordinates after that check, at bitmap preparation.
   x,y=m.u8[r[5]+2],m.u8[r[5]+3]
   require(x+g['advance']<=m.u8[r[5]+4]*8 and y<m.u8[r[5]+5], 'Combat glyph clips after native scrolling')
   p.update(x=x,y=y,native_scroll=y!=p['y'])
   fg=m.u8[0x020000c2];bg=4 if m.u8[r[5]+9]&1 else 7
   pixels=bytes(fg if v=='#' else (7 if y<2 else bg) for y,line in enumerate(g['rows']) for v in line)+bytes([bg])*g['advance']
   require(bytes(m[0x02036430:0x02036430+len(pixels)])==pixels,'Combat glyph pixels differ');p['prepared']=True
  if a==0x08001c68 and self.pending_glyph:
   p=self.pending_glyph;require(p['prepared'] and r[4]==p['code'] and r[0]&255==p['x']+p['advance'],'Combat glyph cursor differs')
   self.draws.append(p);self.pending_glyph=None
   if len(self.draws)==len(self.expected):self.complete=True

def run(cumulative=False):
 global OUT
 if cumulative:OUT=ROOT/'build/english/combat-validation/controlled'
 mgba.log.silence();root=OUT.parent;rom=(ROOT/'build/english/torneko-2-english.gba' if cumulative else root/'game.gba').read_bytes();build=json.loads((ROOT/'build/english/build.json' if cumulative else root/'build.json').read_text())
 if cumulative:
  from tools.combat_fixtures import create
  create(rom,build,root)
 templates={r['id']:r for r in build['combat']['entries']};rows=[]
 names=[(str(r['id']),r['english']) for r in build['monsters']['entries']]
 cases=[('name-'+label,'combat.19c',name,9) for label,name in names]
 for ident in ['combat.19c','combat.1a8','combat.1a0','combat.1b4','combat.1b8','combat.1a4','combat.1bc','combat.1c0']:
  for label,name,n in [('short','Slime',1),('wide','Crack-billed platypunk Lv32767',2147483647),('zero','Torneko',0),('wide-low','Crack-billed platypunk Lv32767',1)]:cases.append((ident+'-'+label,ident,name,n))
 for label,ident,name,n in cases:
  incoming=ident in ('combat.1b4','combat.1b8');fixture_id='combat.1b4' if incoming else 'combat.1a0' if ident=='combat.1a0' else 'combat.19c';fixture=Snapshot.load(root/'native'/fixture_id)
  require(fixture.rom_sha256==digest(rom),'Combat fixture stale')
  with Session(rom,OUT/label) as g:
   g.restore(fixture);m=g.core.memory;r=g.core.cpu.gprs;dest=int(r[0]);sp=int(r[13]);rawname=encode(name);require(len(rawname)<=64,'Probe actor name too long')
   for i,v in enumerate(rawname.ljust(64,b'\0')):m.u8[0x02008d08+i]=v
   row=templates[ident];r[1]=row['offset']+0x8000000;r[2]=0x02008d08;r[3]=n
   if incoming:m.u32[sp+0x26c]=n
   expected=materialize(bytes.fromhex(row['encoded_hex']),[0x02008d08,n],m)[:-1]
   if incoming:expected+=materialize(bytes.fromhex(templates['combat.1c4']['encoded_hex']),[n],m)[:-1]
   ret=0x0800c9cf if incoming else 0x0800d487 if ident=='combat.1a0' else 0x0800cefb
   c=CombatCheck(g,expected,ret,256,bytes(m[dest+256:dest+272]))
   with Debugger(g,c.callback,max_events=20000) as d:
    for a in [0x0801588c,0x080158ce,0x08001bc4,0x08001c14,0x08001c68,ret&~1,0x0800c9f6]:d.breakpoint(a)
    for _ in range(180):
     g.frames(1)
     if c.complete and c.returned and (not incoming or c.fragment_returned):break
    require(c.complete and c.returned and (not incoming or c.fragment_returned),'Controlled combat did not render/return')
    g.capture('rendered')
   rows.append({'case':label,'format':ident,'actor':name,'value':n,'queue':c.queued,'glyphs':len(c.draws),'draws':c.draws,'incoming_duplicate_fragment_suppressed':c.fragment_returned if incoming else None,'buffer_guard_preserved':True,'callee_saved_and_sp_preserved':True,'controlled_overrides':['format argument','name argument and existing 64-byte actor-name scratch','numeric argument/local'],'inputs':g.inputs})
 report={'passed':True,'rom_sha256':digest(rom),'cases':rows,'scope':'Explicit controlled arguments at naturally reached native combat formatter entries. Checks semantic numbers/names, exact queue output, conditional one-line fit, fallback widths, native glyph pixels/cursors, 256-byte guard and queue ABI. Does not establish ordinary gameplay outcome equivalence.'}
 (OUT/'report.json').write_text(json.dumps(report,indent=2)+'\n');print('Combat native cases:',len(rows),'one-line:',sum(r['queue']['one_line'] for r in rows));return report
if __name__=='__main__':
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--cumulative',action='store_true');run(parser.parse_args().cumulative)
