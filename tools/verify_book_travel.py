"""Controlled native legacy book menu and complete travel-confirmation flows."""
import argparse,json,struct
from pathlib import Path
import mgba.log
from unittest.mock import patch
from tools.rom import ROOT,digest,require
from tools.emulator import Session,Debugger,ffi
from tools.dialogue_checks import TextChecks,rendered_codes,player_layout_cases
from tools.bakery_playtest import service_ready
from tools.compact_font import encode
from tools.name_entry import HERO,indexed

class SavedChecks(TextChecks):
 def __init__(self,g,rows,saved):super().__init__(g,rows);self.saved=saved
 def codes(self,payload,*args,**kwargs):return rendered_codes(payload.replace(b'\x1f',self.saved[:-1]),*args,**kwargs)
 def callback(self,e):
  # The original1F getter supplies its own20-byte saved-village buffer. Adapt
  # only the checker's nested-reader identity; do not alter native registers.
  if self.active and e['address']==0x080021B4 and e['registers'][1]==0x0200CEE8:
   require(bytes(self.game.core.memory[0x0200CEE8:0x0200CEE8+len(self.saved)])==self.saved,'Saved village nested reader differs');r=list(e['registers']);r[1]=HERO;e=e|{'registers':r}
  with patch('tools.dialogue_checks.rendered_codes',self.codes):super().callback(e)

def run(source=ROOT/'build/english'):
 out=source/'book-travel-validation';rom=(source/'torneko-2-english.gba').read_bytes();b=json.loads((source/'build.json').read_text());require(digest(rom)==b['output_sha256'],'Stale book/travel ROM');mgba.log.silence();fixture=service_ready(rom,out)
 rows={r['offset']+0x08000000:r for r in b['book_travel']['entries']};jp=dict(player_layout_cases())['widest-Japanese'][:2];table=b['name_entry']['glyph_table']-0x08000000;jpi=next(i for i in range(0xB9) if rom[table+2*i:table+2*i+2]==jp)
 profiles={'ordinary':(indexed('Torneko',8)[:8],encode('Torneko')),'wide-English':(indexed('W'*8,8)[:8],encode('W'*8)),'wide-Japanese':(bytes([jpi])*8,jp*8+b'\0')}
 cases=[('book',enabled,action,'ordinary') for enabled in (False,True) for action in ('cancel','records','scores')]+[('book',True,'trade','ordinary'),('book',True,'empty','ordinary')]+[('travel',mode,action,profile) for mode in (0,1) for action in ('cancel','no','yes') for profile in (profiles if mode==0 and action=='yes' else ['ordinary'])]
 results=[]
 for kind,variant,action,profile in cases:
  case=f'{kind}-{int(variant)}-{action}-{profile}';print('Book/travel:',case,flush=True)
  with Session(rom,out/case) as g:
   g.restore(fixture);m=g.core.memory;stored,saved=profiles[profile];c=SavedChecks(g,rows,saved);initial=[];returns=[];overrides=[];draws=[];creates=[];getter=[];images={};pixels=0;cycle=0;owner=0x08050AA8 if kind=='book' else 0x080524F4;end=0x08050BC2 if kind=='book' else 0x0805278E
   def write(at,data):
    overrides.append({'address':at,'before':bytes(m[at:at+len(data)]).hex(),'after':data.hex()})
    for i,v in enumerate(data):m.u8[at+i]=v
   inventory=bytes(m[0x0200DF28:0x0200E888]);battery=g.snapshot().battery
   def callback(e):
    a,r=e['address'],e['registers']
    if a==0x0801DFAC and len(initial)==len(returns):
     initial.append(e|{'guard':bytes(m[r[13]:r[13]+32]).hex()});draws.clear()
     if kind=='travel':g.core.cpu.gprs[0]=variant;g.core.cpu.gprs[1]=0
     if kind=='book':write(0x0200F008,struct.pack('<I',(m.u32[0x0200F008]&0x7FFFFFFF)|(0 if action=='empty' else 0x80000000)))
     overrides.append({'event':e,'pc_after':owner,'r0_after':variant if kind=='travel' else r[0],'r1_after':0 if kind=='travel' else r[1],'reason':'Controlled ordinary bank call redirected to complete owned book/travel function; script reachability excluded.'});require(g.core._core.writeRegister(g.core._core,b'pc',ffi.new('uint32_t*',owner)),'Book/travel redirect failed');return
    if len(initial)==len(returns):return
    if a==0x08050ABA and kind=='book':g.core.cpu.gprs[0]=int(variant);overrides.append({'event':e,'r0_after':int(variant),'reason':'Select native two/three-row availability branch.'})
    if a==0x0801FAC8:
     require(r[0]==0,'Original saved-village header read failed');write(r[13]+0x14,stored)
    if a==0x0801FB18:
     require(r[0]==0x0200CEE8 and bytes(m[r[0]:r[0]+len(saved)])==saved,'Saved village getter output differs');getter.append(e)
    if a==0x08001798:creates.append(e)
    if a in (0x08001750,0x08001888):draws[:]=[d for d in draws if d['window']!=r[0]]
    if a==0x080021B4 and r[1] in rows:
     ident=rows[r[1]]['id'];w=r[0]
     if ident.startswith('book.') and ident!='book.empty':require(bytes(m[w:w+2])==bytes((8,24)) and bytes(m[w+4:w+6])==bytes((9,2+int(variant))),'Record menu geometry changed')
     if ident=='travel.meadow':require(bytes(m[w:w+2])==bytes((8,120)) and bytes(m[w+4:w+6])==bytes((28,2)),'Meadow prompt geometry changed')
     if ident=='travel.choices':require(bytes(m[w:w+2])==bytes((152,88) if variant==0 else (128,72)) and bytes(m[w+4:w+6])==bytes((10,1)),'Travel choices geometry changed')
     if ident=='travel.question':require(bytes(m[w:w+2])==bytes((32,72)) and bytes(m[w+4:w+6])==bytes((10,1)),'Travel question geometry changed')
    if a==0x08001BC4 and c.active:
     w=r[0];key=(w,r[1],r[13],r[14],m.u8[w+2],m.u8[w+3])
     if not draws or draws[-1]['key']!=key:draws.append({'key':key,'window':w,'code':r[1],'x':m.u8[w+2],'y':m.u8[w+3],'origin':[m.u8[w],m.u8[w+1]],'foreground':m.u8[0x020000C2],'bank':m.u16[m.u32[w+12]]>>12,'id':c.active['id']})
    if a in c.ADDRESSES:c.callback(e)
    if a==end:
     old=initial[-1]['registers'];require(r[4:12]==old[4:12] and r[13]==old[13] and r[0 if kind=='book' else 1]==old[14] and bytes(m[r[13]:r[13]+32]).hex()==initial[-1]['guard'],'Book/travel caller ABI/guard differs')
     if kind=='book':expected=255 if cycle<2 or action in ('cancel','empty') else {'records':0,'scores':1,'trade':2}[action];require(m.u8[0x020101A1]==expected,'Book native selection differs')
     else:expected=2 if cycle<2 or action=='cancel' else 1 if action=='no' else 0;require(r[0]==expected,'Travel native selection differs: '+repr((case,cycle,r[0],expected)))
     returns.append(e|{'native_result_checked':True})
   def capture(tag):
    nonlocal pixels
    g.frames(8);pic=g.capture(tag);images[tag+'.png']=digest((g.output/(tag+'.png')).read_bytes());require(draws and not c.active,'Book/travel incomplete drawing')
    for d in draws:
     glyph,_=c.glyph_record(d['code']);colour=m.u16[0x05000000+2*(16*d['bank']+d['foreground'])];rgb=tuple(((colour>>s)&31)*255//31 for s in (0,5,10))
     for y,line in enumerate(glyph['rows']):
      for x,bit in enumerate(line):require((pic.getpixel((d['origin'][0]+d['x']+x,d['origin'][1]+16*d['y']+y))==rgb)==(bit=='#'),'Book/travel final pixels differ: '+repr((case,tag,d['id'],hex(d['code']),d['x']+x,16*d['y']+y)));pixels+=1
   with Debugger(g,callback,max_events=160000) as debug:
    for a in set(c.ADDRESSES)|{0x0801DFAC,0x08050ABA,end,0x08001798,0x08001750,0x08001888,0x0801FAC8,0x0801FB18}:debug.breakpoint(a)
    for cycle in range(3):
     g.press('A',hold=1,wait=120);capture('opened-'+str(cycle));move='DOWN' if kind=='book' else 'RIGHT';back='UP' if kind=='book' else 'LEFT';g.press(move,wait=20);capture('second-'+str(cycle));g.press(back,wait=20)
     if cycle<2 or action=='cancel':g.press('B',hold=1,wait=120)
     elif kind=='book':
      selection={'records':0,'scores':1,'trade':2,'empty':2}[action]
      for _ in range(selection):g.press('DOWN',wait=20)
      g.press('A',hold=1,wait=120)
      if action=='empty':
       # The refusal is modal; after closing it the original menu stays open.
       capture('empty');g.press('B',hold=1,wait=120);g.press('B',hold=1,wait=120)
     else:
      if action=='no':g.press('RIGHT',wait=20)
      g.press('A',hold=1,wait=120)
      if variant==0 and action=='yes':capture('overwrite');g.press('A',hold=1,wait=120)
     require(len(returns)==cycle+1,'Book/travel failed to return: '+case)
   require(g.snapshot().battery==battery and bytes(m[0x0200DF28:0x0200E888])==inventory,'Book/travel prompt changed save/items');require(not c.active,'Book/travel left active text')
   if kind=='travel' and variant==0 and action=='yes':require(getter,'Saved name getter missing')
   results.append({'case':case,'kind':kind,'variant':variant,'action':action,'profile':profile,'inputs':g.inputs,'overrides':overrides,'reads':c.reads,'returns':returns,'getter':getter,'creates':creates,'caller_guard_abi_preserved':True,'visible_pixels_checked':pixels,'images':images})
 report={'passed':True,'rom_sha256':digest(rom),'cases':results,'scope':'Controlled bank-call entry into complete50AA8 record menu or524F4 travel prompt; native window/cursor/choice/results, twice cancel/reopen, final pixels, caller guards/ABI and unchanged inventory/battery. Availability/storage gates and saved-header name profiles are explicitly controlled. Ordinary script routing, item trading and actual travel/save effects remain excluded.'};(out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print('Book/travel:',len(results),'passed')
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,default=ROOT/'build/english');run(p.parse_args().source)
