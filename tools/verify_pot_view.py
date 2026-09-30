import argparse,json,struct
from pathlib import Path
import mgba.log
from tools.rom import ROOT,digest,require
from tools.emulator import Session,Debugger
from tools.dialogue_checks import TextChecks,rendered_codes as original_codes
from unittest.mock import patch

def pot_codes(payload,*args,**kwargs):
 if payload.startswith(b'\x07'):
  require(payload.endswith(b'\x08\0'),'Unexpected legacy pot controls')
  payload=payload[1:-2]+b'\0'
 return original_codes(payload,*args,**kwargs)
class PotChecks(TextChecks):
 def callback(self,e):
  with patch('tools.dialogue_checks.rendered_codes',pot_codes):super().callback(e)


def run(source=ROOT/'build/english'):
 out=source/'pot-view-validation';mgba.log.silence();rom=(source/'torneko-2-english.gba').read_bytes();build=json.loads((source/'build.json').read_text());require(digest(rom)==build['output_sha256'],'Stale pot-view ROM')
 from tools import verify_player_status_prototype as status
 prior=status.OUT
 try:status.OUT=out;fixture=status.ready(rom,build)
 finally:status.OUT=prior
 rows={r['offset']+0x08000000:r for r in build['pot_view']['entries']};results=[]
 for ident,capacity in [(154,0),(154,3),(157,0),(157,3),(158,3),(159,3),(160,3),(161,3),(164,0),(164,3),(162,3)]:
  case=f'{ident}-{capacity}';print('Pot view:',case,flush=True)
  with Session(rom,out/case) as g:
   g.restore(fixture);m=g.core.memory;overrides=[];initial=[];returns=[];draws=[];images={};pixels=0;copies=[];pending={};ram_labels={};c=PotChecks(g,dict(rows))
   def write(at,data):
    overrides.append({'address':at,'before':bytes(m[at:at+len(data)]).hex(),'after':data.hex()})
    for i,v in enumerate(data):m.u8[at+i]=v
   item=bytearray(120);struct.pack_into('<I',item,0,0xC8000000);item[4]=capacity;item[5]=1;item[8]=bytes(m[0x020013D0:0x020014D0]).index(ident);write(0x0200DF28,item)
   db=0x02003BAC+20*ident;write(db,struct.pack('<I',m.u32[db]|0x40000000));inventory=bytes(m[0x0200DF28:0x0200E888]);hero=m.u32[0x02001624];gold=m.u32[hero+0x60]
   def callback(e):
    a,r=e['address'],e['registers']
    if a==0x0805CF54 and r[1] in rows:
     row=rows[r[1]];require(r[14]==0x08018FB1 and r[0]==r[13]+8,'Pot label copy owner differs');pending.update(regs=r,row=row,guard=bytes(m[r[0]+64:r[0]+80]))
    if a==0x08018FB0 and pending:
     old=pending['regs'];row=pending['row'];raw=bytes.fromhex(row['encoded_hex']);require(bytes(m[old[0]:old[0]+len(raw)])==raw and bytes(m[old[0]+64:old[0]+80])==pending['guard'] and r[4:12]==old[4:12] and r[13]==old[13],'Pot label copy/guard/ABI differs');ram_labels[old[0]]=row;copies.append({'id':row['id'],'guard_abi_preserved':True});pending.clear()
    if a==0x080021B4 and r[1] in ram_labels:
     row=ram_labels[r[1]];raw=bytes.fromhex(row['encoded_hex']);c.resources.pop(r[1],None)
     if bytes(m[r[1]:r[1]+len(raw)])==raw:c.resources[r[1]]=row
    if a==0x08018CE8:initial.append(e|{'guard':bytes(m[r[13]:r[13]+32]).hex()});draws.clear()
    if a==0x080021B4 and r[1] in rows:require(m.u8[r[0]+4]==21,'Pot-view width differs')
    if a==0x08001BC4 and c.active:
     w=r[0];key=(w,r[1],r[13],r[14],m.u8[w+2],m.u8[w+3])
     if not draws or draws[-1]['key']!=key:draws.append({'key':key,'window':w,'code':r[1],'x':m.u8[w+2],'y':m.u8[w+3],'origin':[m.u8[w],m.u8[w+1]],'foreground':m.u8[0x020000C2],'bank':m.u16[m.u32[w+12]]>>12})
    if a in c.ADDRESSES:c.callback(e)
    if a==0x080190DA:
     old=initial[-1]['registers'];require(r[4:12]==old[4:12] and r[13]==old[13] and r[1]==old[14] and bytes(m[r[13]:r[13]+32]).hex()==initial[-1]['guard'],'Pot-view renderer caller ABI differs');returns.append(e)
   def capture(tag):
    nonlocal pixels
    g.frames(3);pic=g.capture(tag);images[tag+'.png']=digest((g.output/(tag+'.png')).read_bytes());require(draws and not c.active,'Pot-view no complete English render')
    for d in draws:
     glyph,_=c.glyph_record(d['code']);colour=m.u16[0x05000000+2*(16*d['bank']+d['foreground'])];rgb=tuple(((colour>>s)&31)*255//31 for s in (0,5,10))
     for y,line in enumerate(glyph['rows']):
      for x,bit in enumerate(line):require((pic.getpixel((d['origin'][0]+d['x']+x,d['origin'][1]+16*d['y']+y))==rgb)==(bit=='#'),'Pot-view final pixels differ: '+repr((case,tag,hex(d['code']),d['x']+x,16*d['y']+y)));pixels+=1
   with Debugger(g,callback,max_events=160000) as debug:
    for a in set(c.ADDRESSES)|{0x08018CE8,0x080190DA,0x0805CF54,0x08018FB0}:debug.breakpoint(a)
    g.press('B',hold=8,wait=120);g.press('A',wait=120)
    for cycle in range(3):
     g.press('A',wait=90);actions=[]
     for i in range(7):
      n=m.u16[0x0200CDD0+2*i]
      if not n:break
      actions.append(n)
     require(42 in actions,'Pot-view native View action missing: '+repr(actions))
     for _ in range(actions.index(42)):g.press('DOWN',wait=20)
     g.press('A',wait=90);capture('view-'+str(cycle));g.press('B',wait=90)
    require(len(initial)==len(returns)==3 and c.reads and not c.active,'Pot-view render/reopen incomplete: '+repr((len(initial),len(returns))))
   require(bytes(m[0x0200DF28:0x0200E888])==inventory and m.u32[hero+0x60]==gold and g.snapshot().battery==fixture.battery,'Pot-view browsing changed items/gold/battery')
   results.append({'case':case,'item_id':ident,'capacity':capacity,'inputs':g.inputs,'overrides':overrides,'reads':c.reads,'copies':copies,'returns':returns,'caller_guard_abi_preserved':True,'visible_pixels_checked':pixels,'images':images})
 report={'passed':True,'rom_sha256':digest(rom),'cases':results,'scope':'Controlled pot identities/capacities and known flags, followed by ordinary inventory View, B and twice reopening. Native18CE8 branch/row selection, exact original168px geometry, complete visible pixels, full renderer ABI and unchanged inventory/gold/battery. Empty and concealed content labels are checked; ordinary acquisition and existing-content mechanics remain separate.'}
 (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print('Pot views:',len(results),'passed')
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,default=ROOT/'build/english');run(p.parse_args().source)
