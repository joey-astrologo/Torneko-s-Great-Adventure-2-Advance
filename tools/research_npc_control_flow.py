"""Conservative NPC branch traversal; unresolved roots stay explicit."""


def run():
    import json,struct
    from tools.rom import ROOT,load_base,digest
    (ROOT/'build/event-script-audit').mkdir(parents=True,exist_ok=True)
    from tools.lz77 import decompress
    from tools.opening_text import banks
    from tools.event_text import table_entries
    rom=load_base();src=json.loads((ROOT/'build/event-script-audit/npc-text-refs.json').read_text());lengths=list(rom[0x14CEBC:0x14CEE0]);out=[];allrefs=[]
    assert src['source_rom_sha256']==digest(rom), 'NPC reference audit uses another source ROM'
    for bank in src['banks']:
     d,_=decompress(rom,bank['rom_start']);lo,hi=bank['header'][3:5];rows={(r['group'],r['index']):r for r in table_entries(banks()[bank['bank']])};roots=[]
     for s in bank['scripts']:
      todo=[s['start']];seen=set();ins=[];errors=[]
      while todo:
       pc=todo.pop()
       if pc in seen:continue
       seen.add(pc)
       if not lo<=pc<hi:errors.append(dict(at=pc,reason='Outside declared instruction region'));continue
       op=d[pc]
       if op>=len(lengths):errors.append(dict(at=pc,reason='Unknown opcode',value=op));continue
       size=1+lengths[op]
       if pc+size>hi:errors.append(dict(at=pc,reason='Truncated operands',opcode=op));continue
       # Native4EF40 stops on21.20 resumes after asynchronous actor work.
       successors=[] if op==21 else [pc+size]
       if op==6:successors.append(pc+struct.unpack_from('<b',d,pc+4)[0])
       elif op==16:successors.append(pc+d[pc+1])
       row=dict(offset=pc,opcode=op,hex=d[pc:pc+size].hex(),successors=successors)
       if op==8:
        _,actor,group,index,mode,extra=d[pc:pc+size];e=rows.get((group,index));ref=dict(bank=bank['bank'],root=s['start'],offset=pc,actor=actor,group=group,index=index,mode=mode,extra=extra,id=e['id'] if e else None,display='custom-handler-ignores-text' if mode==2 else 'modal');row['text_reference']=ref;allrefs.append(ref)
       todo.extend(successors);ins.append(row)
      roots.append(dict(start=s['start'],consumers=s['consumers'],instructions=sorted(ins,key=lambda x:x['offset']),errors=errors))
     out.append(dict(bank=bank['bank'],roots=roots,outside=bank['outside']));print('bank',bank['bank'],'roots',len(roots),'errors',[(hex(s['start']),s['errors']) for s in roots if s['errors']])
    stubs=src['stub_references'];report=dict(source_rom_sha256=digest(rom),scope='Conservative static traversal from original NPC selector roots. Both outcomes for flag opcode6 and choice opcode16; original signed/unsigned relative offsets, END21 stops, WAIT20 advances. Other handlers treated as fallthrough using original lengths; native map activation, malformed bank2 roots and other direct getter consumers remain excluded. No unused-text disposition is established here.',banks=out,references=allrefs,stub_references={k:[r for r in allrefs if r['id']==k] for k in stubs});(ROOT/'build/event-script-audit/npc-control-flow.json').write_text(json.dumps(report,indent=2)+'\n')
    for k,v in report['stub_references'].items():
     if v:print(k,v)
    return report


if __name__ == "__main__":
    run()
