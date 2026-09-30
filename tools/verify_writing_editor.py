"""Actual inventory Write/Name buttons through the full native editor."""
import argparse,json,struct
import mgba.log
from tools.rom import ROOT,digest,require
from pathlib import Path
from tools.emulator import Session,Debugger
from tools.name_entry import EDIT,IDS
from tools.name_entry_route import NameEntryRoute,POSITION,SELECTION
from tools.verify_name_entry import EditorChecks
from tools.dialogue_checks import TextChecks

def run(source=ROOT/'build/english',only=None):
 mgba.log.silence();out=source/'writing-editor-validation';rom=(source/'torneko-2-english.gba').read_bytes();b=json.loads((source/'build.json').read_text())
 from tools import verify_player_status_prototype as status
 prior=status.OUT
 try:status.OUT=out;fixture=status.ready(rom,b)
 finally:status.OUT=prior
 cases=[('spell-long',151,'Lightning Storm',43),('scroll-long',124,'Lyre of Ire',140),('scroll-full',124,'Safe Passage',142),('spell-case',151,'mAgIc BaRrIeR',30),('spell-unknown',151,'Not a spell',0),('ordinary-name',177,'WWWWWWWW',0),('scroll-display',124,'Great room scr.',122),('spell-empty',151,'',0),('wide-japanese',151,'Japanese stress',0)]
 results=[]
 for case,item_id,text,target in cases:
  if only and only!=case:continue
  limit=8 if item_id==177 else 15
  if case=='wide-japanese':
   from tools.review_fonts import extract
   from tools.rom import load_base
   table=b['name_entry']['glyph_table']-0x08000000;base=load_base()
   candidates={ident for page in b['name_entry']['keyboard_pages'][3:] for ident in bytes.fromhex(page)[4:] if 1<ident<0xB9}
   widest=max(candidates,key=lambda ident:extract(base,int.from_bytes(rom[table+2*ident:table+2*ident+2],'big'))['width'])
   entered_ids=bytes([widest])*15
  else:entered_ids=bytes(IDS[c] for c in text)
  print('Writing editor',case,flush=True)
  with Session(rom,out/case) as g:
   g.restore(fixture);m=g.core.memory;overrides=[];initial=[];returns=[];inputs=[];windows=[];name_draws=[];active=False;glyphs=[];lookup=[];matches=[];images={};pixels=0
   def write(at,data):
    overrides.append({'address':at,'before':bytes(m[at:at+len(data)]).hex(),'after':data.hex()})
    for i,v in enumerate(data):m.u8[at+i]=v
   item=bytearray(120);struct.pack_into('<I',item,0,0x80000000 if item_id==177 else 0xC8000000);item[5]=1;item[8]=bytes(m[0x020013D0:0x020014D0]).index(item_id);write(0x0200DF28,item)
   write(m.u32[0x02001624]+0x90,bytes([2 if item_id==151 else 0]))
   db=0x02003BAC+20*item_id;write(db,struct.pack('<I',m.u32[db]&~0x40000000 if item_id==177 else m.u32[db]|0x40000000))
   if target:
    if item_id==151:write(0x02004DBD+target,b'\1')
    else:
     at=0x02003BAC+20*target;write(at,struct.pack('<I',m.u32[at]|0x400000))
   editor=EditorChecks(g,rom,b);checks=TextChecks(g,{})
   def callback(e):
    nonlocal active
    a,r=e['address'],e['registers']
    if a==0x08018284:
     require(not initial and r[0]==0x0200DF28,'Writing editor item/entry differs');initial.append(e|{'guard':bytes(m[r[13]:r[13]+32]).hex(),'working_before':bytes(m[EDIT-4:EDIT+24]).hex()})
    if not initial or returns:return
    if a in (0x08019F68,0x08019F72,0x08001C14):editor.callback(e)
    if a==0x08019F3C:require(r[0]==limit,'Writing input limit differs');inputs.append(e)
    if a==0x08001798:windows.append(e)
    if a==0x08002298 and r[14]==0x080183CB:
     require(r[1]==r[13] and r[13]==initial[0]['registers'][13]-68 and m.u32[r[13]+32]==limit,'Writing display frame differs');active=True;name_draws.clear()
    if a==0x080183CA:active=False
    if a==0x08001BC4 and active:
     w=r[0];key=(w,r[1],r[13],r[14],m.u8[w+2],m.u8[w+3])
     if not name_draws or name_draws[-1]['key']!=key:name_draws.append({'key':key,'window':w,'code':r[1],'x':m.u8[w+2],'y':m.u8[w+3],'origin':[m.u8[w],m.u8[w+1]],'foreground':m.u8[0x020000C2],'bank':m.u16[m.u32[w+12]]>>12})
    if a in (0x08035458,0x0803EF48):
     require(r[1]==EDIT,'Writing matcher input differs');lookup.append(e)
    if a in (0x080354D2,0x0803EFC2):matches.append(e);require(r[0]==(target+(10 if item_id==151 else 0) if target else 0),'Typed English lookup returned wrong target')
    if a==0x0801851A:
     old=initial[0]['registers'];require(r[4:12]==old[4:12] and r[13]==old[13] and r[1]==old[14] and bytes(m[r[13]:r[13]+32]).hex()==initial[0]['guard'],'Writing editor frame/ABI guard differs');returns.append(e)
   def capture(tag):
    nonlocal pixels
    g.frames(8);pic=g.capture(tag);images[tag+'.png']=digest((g.output/(tag+'.png')).read_bytes());require(name_draws and not active,'Writing name display incomplete')
    for d in name_draws:
     glyph,_=checks.glyph_record(d['code']);require(d['x']+glyph['advance']<=(120 if item_id==177 else 224) and d['y']==0,'Writing name clips')
     colour=m.u16[0x05000000+2*(16*d['bank']+d['foreground'])];rgb=tuple(((colour>>s)&31)*255//31 for s in (0,5,10))
     for y,line in enumerate(glyph['rows']):
      for x,bit in enumerate(line):
       require((pic.getpixel((d['origin'][0]+d['x']+x,d['origin'][1]+y))==rgb)==(bit=='#'),'Writing field pixels differ');pixels+=1
   with Debugger(g,callback,max_events=400000) as debug:
    for a in (0x08018284,0x0801851A,0x08019F68,0x08019F72,0x08001C14,0x08019F3C,0x08001798,0x08002298,0x080183CA,0x08001BC4,0x08035458,0x0803EF48,0x080354D2,0x0803EFC2):debug.breakpoint(a)
    g.press('B',hold=8,wait=30);g.press('A',wait=30);g.press('A',wait=30);actions=[]
    for i in range(7):
     n=m.u16[0x0200CDD0+2*i]
     if not n:break
     actions.append(n)
    action=41 if item_id==177 else 33
    require(action in actions,'Write/Name action absent: '+repr(actions))
    for _ in range(actions.index(action)):g.press('DOWN',wait=20)
    g.capture('action');images['action.png']=digest((g.output/'action.png').read_bytes());g.press('A',wait=60);require(len(initial)==1 and inputs and not returns,'Native Write did not open editor')
    require(windows[0]['registers'][:4]==([7,1,15,1] if item_id==177 else [1,1,28,1]) and windows[1]['registers'][:4]==[1,5,28,7],'Writing windows differ')
    route=NameEntryRoute(g,b['name_entry']['keyboard_pages']);capture('empty')
    for ident in entered_ids:route.choose_id(ident)
    expected=entered_ids+b'\1'*(limit-len(entered_ids))+b'\0';require(bytes(m[EDIT:EDIT+limit+1])==expected,'Typed inscription working bytes differ');capture('typed')
    if len(entered_ids)==limit:
     # B must erase at position14 and preserve all earlier bytes, then allow replacement.
     g.frames(60);g.press('B',hold=8,wait=60);require(bytes(m[EDIT:EDIT+limit+1])==expected[:limit-1]+b'\1\0','Long inscription Back corrupted working buffer: '+repr((bytes(m[EDIT:EDIT+16]).hex(),expected.hex(),m.u32[POSITION],m.u32[SELECTION],len(returns))));capture('back');route.choose_id(entered_ids[-1]);capture('retyped')
    if entered_ids:route.confirm()
    else:g.press('B',hold=8,wait=180)
    require(len(returns)==1 and len(lookup)==len(matches)==(0 if item_id==177 or not entered_ids else 1),'Writing lookup/editor did not finish')
    g.frames(180);g.capture('result');images['result.png']=digest((g.output/'result.png').read_bytes())
   ident=m.u8[0x020013D0+m.u8[0x0200DF30]];flags=m.u32[0x0200DF28]
   require(ident==(153 if item_id==151 else target) if target else ident==item_id,'Native inscription item result differs')
   if item_id==177:require(m.u8[db+8]==1 and bytes(m[db+9:db+19])==expected+b'\0','Ordinary custom name storage differs')
   if target:require(flags&0x400000 and (item_id!=151 or m.u8[0x0200DF2C]==target),'Native inscription flags/spell ID differ')
   require(g.snapshot().battery==fixture.battery,'Writing editor changed battery')
   results.append({'case':case,'item_id':item_id,'text':text,'indexed_hex':entered_ids.hex(),'target':target,'inputs':g.inputs,'overrides':overrides,'editor_entry':initial,'editor_return':returns,'lookup':lookup,'matches':matches,'cursor_checks':editor.cursor_checks,'glyphs':sorted(editor.glyphs),'visible_pixels_checked':pixels,'native_item_result_checked':True,'images':images})
 (out/'report.json').write_text(json.dumps({'passed':True,'rom_sha256':digest(rom),'cases':results,'scope':'Controlled item/history setup, followed by actual inventory Write selection, ordinary keyboard button input, full native editor/lookup and inscription outcomes. Long-name Back/replacement, cursor/visible pixels, complete owner ABI and battery preservation checked. Natural item acquisition remains separate.'},indent=2)+'\n')
 print('Writing editor',len(results),'passed')

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,default=ROOT/'build/english');p.add_argument('--only');a=p.parse_args();run(a.source,a.only)
