"""Original NPC selector roots and physical instruction references."""


def run():
    import json,struct
    from tools.rom import ROOT,load_base,digest,require
    (ROOT/'build/event-script-audit').mkdir(parents=True,exist_ok=True)
    from tools.lz77 import decompress
    from tools.event_text import table_entries
    from tools.opening_text import banks
    r=load_base();u32=lambda a:struct.unpack_from('<I',r,a)[0];lengths=list(r[0x14CEBC:0x14CEE0]);out=[];refs=[]
    for bank,b in enumerate(banks()):
     lo=u32(0x14CD68+4*bank)-0x8000000;data,hi=decompress(r,lo);h=struct.unpack_from('<5I',data);rows={(e['group'],e['index']):e for e in table_entries(b)};maps=[];roots={};outside=[]
     for node in range(32):
      relative=struct.unpack_from('<I',data,h[0]+4*node)[0];first,count=struct.unpack_from('<HH',data,h[1]+4*node)
      if relative==0xFFFFFFFF or first==0xFFFF:continue
      require(h[2]+4*(first+count)<=h[3],'Actor offsets exceed table');actors=[]
      for actor in range(count):
       record=data[h[4]+8*(first+actor):h[4]+8*(first+actor)+8];require(len(record)==8,'Missing actor record');selector=record[4]
       if selector==255:continue
       index=first-1+selector;require(h[2]+4*(index+1)<=h[3],'Selected actor offset outside table');start=h[3]+relative+struct.unpack_from('<I',data,h[2]+4*index)[0]
       ref=dict(node=node,actor=actor,record_index=first+actor,selector=selector,offset_index=index)
       if not h[3]<=start<h[4]:outside.append(ref|dict(target=start,record_hex=record.hex()));continue
       roots.setdefault(start,[]).append(ref);actors.append(start)
      maps.append(dict(node=node,relative=relative,first=first,count=count,roots=actors))
     bounds=sorted(roots)+[h[4]];scripts=[]
     for n,start in enumerate(bounds[:-1]):
      end=bounds[n+1];pc=start;instructions=[];errors=[]
      while pc<end:
       op=data[pc]
       if op>=len(lengths):errors.append(dict(at=hex(pc),error='Unknown opcode',byte=op));break
       size=1+lengths[op]
       if pc+size>end:errors.append(dict(at=hex(pc),error='Instruction exceeds next root',opcode=op,size=size,remaining=end-pc));break
       ins=dict(offset=pc,opcode=op,hex=data[pc:pc+size].hex())
       if op==8:
        _,actor,group,index,mode,extra=data[pc:pc+size];e=rows.get((group,index));ref=dict(bank=bank,offset=pc,root=start,consumers=roots[start],actor=actor,group=group,index=index,mode=mode,extra=extra,id=e['id'] if e else None,display='custom-handler-ignores-text' if mode==2 else 'modal');refs.append(ref);ins['text_reference']=ref
       instructions.append(ins);pc+=size
      scripts.append(dict(start=start,end_exclusive=end,consumers=roots[start],instructions=instructions,errors=errors))
     out.append(dict(bank=bank,rom_start=lo,rom_end_exclusive=hi,decoded_sha256=digest(data),header=h,outside=outside,maps=maps,scripts=scripts));print('NPC bank',bank,'roots',len(roots),'outside',outside,'errors',[(s['start'],s['errors']) for s in scripts if s['errors']],'refs',sum('text_reference' in i for s in scripts for i in s['instructions']))
    stubs={e['id'] for e in json.load(open(ROOT/'build/text-inventory/catalog.json'))['entries'] if e['family']=='event' and e['language_status']=='untranslated'}
    for ident in sorted(stubs):print(ident,[{k:v for k,v in ref.items() if k not in ('consumers',)} for ref in refs if ref['id']==ident])
    report=dict(source_rom_sha256=digest(r),scope='Static actor-script roots selected by original map offset, actor first/count and relative instruction tables. Native4B33C address arithmetic; operand lengths from14CEBC. Linear physical instruction decode does not establish natural reachability. Branch targets, scripts outside the named bank and direct getter consumers remain separate.',banks=out,references=refs,stub_references={i:[x for x in refs if x['id']==i] for i in sorted(stubs)});(ROOT/'build/event-script-audit/npc-text-refs.json').write_text(json.dumps(report,indent=2)+'\n')
    return report


if __name__ == "__main__":
    run()
