"""Reference-list selection, full native pages, locked entries and close/reopen."""
import argparse,json,struct
from pathlib import Path
import mgba.log
from tools.rom import ROOT,digest,require
from tools.emulator import Session,Debugger,ffi
from tools.dialogue_checks import TextChecks
from tools.verify_service_ui import materialize


def run(source,only=None):
 out=source/'reference-lists-validation';mgba.log.silence();rom=(source/'torneko-2-english.gba').read_bytes();build=json.loads((source/'build.json').read_text());require(digest(rom)==build['output_sha256'],'Stale reference list ROM')
 from tools import verify_player_status_prototype as status
 prior=status.OUT
 try:status.OUT=out;fixture=status.ready(rom,build)
 finally:status.OUT=prior
 results=[];cases=[(f'categories-{mask}',None,False,mask) for mask in (1,3,7)]+[(kind+('-known' if known else '-locked'),kind,known,7) for kind in ('scroll','skill','spell') for known in (True,False)]
 names={}
 for key,kind in (('items','scroll'),('skill_info','skill'),('spell_info','spell')):
  for row in build[key]['entries']:
   if row['id'].startswith(('item.name.','skill.name.','spell.name.')):names[row['offset']+0x08000000]=row|{'kind':kind,'entity':int(row['id'].split('.')[-1])}
 labels={r['offset']+0x08000000:r|{'layout':{'pages':[[r['id']]]}} for r in build['reference_lists']['entries']}
 returns_at={0x08020A74:('scroll',64),0x08020A9C:('scroll',64),0x08020CC0:('skill',64),0x08020CE8:('skill',64),0x08020F00:('spell',64),0x08020F24:('spell',64),0x0801CFF2:('page',16)}
 scroll_ids=set(rom[0x148343:0x148343+27]);eligible={'scroll':scroll_ids,'skill':{r['id'] for r in build['skill_info']['definitions'] if r['menu_eligible']},'spell':{r['id'] for r in build['spell_info']['definitions'] if r['menu_eligible']}}
 for name,kind,known,mask in cases:
  if only and only!=name:continue
  print('Reference lists:',name,flush=True)
  with Session(rom,out/name) as g:
   g.restore(fixture);m=g.core.memory;initial=[];ends=[];overrides=[];formats=[];pending=[];draws=[];images={};pixels=0;creations=[];infos=[];c=TextChecks(g,dict(labels))
   def write(at,data):
    overrides.append({'address':at,'before':bytes(m[at:at+len(data)]).hex(),'after':data.hex()})
    for i,v in enumerate(data):m.u8[at+i]=v
   def jump(e,at):
    overrides.append({'event':e,'pc_after':at,'reason':'Controlled native reference menu invocation; original entire function/prologue executes.'});require(g.core._core.writeRegister(g.core._core,b'pc',ffi.new('uint32_t*',at)),'Reference menu dispatch failed')
   write(m.u32[0x02001624]+0x90,b'\1')
   for ident in scroll_ids:
    at=0x02003BAC+20*ident;write(at,struct.pack('<I',(m.u32[at]|0x400000) if known else (m.u32[at]&~0x400000)))
   write(0x02004DFA,bytes([int(known)])*128);write(0x02004DBD,bytes([int(known)])*61)
   initial_inventory=bytes(m[0x0200DF28:0x0200DF28+2400]);initial_skills=bytes(m[0x02004DFA:0x02004E7A]);initial_spells=bytes(m[0x02004DBD:0x02004DFA])
   def callback(e):
    a,r=e['address'],e['registers']
    if a==0x08020F9C and not initial:
     initial.append(e|{'guard':bytes(m[r[13]:r[13]+32]).hex()});overrides.append({'event':e,'r1_after':mask});g.core.cpu.gprs[1]=mask;jump(e,0x08020760);return
    if not initial or ends:return
    if a==0x08001798:creations.append(e)
    if a in (0x08001750,0x08001888):draws[:]=[d for d in draws if d['window']!=r[0]]
    if a in (0x08017A4C,0x0802172C,0x08022828):infos.append(e)
    if a==0x08000FB8 and (r[14]&~1) in returns_at:
     family,cap=returns_at[r[14]&~1];require(r[0]==r[13],'Reference row stack ownership differs')
     src=bytes(m[r[1]:r[1]+30]).split(b'\0')[0]+b'\0';payload=(b'%2d/%2d\0' % tuple(r[2:4])) if family=='page' else materialize(src,r[2:4],m);require(len(payload)<=cap,'Reference row buffer exceeds capacity')
     found=[names[v] for v in r[2:4] if v in names];require(all(x['kind']==family for x in found),'Reference row used wrong name definition')
     if family!='page':require(bool(found)==known,'Reference row name eligibility differs')
     pending.append({'r':r,'raw':payload,'guard':bytes(m[r[0]+cap:r[0]+cap+16]),'capacity':cap,'family':family,'entities':[x['entity'] for x in found],'label_ids':[labels[v]['id'] for v in r[2:4] if v in labels]})
    if pending and a==(pending[-1]['r'][14]&~1):
     p=pending.pop();old=p['r'];at=old[0];cap=p['capacity'];require(bytes(m[at:at+len(p['raw'])])==p['raw'] and bytes(m[at+cap:at+cap+16])==p['guard'] and r[4:12]==old[4:12] and r[13]==old[13],'Reference format guard/ABI differs')
     ident='reference-row.'+p['family'];c.resources[at]={'id':ident,'encoded_hex':p['raw'].hex(),'layout':{'pages':[[ident]]}};formats.append({'id':ident,'hex':p['raw'].hex(),'capacity':cap,'bytes':len(p['raw']),'entities':p['entities'],'family':p['family'],'label_ids':p['label_ids'],'guard_abi_preserved':True})
    if a==0x08001BC4 and c.active:
     w=r[0];key=(w,r[1],r[13],r[14],m.u8[w+2],m.u8[w+3]);glyph,_=c.glyph_record(r[1]);limit=m.u8[w+4]*8
     # Exact text region and glyph edge are checked against each unchanged window.
     require(m.u8[w+2]+glyph['advance']<=limit,'Reference glyph exceeds native window')
     if not draws or draws[-1]['key']!=key:draws.append({'key':key,'window':w,'code':r[1],'x':m.u8[w+2],'y':m.u8[w+3],'origin':[m.u8[w],m.u8[w+1]],'foreground':m.u8[0x020000C2],'bank':m.u16[m.u32[w+12]]>>12})
    if a==0x080021B4 and r[1] in c.resources and 0x02000000<=r[1]<0x04000000 and m.u8[r[1]]==0:c.resources.pop(r[1])
    if a in c.ADDRESSES:c.callback(e)
    if a==0x080208CA:
     old=initial[0]['registers'];require(r[4:12]==old[4:12] and r[13]==old[13] and r[0]==old[14] and bytes(m[r[13]:r[13]+32]).hex()==initial[0]['guard'],'Reference menu caller ABI differs');ends.append(e)
   def capture(tag):
    nonlocal pixels
    g.frames(90);pic=g.capture(tag);images[tag+'.png']=digest((g.output/(tag+'.png')).read_bytes());require(draws,'Reference list has no English draws')
    for d in draws:
     glyph,_=c.glyph_record(d['code']);colour=m.u16[0x05000000+2*(16*d['bank']+d['foreground'])];rgb=tuple(((colour>>s)&31)*255//31 for s in (0,5,10))
     for y,line in enumerate(glyph['rows']):
      for x,bit in enumerate(line):
       px=d['origin'][0]+d['x']+x;py=d['origin'][1]+d['y']*16+y;require((pic.getpixel((px,py))==rgb)==(bit=='#'),'Reference list pixels differ: '+repr((name,tag,hex(d['code']),px,py)));pixels+=1
   with Debugger(g,callback,max_events=500000) as debug:
    for a in set(c.ADDRESSES)|set(returns_at)|{0x08020F9C,0x080208CA,0x08000FB8,0x08001798,0x08001750,0x08001888,0x08017A4C,0x0802172C,0x08022828}:debug.breakpoint(a)
    g.press('B',hold=8,wait=120);g.press('DOWN',wait=30);g.press('A',wait=120);capture('categories');require(creations[-1]['registers'][:4]==[1,3,8,mask.bit_count()],'Reference category geometry differs')
    g.press('UP',wait=20);g.press('DOWN',wait=20);capture('category-cursor-wrap')
    if kind:
     for _ in range(('scroll','skill','spell').index(kind)):g.press('DOWN',wait=20)
     g.press('A',wait=120);capture('page-0');pages=(len(eligible[kind])+7)//8
     for page in range(1,pages):g.press('RIGHT',wait=60);capture('page-'+str(page))
     g.press('RIGHT',wait=60);capture('page-wrap');g.press('UP',wait=20);g.press('DOWN',wait=20);capture('row-cursor-wrap')
     require((24*8-4)-((1+21)*8+4)==8,'Reference page border gap differs')
     if not known:
      g.press('A',wait=60);require(not infos,'Locked reference entry opened Info');capture('locked-refusal')
     g.press('B',wait=60);capture('categories-restored')
     g.press('A',wait=60);capture('reopened');g.press('B',wait=60);capture('cancelled-again')
    g.press('B',wait=60)
   covered={i for f in formats if f['family']==kind for i in f['entities']}
   if kind:require(covered==(eligible[kind] if known else set()),'Reference name coverage differs: '+repr((kind,covered,eligible[kind])))
   require(len(initial)==len(ends)==1 and not c.active and not pending and g.snapshot().battery==fixture.battery,'Reference menu did not finish cleanly')
   require(bytes(m[0x0200DF28:0x0200DF28+2400])==initial_inventory and bytes(m[0x02004DFA:0x02004E7A])==initial_skills and bytes(m[0x02004DBD:0x02004DFA])==initial_spells,'Reference browsing changed inventory/eligibility')
   results.append({'case':name,'kind':kind,'known':known,'mask':mask,'covered_ids':sorted(covered),'formats':formats,'reads':c.reads,'inputs':g.inputs,'overrides':overrides,'creations':creations,'caller_guard_abi_preserved':True,'visible_pixels_checked':pixels,'images':images})
 report={'passed':True,'rom_sha256':digest(rom),'cases':results,'scope':'Controlled original20760 reference-menu invocation with native category navigation,27 scroll/100 skill/50 spell selectors, eligible and locked rows, all pages/cursor wrapping, refusal, cancellation and repeated reopening. Eligibility RAM alone is controlled. Original64px categories and168px rows with6px cursor reserves,40px page indicators,8px outer-border gap,64-byte row/16-byte indicator buffers and caller ABI/pixels/battery checked. Natural unlocks, source-script invocation and item-writing input matching remain separate.'}
 (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print('Reference lists:',len(results),'passed',flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,default=ROOT/'build/english');p.add_argument('--only');a=p.parse_args();run(a.source,a.only)
