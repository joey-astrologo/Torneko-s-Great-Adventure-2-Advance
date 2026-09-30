"""Bounded original event-script references and opening-trace comparison."""


def run():
    import json,struct
    from tools.rom import ROOT,load_base,digest,require
    (ROOT/'build/event-script-audit').mkdir(parents=True,exist_ok=True)
    from tools.event_text import table_entries
    from tools.opening_text import banks
    r=load_base();u32=lambda a:struct.unpack_from('<I',r,a)[0];starts=[u32(0x14CD4C+4*i)-0x8000000 for i in range(7)]+[0x43FAAC];lengths=list(r[0x14CEBC:0x14CEE0]);out=[];allrefs=[]
    for bank,b in enumerate(banks()):
     lo,hi=starts[bank:bank+2];count=u32(lo);base=lo+4+4*count;offsets=[u32(lo+4+4*i) for i in range(count)];require(offsets==sorted(offsets) and offsets[0]==0,'Script block offsets differ');roots=[base+v for v in offsets]+[hi];rows={(e['group'],e['index']):e for e in table_entries(b)};scripts=[]
     for n in range(count):
      start,end=roots[n:n+2];pc=start+4;instructions=[];errors=[]
      while pc<end:
       op=r[pc]
       if op>=len(lengths):errors.append(dict(at=hex(pc),error='Opcode outside known size table',byte=op));break
       size=1+lengths[op]
       if pc+size>end:errors.append(dict(at=hex(pc),error='Instruction exceeds root boundary',opcode=op,size=size,remaining=end-pc));break
       instruction=dict(address=pc,hex=r[pc:pc+size].hex(),opcode=op)
       if op==8:
        require(size==6,'Dialogue opcode size differs');_,actor,group,index,mode,extra=r[pc:pc+size];entry=rows.get((group,index));ref=dict(bank=bank,script=n,address=pc,actor=actor,group=group,index=index,mode=mode,extra=extra,id=entry['id'] if entry else None,display='custom-handler-ignores-text' if mode==2 else 'modal');allrefs.append(ref);instruction['text_reference']=ref
       instructions.append(instruction);pc+=size
      scripts.append(dict(index=n,start=start,end_exclusive=end,header_hex=r[start:start+4].hex(),instructions=instructions,errors=errors))
     out.append(dict(bank=bank,rom_start=lo,rom_end_exclusive=hi,script_count=count,scripts=scripts));print('Script bank',bank,count,'errors',[(s['index'],s['errors']) for s in scripts if s['errors']],'dialogues',sum('text_reference' in i for s in scripts for i in s['instructions']))
    stubs={e['id'] for e in json.load(open(ROOT/'build/text-inventory/catalog.json'))['entries'] if e['family']=='event' and e['language_status']=='untranslated'}
    for ident in sorted(stubs):print(ident,[ref for ref in allrefs if ref['id']==ident])
    opening_matches=[]
    by_address={ref['address']+0x08000001:ref for ref in allrefs}
    for branch in ('yes','no'):
     path=ROOT/'build/opening-dialogue/research'/branch/'trace.json';trace=json.loads(path.read_text())
     require(trace['passed'] and trace['source_rom_sha256']==digest(r),'Opening trace is not pinned to original ROM')
     for slot in trace['slots']:
      ref=by_address[slot['script']]
      require(ref['bank']==0 and all(ref[k]==slot[k] for k in ('group','index','id')),'Original opening execution differs from static opcode decode')
     opening_matches.append(dict(branch=branch,calls=len(trace['slots']),trace=str(path.relative_to(ROOT)),trace_sha256=digest(path.read_bytes())))
    report=dict(opening_native_trace_matches=opening_matches,source_rom_sha256=digest(r),scope='Static linear decode of seven original script banks using original operand-size table and per-root offsets. Includes all physical instructions regardless of branches; no natural reachability claim. Separate actor dialogue tables and direct getter callers remain outside this pass.',banks=out,references=allrefs,stub_references={i:[x for x in allrefs if x['id']==i] for i in sorted(stubs)});(ROOT/'build/event-script-audit/script-text-refs.json').write_text(json.dumps(report,indent=2)+'\n')
    return report


if __name__ == "__main__":
    run()
