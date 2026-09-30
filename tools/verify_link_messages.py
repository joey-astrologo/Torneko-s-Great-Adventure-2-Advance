"""Controlled original link message producers, formatting and native modals."""
import argparse,json,struct
from pathlib import Path
import mgba.log
from tools.rom import ROOT,digest,require
from tools.emulator import Session,Debugger,ffi
from tools.dialogue_checks import TextChecks
from tools.bakery_playtest import service_ready
from tools.verify_result_ui import native_format
from tools.compact_font import encode,measure

def run(source):
 out=source/'link-message-validation';rom=(source/'torneko-2-english.gba').read_bytes();b=json.loads((source/'build.json').read_text());require(digest(rom)==b['output_sha256'],'Stale link ROM');mgba.log.silence();fixture=service_ready(rom,out)
 rows={r['source']['offset']:r for r in b['link_text']['entries']};resources={r['offset']+0x08000000:r for r in rows.values() if not r['field']};results=[]
 widest='W'*(162//measure('W'))
 while measure(widest)<162:widest+='.' if measure(widest+'.')<=162 else 'i'
 require(measure(widest)==162,'Link maximum item field width differs')
 profiles={'ordinary':encode('Iron Arrow'),'maximum-width':encode(widest),'maximum-bytes':encode('i'*31)}
 cases=[('error',i,'dismiss',None) for i in range(5)]+[(kind,0,action,profile) for kind in ('connect','repeat','item') for action in ('yes','no','cancel') for profile in (profiles if kind=='item' else (None,))]+[('instruction',0,'dismiss',None)]
 for kind,index,action,profile in cases:
  case=f'{kind}-{index}-{action}-{profile}';print('Link text:',case,flush=True)
  with Session(rom,out/case) as g:
   g.restore(fixture);m=g.core.memory;c=TextChecks(g,dict(resources));initial=[];returns=[];overrides=[];pending={};formats=[];modals=[];modal_returns=[];draws=[];images={};pixels=0
   inventory=bytes(m[0x0200DF28:0x0200E888]);hero=m.u32[0x02001624];gold=m.u32[hero+0x60]
   owner=0x57C1C if kind=='error' else 0x58084 if kind=='instruction' else 0x57C54
   end=0x57C4A if kind=='error' else 0x58092 if kind=='instruction' else 0x57DAC
   modal_end={'error':0x57C0C,'connect':0x57D3C,'repeat':0x57D68,'item':0x57D1E,'instruction':0x57C0C}[kind]
   target=rows[{'error':0x6EBD0,'connect':0x6EC10,'repeat':0x6EC60,'item':0x6EBF4,'instruction':0x6ECB8}[kind]]
   def reg(e,i,v,reason):overrides.append({'event':e,'register':i,'after':v,'reason':reason});g.core.cpu.gprs[i]=v
   def jump(e,at,reason):overrides.append({'event':e,'pc_after':at+0x08000000,'reason':reason});require(g.core._core.writeRegister(g.core._core,b'pc',ffi.new('uint32_t*',at+0x08000000)),'Link redirect failed')
   def write(at,raw,reason):
    overrides.append({'address':at,'before':bytes(m[at:at+len(raw)]).hex(),'after':raw.hex(),'reason':reason})
    for i,v in enumerate(raw):m.u8[at+i]=v
   def callback(e):
    a,r=e['address'],e['registers']
    if a==0x0801DFAC and not initial:
     initial.append(e|{'guard':bytes(m[r[13]:r[13]+32]).hex()})
     if kind=='error':reg(e,0,index,'Select original bounded link error table index.')
     jump(e,owner,'Controlled bank call into complete link-owner frame; no connected peer.');return
    if not initial or returns:return
    if a==0x08057C5E:
     for register,literal in ((6,0x57DBC),(7,0x57DC0)):reg(e,register,struct.unpack_from('<I',rom,literal)[0],'Original modal flag globals.')
     reg(e,4,0,'Original zero callback/argument.');reg(e,5,0x200,'Original message flag mask.')
     if kind=='item':
      raw=profiles[profile];require(len(raw)<=64,'Link item scratch exceeds64');write(r[13]+8,raw.ljust(64,b'\0'),'Controlled64-byte item formatter result; item generation separately scoped.');reg(e,8,r[13]+0x48,'Original128-byte message output.');jump(e,0x57CF0,'Original item confirmation formatter and modal block; storage selection excluded.')
     else:jump(e,0x57D22 if kind=='connect' else 0x57D4E,'Original prompt flag/pointer loads and complete Yes/No modal; link transfer excluded.')
    if a==0x08000FB8 and r[1]==target['offset']+0x08000000:
     require(kind in ('error','item'),'Unexpected link formatter');expected_argument=rows[(0x6EBB0,0x6EB94,0x6EB74,0x6EB58,0x6EB38)[index]]['offset']+0x08000000 if kind=='error' else r[13]+8
     require(r[2]==expected_argument,'Link native field source differs');raw=native_format(bytes.fromhex(target['encoded_hex']),[r[2]],m);require(len(raw)<=target['maximum_bytes']<=128,'Link format exceeds128');pending.update(regs=r,raw=raw,guard=bytes(m[r[0]+128:r[0]+144]));formats.append({'entry':e,'raw_hex':raw.hex(),'bytes':len(raw)})
    if pending and a==(pending['regs'][14]&~1):
     old=pending['regs'];raw=pending['raw'];require(bytes(m[old[0]:old[0]+len(raw)])==raw and bytes(m[old[0]+128:old[0]+144])==pending['guard'] and r[4:12]==old[4:12] and r[13]==old[13],'Link output/guard/formatter ABI differs');c.resources[old[0]]=target|{'encoded_hex':raw.hex()};pending.clear()
    if a==0x08015A34:
     require(r[0] in c.resources and c.resources[r[0]]['id']==target['id'],'Link modal selected unexpected English');require(r[2]==int(kind in ('connect','repeat','item')),'Link modal choice mode differs');modals.append(e)
    if a in (0x08001750,0x08001888):draws[:]=[d for d in draws if d['window']!=r[0]]
    if a==0x080021B4 and r[1] in c.resources:
     w=r[0];require(bytes(m[w+4:w+6])==bytes((28,2)),'Link original224px/two-row window differs')
    if a==0x08001BC4 and c.active:
     w=r[0];key=(w,r[1],r[13],r[14],m.u8[w+2],m.u8[w+3])
     if not draws or draws[-1]['key']!=key:draws.append({'key':key,'window':w,'code':r[1],'x':m.u8[w+2],'y':m.u8[w+3],'origin':[m.u8[w],m.u8[w+1]],'foreground':m.u8[0x020000C2],'bank':m.u16[m.u32[w+12]]>>12})
    if a in c.ADDRESSES:c.callback(e)
    if a==modal_end+0x08000000:
     old=modals[-1]['registers'];require(r[4:12]==old[4:12] and r[13]==old[13],'Link modal ABI differs');require(kind in ('error','instruction') or r[0]==int(action=='yes'),'Link choice result differs');modal_returns.append(e)
     if kind not in ('error','instruction'):jump(e,0x57DA0,'Skip transfer/repeat routing after actual modal result; original owner epilogue.')
    if a==0x08057C3C and kind=='error':jump(e,0x57C40,'Exclude post-error storage sort; original -1 result and epilogue execute.')
    if a==0x0805808C and kind=='instruction':jump(e,0x58090,'Instruction modal complete; storage picker tested separately.')
    if a==end+0x08000000:
     old=initial[0]['registers'];require(r[4:12]==old[4:12] and r[13]==old[13] and r[1 if kind in ('error','instruction') else 0]==old[14] and bytes(m[r[13]:r[13]+32]).hex()==initial[0]['guard'],'Link owner caller ABI/guard differs');returns.append(e)
   def capture(tag):
    nonlocal pixels
    g.frames(8);pic=g.capture(tag);images[tag+'.png']=digest((g.output/(tag+'.png')).read_bytes());require(draws and not c.active,'Link text incomplete')
    for d in draws:
     glyph,_=c.glyph_record(d['code']);colour=m.u16[0x05000000+2*(16*d['bank']+d['foreground'])];rgb=tuple(((colour>>s)&31)*255//31 for s in (0,5,10))
     for y,line in enumerate(glyph['rows']):
      for x,bit in enumerate(line):require((pic.getpixel((d['origin'][0]+d['x']+x,d['origin'][1]+16*d['y']+y))==rgb)==(bit=='#'),'Link final pixels differ');pixels+=1
   with Debugger(g,callback,max_events=180000) as d:
    for a in set(c.ADDRESSES)|{0x0801DFAC,0x08057C5E,0x08000FB8,0x08057C36,0x08057CFA,0x08015A34,modal_end+0x08000000,0x08057C3C,0x0805808C,end+0x08000000,0x08001750,0x08001888}:d.breakpoint(a)
    g.press('A',hold=1,wait=120);capture('opened')
    if action=='no':g.press('RIGHT',wait=20);capture('no-selected')
    g.press('B' if action=='cancel' else 'A',hold=1,wait=120)
    require(len(returns)==len(modals)==len(modal_returns)==len(c.reads)==1 and not c.active and not pending and len(formats)==int(kind in ('error','item')),'Link message route incomplete')
   require(bytes(m[0x0200DF28:0x0200E888])==inventory and m.u32[hero+0x60]==gold and g.snapshot().battery==fixture.battery,'Link message changed inventory/gold/save')
   results.append({'case':case,'kind':kind,'index':index,'profile':profile,'action':action,'inputs':g.inputs,'overrides':overrides,'reads':c.reads,'formats':formats,'modals':modals,'modal_returns':modal_returns,'returns':returns,'caller_guard_abi_preserved':True,'visible_pixels_checked':pixels,'images':images});(out/'partial.json').write_text(json.dumps(results,indent=2)+'\n')
 report={'passed':True,'rom_sha256':digest(rom),'cases':results,'scope':'Controlled bank-call entry into original full link-owner frames. Five native error selectors,128-byte error/item formatting with guards, original224px/two-row modals, actual Yes/No/B results, maximum162px/64-byte item fields, final pixels and modal/caller ABI. Item-generation result is explicitly controlled. Serial transfer, storage sort/picker and natural link-menu access excluded. Inventory/gold/battery unchanged.'};(out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print('Link messages:',len(results),'passed')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--source',type=Path,default=ROOT/'build/english');run(p.parse_args().source)
