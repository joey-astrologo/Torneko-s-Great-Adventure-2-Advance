"""Controlled fused equipment, ordinary inventory Info and native selection."""
import argparse,json,struct
from pathlib import Path
import mgba.log
from tools.rom import ROOT,digest,require
from tools.emulator import Session,Debugger
from tools.service_fixtures import dungeon
from tools.verify_items import ItemChecks
from tools.audit_menu_layouts import Observer,parent_image

def run(source,only=None):
 out=source/'ability-info-validation';mgba.log.silence();rom=(source/'torneko-2-english.gba').read_bytes();build=json.loads((source/'build.json').read_text());require(digest(rom)==build['output_sha256'],'Stale ability Info ROM')
 fixture=dungeon(rom,build);resources={r['offset']+0x08000000:r for r in build['ability_info']['entries']};results=[]
 cases=[(f'{kind}-{bit}',kind,1<<bit,0) for kind in (0,1) for bit in range(20)]
 cases += [('special',0,(1<<16)|(1<<4),0),('all-sword',0,0xfffff,0),('all-shield',1,0xfffff,0),('highlight-sword',0,0xfffff,0xfffff),('highlight-shield',1,0xfffff,0xfffff)]
 for case,kind,bits,highlight in cases:
  if only and case not in only:continue
  print('Ability Info:',case,flush=True)
  with Session(rom,out/case) as g:
   g.restore(fixture);m=g.core.memory;overrides=[];initial=[];returns=[];draws=[];images={};pixels=0;copies=[];pending={};headers=[];c=ItemChecks(g,build);o=Observer(g)
   def write(at,data):
    overrides.append({'address':at,'before':bytes(m[at:at+len(data)]).hex(),'after':data.hex()})
    for i,v in enumerate(data):m.u8[at+i]=v
   ident=31 if kind else 1;item=bytearray(120);struct.pack_into('<I',item,0,0xC8200000|bits);item[5]=1;item[8]=bytes(m[0x020013D0:0x020014D0]).index(ident);write(0x0200DF28,item)
   db=0x02003BAC+20*ident;write(db,struct.pack('<I',m.u32[db]|0x40000000));inventory=bytes(m[0x0200DF28:0x0200E888]);hero=m.u32[0x02001624];gold=m.u32[hero+0x60]
   def callback(e):
    a,r=e['address'],e['registers']
    if a==0x08017A4C:
     initial.append(e|{'guard':bytes(m[r[13]:r[13]+32]).hex()});draws.clear()
     if highlight:
      overrides.append({'event':e,'r3_after':highlight,'reason':'Exercise the original Info highlight mask while preserving ordinary entry, complete frame and selection.'});g.core.cpu.gprs[3]=highlight
    if (a==0x0805CF54 and r[1] in resources) or (a==0x08000FB8 and r[14]==0x08017CC7):
     pointer=r[1] if a==0x0805CF54 else r[2];row=resources[pointer];selected=m.u32[0x0200CDC4];index=40 if kind==0 and selected==16 and bits&16 else kind*20+selected
     require(row['index']==index and r[0]==r[13]+0x108,'Ability Info native source selection differs')
     raw=bytes.fromhex(row['encoded_hex']);raw=(b'\x03\x05'+raw) if a==0x08000FB8 else raw
     require(bool(highlight&(1<<selected))==(a==0x08000FB8),'Ability Info highlight selection differs')
     saved={'regs':r,'row':row,'raw':raw,'guard':bytes(m[r[0]+256:r[0]+272]),'selected':selected}
     if pending:require(pending==saved,'Different pending Info copy')
     pending.update(saved)
    if a in (0x08017CC6,0x08017CDC) and pending:
     old=pending['regs'];row=pending['row'];raw=pending['raw'];require(bytes(m[old[0]:old[0]+len(raw)])==raw and bytes(m[old[0]+256:old[0]+272])==pending['guard'] and r[4:12]==old[4:12] and r[13]==old[13],'Ability Info body copy/guard/ABI differs')
     c.materialized[old[0]]=row|{'encoded_hex':raw.hex()};copies.append({'id':row['id'],'selected':pending['selected'],'bytes':len(raw),'highlighted':bool(highlight&(1<<pending['selected'])),'guard_abi_preserved':True});pending.clear();draws.clear()
    if a==0x08017C1C:headers.append(bytes(m[r[13]+8:r[13]+264]).split(b'\0',1)[0].hex())
    if a==0x080021B4 and r[1] in c.materialized and c.materialized[r[1]]['id'].startswith('ability-info.'):
     require(m.u8[r[0]+4]==28 and m.u8[r[0]+5]==7 and m.u8[r[0]+3]==(4 if bits.bit_count()>12 else 3),'Ability Info original window/row changed')
    if a==0x08001BC4 and c.active and c.active['id'].startswith('ability-info.'):
     w=r[0];key=(w,r[1],r[13],r[14],m.u8[w+2],m.u8[w+3])
     if not draws or draws[-1]['key']!=key:draws.append({'key':key,'code':r[1],'x':m.u8[w+2],'y':m.u8[w+3],'origin':[m.u8[w],m.u8[w+1]],'foreground':m.u8[0x020000C2],'bank':m.u16[m.u32[w+12]]>>12})
    if a in c.ADDRESSES:c.callback(e)
    if a in o.ADDRESSES:o.callback(e)
    if a==0x08017EEC:
     old=initial[-1]['registers'];require(r[4:12]==old[4:12] and r[13]==old[13] and r[0]==old[14] and bytes(m[r[13]:r[13]+32]).hex()==initial[-1]['guard'],'Ability Info caller ABI differs');returns.append(e)
   def capture(tag):
    nonlocal pixels
    g.frames(3);pic=g.capture(tag);images[tag+'.png']=digest((g.output/(tag+'.png')).read_bytes());require(draws and not c.active,'Ability Info missing complete English body')
    for d in draws:
     glyph,_=c.glyph_record(d['code']);colour=m.u16[0x05000000+2*(16*d['bank']+d['foreground'])];rgb=tuple(((colour>>s)&31)*255//31 for s in (0,5,10))
     for y,line in enumerate(glyph['rows']):
      for x,bit in enumerate(line):require((pic.getpixel((d['origin'][0]+d['x']+x,d['origin'][1]+16*d['y']+y))==rgb)==(bit=='#'),'Ability Info final pixels differ: '+repr((case,tag,hex(d['code']),d['x']+x,16*d['y']+y)));pixels+=1
   with Debugger(g,callback,max_events=300000) as debug:
    for a in set(c.ADDRESSES+o.ADDRESSES)|{0x08017A4C,0x08017EEC,0x08017CC6,0x08017CDC,0x08017C1C}:debug.breakpoint(a)
    g.press('B',hold=8,wait=120);g.press('A',wait=120);before=parent_image(g)
    for cycle in range(3):
     g.press('A',wait=90);actions=[]
     for i in range(7):
      n=m.u16[0x0200CDD0+2*i]
      if not n:break
      actions.append(n&127)
     require(40 in actions,'Native Info action missing')
     for _ in range(actions.index(40)):g.press('DOWN',wait=20)
     g.press('A',wait=90);capture('info-'+str(cycle))
     if cycle==0 and bits.bit_count()>1:
      for i in range(bits.bit_count()-1):g.press('RIGHT',wait=15);capture('select-'+str(i+1))
     g.press('B',wait=90)
     require(parent_image(g)==before,'Ability Info did not restore inventory parent')
    require(len(initial)==len(returns)==3 and c.reads and not c.active and not pending and not c.stack,'Ability Info render/reopen incomplete')
   require(bytes(m[0x0200DF28:0x0200E888])==inventory and m.u32[hero+0x60]==gold and g.snapshot().battery==fixture.battery,'Ability Info browsing changed items/gold/battery')
   expected={40 if kind==0 and bit==16 and bits&16 else kind*20+bit for bit in range(20) if bits&(1<<bit)}
   require({int(row['id'].split('.')[-1]) for row in copies}==expected,'Ability Info native selection coverage incomplete')
   results.append({'case':case,'kind':kind,'bits':bits,'highlight':highlight,'inputs':g.inputs,'overrides':overrides,'reads':c.reads,'copies':copies,'returns':returns,'header_hex':headers,'caller_guard_abi_preserved':True,'parent_restored':True,'visible_pixels_checked':pixels,'images':images})
 report={'passed':True,'rom_sha256':digest(rom),'cases':results,'scope':'Controlled sword/shield bit fields, ordinary inventory Info, native directional selection and B with twice reopening. Full original renderer/selection/colour branches, 256-byte body guard, caller ABI, original224px by7-row geometry, exact body pixels and unchanged inventory/gold/battery. Highlight mask is explicitly injected at the native entry. Question-mark placeholders and impossible ability combinations are renderer stress cases, not claims of natural synthesis availability. Native header property symbols remain separately scoped.'}
 (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print('Ability Info:',len(results),'passed')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--source',type=Path,default=ROOT/'build/english');p.add_argument('--case',action='append');args=p.parse_args();run(args.source,args.case)
