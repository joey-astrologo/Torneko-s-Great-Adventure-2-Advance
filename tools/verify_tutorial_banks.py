"""Native soldier/adventurer help menus and their complete direct prose."""
import argparse,json,struct
from pathlib import Path
import mgba.log
from tools.rom import ROOT,digest,require,load_base
from tools.opening_text import BANK_RAM,banks
from tools.event_text import table_entries
from tools.lz77 import decompress
COHORTS={4:[2],5:[2],6:[3],7:[5,6],10:[3],11:[4],12:[5,6],13:[3],15:[6],16:[5,6],17:[6],20:[6],21:[6],22:[6],23:[5,6],26:[6]}
from tools.emulator import Session,Debugger,ffi
from tools.dialogue_checks import TextChecks
from tools.bakery_playtest import service_ready

def run(source,only=None):
 out=source/'tutorial-bank-validation';rom=(source/'torneko-2-english.gba').read_bytes();b=json.loads((source/'build.json').read_text());require(digest(rom)==b['output_sha256'],'Stale tutorial-help ROM');mgba.log.silence();fixture=service_ready(rom,out);rows={r['offset']+0x08000000:r for r in b['tutorial_help']['entries']};by_src={r['source']['offset']:r for r in rows.values()};groups={g['index']:g for g in b['tutorial_help']['groups']};results=[];original=load_base();event_rows={r['id']:r for r in b['dialogue']['entries']};rows.update({r['rom_offset']+0x08000000:r|{'kind':'bank-prose'} for r in event_rows.values()});by_id={r['id']:r for r in rows.values()}
 for index,bank_index in [(i,bn) for i,nums in COHORTS.items() for bn in nums]:
  group=groups[index];bank=banks()[bank_index];bank_entries={(r['group'],r['index']):r for r in table_entries(bank)};count=group['descriptor'][7];skip=2 if group['menu'] in(8,19,21,22) else 1;selectors=[]
  for pos in range(count-1):
   pointer=int.from_bytes(bytes.fromhex(group['intro_table_hex'])[4*(pos+skip):4*(pos+skip+1)],'little')-0x08000000;pair=tuple(original[pointer:pointer+2]);entry=bank_entries[pair];require(entry['id'] in event_rows,'Tutorial bank source lacks English');selectors.append({'pair':pair,'id':entry['id'],'source_offset':pointer})
  packed=struct.unpack_from('<I',rom,bank['pointer_offset'])[0]-0x08000000;decoded,_=decompress(rom,packed);expected_bank=bytearray(decoded)
  for word in range(4):struct.pack_into('<I',expected_bank,word*4,(struct.unpack_from('<I',decoded,word*4)[0]+BANK_RAM)&0xFFFFFFFF)
  if only is not None and index!=only:continue
  case=f'{index}-bank-{bank_index}';print('Tutorial help:',case,flush=True)
  with Session(rom,out/case) as g:
   g.restore(fixture);m=g.core.memory;c=TextChecks(g,rows);initial=[];returns=[];overrides=[];draws=[];images={};pixels=0;cycle=0;modals=[];modal_returns=[];pending=[];seen_pages=[];current_group=group;loads=[];selections=[];restores=[]
   original_banks=[]
   for possible in banks():
    packed0=struct.unpack_from('<I',rom,possible['pointer_offset'])[0]-0x08000000;d,_=decompress(rom,packed0);expected0=bytearray(d)
    for word in range(4):struct.pack_into('<I',expected0,word*4,(struct.unpack_from('<I',d,word*4)[0]+BANK_RAM)&0xFFFFFFFF)
    if bytes(m[BANK_RAM:BANK_RAM+len(expected0)])==expected0:original_banks.append((possible['index'],bytes(expected0)))
   require(len(original_banks)==1,'Fixture bank identity ambiguous');original_bank,original_bytes=original_banks[0]
   def reg(e,i,v):overrides.append({'event':e,'register':i,'after':v});g.core.cpu.gprs[i]=v
   def jump(e,at,why):
    overrides.append({'event':e,'pc_after':at+0x08000000,'reason':why});require(g.core._core.writeRegister(g.core._core,b'pc',ffi.new('uint32_t*',at+0x08000000)),'Tutorial redirect failed')
   inventory=bytes(m[0x0200DF28:0x0200E888]);hero=m.u32[0x02001624];gold=m.u32[hero+0x60]
   def callback(e):
    a,r=e['address'],e['registers']
    if a==0x0801DFAC and len(initial)==len(returns):
     initial.append(e|{'guard':bytes(m[r[13]:r[13]+32]).hex()});draws.clear();reg(e,0,bank_index);reg(e,14,0x0804F8F5);jump(e,0x4D6F8,'Controlled entry into full original event-bank loader, then full script-reader frame.');return
    if len(initial)==len(returns):return
    if a==0x0804F8F4:
     old=initial[-1]['registers'];require(r[4:12]==old[4:12] and r[13]==old[13] and bytes(m[r[13]:r[13]+32]).hex()==initial[-1]['guard'],'Tutorial bank loader ABI/guard differs');require(m.u32[0x0200FF38]==BANK_RAM and bytes(m[BANK_RAM:BANK_RAM+len(expected_bank)])==expected_bank,'Tutorial native bank load/fixups differ');loads.append({'event':e,'bank':bank_index,'bytes':len(expected_bank),'sha256':digest(bytes(expected_bank))});reg(e,14,old[14])
    if a==0x0804FA68:
     selector=selectors[m.u8[0x020101A1]];require(tuple(r[:2])==selector['pair'],'Tutorial bank selection differs');selections.append(e|selector)
    if a==0x0804F8F8:
     reg(e,4,index);jump(e,0x4F9AA,'Select owned menu configuration; original descriptor/outer-table loads execute, event-bank prelude excluded.')
    if a==0x08015A34:
     require(r[0] in rows and rows[r[0]]['kind']=='bank-prose','Tutorial selected an unowned prose source');modals.append(e|{'id':rows[r[0]]['id']});pending.append(e)
    if a in (0x08001750,0x08001888):draws[:]=[d for d in draws if d['window']!=r[0]]
    if a==0x080021B4 and r[1] in rows:
     row=rows[r[1]];w=r[0]
     if row['kind']=='heading':require(bytes(m[w:w+2])==bytes((8,24)) and bytes(m[w+4:w+6])==bytes((28,1)),'Tutorial header geometry differs')
     if row['kind']=='label':require(bytes(m[w:w+2])==bytes((8,56)) and m.u8[w+4]*8==(224 if current_group['menu'] in(10,13,14) else min(current_group['descriptor'][6]*16,224)) and m.u8[w+5]==current_group['rows'],'Tutorial topic geometry differs')
    if a==0x08001BC4 and c.active:
     w=r[0];key=(w,r[1],r[13],r[14],m.u8[w+2],m.u8[w+3])
     if not draws or draws[-1]['key']!=key:draws.append({'key':key,'window':w,'code':r[1],'x':m.u8[w+2],'y':m.u8[w+3],'origin':[m.u8[w],m.u8[w+1]],'foreground':m.u8[0x020000C2],'bank':m.u16[m.u32[w+12]]>>12,'id':c.active['id']})
    if a in c.ADDRESSES:c.callback(e)
    if pending and a==(pending[-1]['registers'][14]&~1):
     old=pending.pop()['registers'];require(r[4:12]==old[4:12] and r[13]==old[13],'Tutorial modal ABI differs');modal_returns.append(e)
    if a==0x0804FA44:
     restores.append(e);reg(e,0,original_bank);reg(e,14,0x0804FA53);jump(e,0x4D6F8,'Restore fixture bank through original loader before returning; VM advancement excluded.')
    if a==0x0804FA52:
     old=restores[-1]['registers'];require(r[4:12]==old[4:12] and r[13]==old[13] and bytes(m[BANK_RAM:BANK_RAM+len(original_bytes)])==original_bytes,'Fixture bank native restoration differs')
    if a==0x0804FA58:
     old=initial[-1]['registers'];require(r[4:12]==old[4:12] and r[13]==old[13] and r[0]==old[14] and bytes(m[r[13]:r[13]+32]).hex()==initial[-1]['guard'],'Tutorial caller ABI/guard differs');returns.append(e)
   def capture(tag):
    nonlocal pixels
    g.frames(8);pic=g.capture(tag);images[tag+'.png']=digest((g.output/(tag+'.png')).read_bytes());require(draws,'Tutorial missing visible text')
    for d in draws:
     glyph,_=c.glyph_record(d['code']);colour=m.u16[0x05000000+2*(16*d['bank']+d['foreground'])];rgb=tuple(((colour>>s)&31)*255//31 for s in (0,5,10))
     if by_id[d['id']]['kind']=='label':require(d['x']>=6,'Tutorial label in cursor reserve')
     for y,line in enumerate(glyph['rows']):
      for x,bit in enumerate(line):require((pic.getpixel((d['origin'][0]+d['x']+x,d['origin'][1]+16*d['y']+y))==rgb)==(bit=='#'),'Tutorial final pixels differ: '+repr((case,tag,d['id'],hex(d['code']),d['x'],d['y'])));pixels+=1
   def move(target):
    columns=group['menu'] in(10,13,14)
    if columns and m.u8[0x020101A1]>=(count+1)//2:g.press('LEFT',wait=20)
    for _ in range(count):
     if m.u8[0x020101A1]==0:break
     g.press('DOWN',wait=20)
    require(m.u8[0x020101A1]==0,'Tutorial cursor origin unreachable')
    if columns and target>=(count+1)//2:g.press('RIGHT',wait=20)
    for _ in range(count):
     if m.u8[0x020101A1]==target:return
     g.press('DOWN',wait=20)
    raise ValueError('Tutorial cursor failed to reach topic '+str(target))
   def check_menu(start):
    expected=[by_src[current_group['prose'][0]['source']['offset']]['id']]+[by_src[e['offset']]['id'] for e in current_group['labels']]
    require([r['id'] for r in c.reads[start:]]==expected,'Tutorial native header/labels differ: '+repr(([r['id'] for r in c.reads[start:]],expected,len(initial),len(loads),hex(int(g.core.cpu.gprs[15])),overrides[-4:],dict((hex(a),m.u16[a]) for a in [0x04000200,0x04000208,0x04000004]))))
   with Debugger(g,callback,max_events=600000) as debug:
    for a in set(c.ADDRESSES)|{0x08050DD0,0x0801DFAC,0x0804F8F4,0x0804FA68,0x0804FAA8,0x0804F8F8,0x0804FA44,0x0804FA52,0x0804FA58,0x08015A34,0x08050E6E,0x080510CE,0x08001750,0x08001888}:debug.breakpoint(a)
    for cycle in range(3):
     current_group=group;start=len(c.reads);g.press('A',hold=1,wait=120);check_menu(start);capture('opened-'+str(cycle));g.press('UP',wait=20);require(m.u8[0x020101A1]<count,'Tutorial upward wrap differs');capture('last-'+str(cycle));g.press('DOWN',wait=20);require(m.u8[0x020101A1]==0,'Tutorial downward wrap differs')
     if cycle<2:g.press('B',hold=1,wait=120)
     else:
      for page in ([18,19] if index==18 else [index]):
       if page!=index:
        current_group=groups[page];start=len(c.reads);g.press('RIGHT',wait=120);check_menu(start);capture('next-menu');seen_pages.append(page)
       else:seen_pages.append(page)
       for topic in range(count-1):
        move(topic);old=len(modal_returns);start=len(c.reads);g.press('A',hold=1,wait=0);handled=set();expected=selectors[topic]['id']
        for tick in range(6000):
         if len(modal_returns)>old:break
         state=(len(c.reads),c.active['page_waits'] if c.active else -1)
         if ((c.active and c.active['id']==expected and c.active['page_waits']) or (c.reads and not c.active and c.reads[-1]['id']==expected)) and state not in handled:
          capture(f'body-{page}-{topic}-{len(handled)}');handled.add(state);g.press('A',hold=1,wait=0)
         else:g.frames(1)
        require(len(modal_returns)==old+1 and modals[-1]['id']==expected,'Tutorial prose/return incomplete');require(len(handled)==len(event_rows[expected]['layout']['pages']),'Tutorial prose pages incomplete');g.frames(120);capture(f'reopened-{page}-{topic}')
      if index==18:
       current_group=groups[18];g.press('LEFT',wait=120);capture('previous-menu');current_group=groups[19];g.press('RIGHT',wait=120);capture('next-menu-again')
      move(count-1);g.press('A',hold=1,wait=120)
     require(len(returns)==cycle+1,'Tutorial menu did not exit')
   require(len(modals)==len(modal_returns) and not c.active and not pending,'Tutorial modal remained active');require(bytes(m[0x0200DF28:0x0200E888])==inventory and m.u32[hero+0x60]==gold and g.snapshot().battery==fixture.battery,'Tutorial browsing changed items/gold/save');results.append({'case':case,'group':index,'inputs':g.inputs,'overrides':overrides,'reads':c.reads,'modals':modals,'modal_returns':modal_returns,'returns':returns,'pages':seen_pages,'native_bank_loads':loads,'fixture_bank_restores':restores,'fixture_bank':original_bank,'selections':selections,'caller_guard_abi_preserved':True,'visible_pixels_checked':pixels,'images':images});(out/'partial.json').write_text(json.dumps(results,indent=2)+'\n')
 report={'passed':True,'rom_sha256':digest(rom),'cases':results,'scope':'Controlled original event-bank loader followed by full tutorial dispatcher/menu. All topics in16 consistent bank-backed configurations, including both relevant pot/trick banks, exact original two-byte selectors and English pointers, complete modal pages, original geometry, cursor selection, Cancel/B and repeated reopen, final pixels and loader/modal/caller ABI. Script prelude/progression and natural NPC access are excluded. Five inconsistent original configurations remain render/cursor-only pending reachability research. Inventory/gold/battery remain unchanged.'};(out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print('Tutorial banks:',len(results),'passed')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--source',type=Path,default=ROOT/'build/english');p.add_argument('--only',type=int);a=p.parse_args();run(a.source,a.only)
