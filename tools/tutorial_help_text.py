"""Prototype all tutorial labels while preserving nontext menu references."""
import json,struct
from tools.rom import ROOT,digest,require
from tools.extract_items import source
from tools.text_codec import tokenize
from tools.compact_font import encode,measure
from tools.dialogue_layout import compile_dialogue
CATALOG=ROOT/'translations/tutorial-help-review.json'
def add_tutorial_help(build, dialogue=None):
 c=json.loads(CATALOG.read_text());require(c['base_rom_sha256']==digest(build.original) and [g['index'] for g in c['groups']]==list(range(27)),'Tutorial-all source cohort differs');rows=[];outer=[bytearray(build.original[0x14CF50:0x14CFBC]),bytearray(build.original[0x14CFBC:0x14D028])]
 require(len(c['entries'])==104 and len({e['source']['offset'] for e in c['entries']})==104,'Tutorial-all unique sources differ')
 for row in c['entries']:
  src=row['source'];text=row['english'];require(row['status']=='reviewed' and src==source(build.original,src['offset']+0x08000000),'Tutorial-all source review differs')
  if row['kind']=='prose':raw,layout=compile_dialogue(text,tokenize(bytes.fromhex(src['raw_hex']))[0])
  elif 'cells' in row:
   require(text==' | '.join(row['cells']) and len(row['cells'])==2 and all(not any(c in t for c in '{}%@\n') for t in row['cells']),'Tutorial cells/control mismatch');commands=[t['raw_hex'] for t in tokenize(bytes.fromhex(src['raw_hex']))[0] if t['kind']=='command'];require(len(commands)==1 and commands[0].startswith('04'),'Tutorial column source differs');x=int(commands[0][2:],16)*240//256;require(x==row['source_column_x'],'Tutorial original cursor column differs');menus={g['menu'] for g in c['groups'] if any(e['offset']==src['offset'] for e in g['labels'])};require(len(menus)==1,'Tutorial cell geometry ambiguous');menu=next(iter(menus));cursor_table,count={10:(0x14E3BC,8),13:(0x14E4D0,9),14:(0x14E54C,8)}[menu];cursor_x=sorted({struct.unpack_from('<I',build.original,cursor_table+8*i)[0] for i in range(count)});require(len(cursor_x)==2,'Tutorial cursor columns differ');starts=[cursor_x[0]+6,max(x+6,cursor_x[1]+6)];widths=[measure(t) for t in row['cells']];budgets=[cursor_x[1]-starts[0],224-starts[1]];require(all(w<=b for w,b in zip(widths,budgets)),'Tutorial cell exceeds original cursor region');raw=bytes((6,starts[0]))+encode(row['cells'][0])[:-1]+bytes((6,starts[1]))+encode(row['cells'][1]);layout={'pages':[[text]],'cell_widths':widths,'cell_budgets':budgets,'cell_starts':starts,'cursor_x':cursor_x,'original_cursor_table':cursor_table}
  else:
   require(not any(ch in text for ch in '{}%@\n'),'Unexpected tutorial label control');matching=[g for g in c['groups'] if any(e['offset']==src['offset'] for e in g['labels'])];start=11 if matching and all(g['menu']==13 for g in matching) else 6;budget=216 if row['kind']=='heading' else min((120 if g['menu']==13 else min(g['descriptor'][6]*16,224))-start for g in matching);require(measure(text)<=budget,'Tutorial label exceeds original region: '+text);raw=(b'' if row['kind']=='heading' else bytes((6,start)))+encode(text);layout={'pages':[[text]],'line_widths':[[measure(text)]],'maximum_width':budget,'start':0 if row['kind']=='heading' else start}
  at=build.allocate(row['id'],raw,'tutorial-help');rows.append(row|{'offset':at,'encoded_hex':raw.hex(),'layout':layout})
 by_src={e['source']['offset']:e for e in rows};bindings=[];repairs={}
 if dialogue is not None:
  # The original early-story banks do not contain these tutorial groups.
  # Reuse reviewed explanations through the existing direct-prose consumer.
  from tools.opening_text import banks
  from tools.event_text import table_entries
  event_rows={r['id']:r for r in dialogue['entries']}
  source_rows={(bn,e['group'],e['index']):e for bn in (5,6) for e in table_entries(banks()[bn])}
  for index,bank,pairs,menu in ((12,5,[(2,i) for i in (2,5,6,7,8,9,10)],14),
                                 (14,6,[(9,1)],5)):
   selected=[event_rows[source_rows[(bank,*pair)]['id']] for pair in pairs]
   for e in selected:
    raw=bytes.fromhex(e['encoded_hex']);require(e['language_status']=='reviewed' and build.data[e['rom_offset']:e['rom_offset']+len(raw)]==raw,'Tutorial repair prose is not inserted')
   repairs[index]=dict(configuration=index,source_bank=bank,source_pairs=pairs,
                      prose_ids=[e['id'] for e in selected],pointers=[e['rom_offset']+0x08000000 for e in selected],
                      menu=menu,mode=0,reason='Original bank-dependent selectors resolve unrelated text; reuse matching reviewed tutorials without changing event banks or prose')
 for g in c['groups']:
  i=g['index'];require(build.original[0x14CEFC+3*i:0x14CEFF+3*i].hex()==g['descriptor_triple_hex'] and tuple(g['descriptor'])==struct.unpack_from('<8h',build.original,0x14D52C+16*g['menu']),'Tutorial original descriptor differs')
  for num,key in enumerate(('labels','intro')):
   start=g[key+'_offset'];data=bytearray.fromhex(g[key+'_table_hex']);require(build.original[start:start+len(data)]==data and struct.unpack_from('<I',outer[num],4*i)[0]==start+0x08000000,'Tutorial original nested table differs');changed=[]
   for k in range(len(data)//4):
    ptr=struct.unpack_from('<I',data,4*k)[0];offset=ptr-0x08000000
    # Intro index0 is the header, optional index1 may hold an alternate
    # header. Type0/2 subsequent entries are direct prose; type1 entries
    # instead contain two-byte bank/group selectors, even if bytes decode.
    owned=(num==0 or k==0 or (k==1 and g['menu'] in(8,19,21,22) and offset in by_src and by_src[offset]['kind']=='heading') or (g['mode'] in(0,2) and offset in by_src and by_src[offset]['kind']=='prose'))
    if owned:
     require(offset in by_src,'Tutorial text lacks review');struct.pack_into('<I',data,4*k,by_src[offset]['offset']+0x08000000);changed.append(k)
   if i in repairs and key=='intro':
    for k,pointer in enumerate(repairs[i]['pointers'],1):struct.pack_into('<I',data,4*k,pointer);changed.append(k)
   at=build.allocate(f'tutorial-help-{key}-{i}',bytes(data),'tutorial-help');struct.pack_into('<I',outer[num],4*i,at+0x08000000);bindings.append({'group':i,'kind':key,'source_offset':start,'offset':at,'bytes':len(data),'changed_slots':changed})
  if i in repairs:
   repair=repairs[i];old=bytes.fromhex(g['descriptor_triple_hex']);new=bytes((repair['menu'],old[1],0))
   build.patch('tutorial-help-dispatch-'+str(i),0x14CEFC+3*i,old,new,'tutorial-help')
   g['original_configuration']={k:g[k] for k in ('menu','mode','descriptor','rows','labels','descriptor_triple_hex')}
   g.update(menu=repair['menu'],mode=0,descriptor=list(struct.unpack_from('<8h',build.original,0x14D52C+16*repair['menu'])),descriptor_triple_hex=new.hex())
   g['rows']=(g['descriptor'][7]+1)//2 if g['menu'] in (10,13,14) else g['descriptor'][7]
   if i==14:g['labels']=g['labels'][:2]
 for label,data,base,sites in [('labels',outer[0],0x14CF50,(0x4F9F0,0x4FA1C,0x5103C,0x51088)),('intro',outer[1],0x14CFBC,(0x4F9F4,0x4FA20,0x51040,0x5108C))]:
  at=build.allocate('tutorial-help-private-'+label,bytes(data),'tutorial-help')
  for site in sites:build.patch('tutorial-help-reader-'+hex(site),site,struct.pack('<I',base+0x08000000),struct.pack('<I',at+0x08000000),'tutorial-help')
 return {'entries':rows,'groups':c['groups'],'bindings':bindings,'repairs':list(repairs.values()),'catalog_sha256':digest(CATALOG.read_bytes()),'scope':c['scope']}
