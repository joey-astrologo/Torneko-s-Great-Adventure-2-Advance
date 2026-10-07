"""Give each event fragment a disposition in the current shipped script graph.

Rebuild NPC roots from the compiled actor records, follow both branch outcomes,
and cross-check the event interpreters, direct getters and tutorial contexts.
No dialogue is reconstructed for records with no executable reference.
"""
import json
from pathlib import Path
import struct

from tools.audit_reader_routes import direct_calls
from tools.event_text import table_entries
from tools.lz77 import decompress
from tools.npc_script_model import operand_lengths
from tools.opening_text import banks
from tools.rom import ROOT,digest,load_base,require

OUT=ROOT/'build/oct07-source-dispositions'
BASE=0x08000000


def run():
    original=load_base(); compiled=(ROOT/'build/torneko-2-english.gba').read_bytes()
    ledger=json.loads((ROOT/'build/english/build.json').read_text())
    require(digest(compiled)==ledger['output_sha256'],'Fragment audit build differs')
    inputs={}
    def receipt(name):
        path=ROOT/name; data=json.loads(path.read_text());inputs[name]=digest(path.read_bytes())
        require(data.get('source_rom_sha256',data.get('source_sha256'))==digest(original),'Fragment input source differs')
        return data
    events=receipt('build/oct07-text/event-script-paths/report.json')
    direct=receipt('build/npc-handlers/report.json')
    tutorials=receipt('build/oct04-continuation/tutorial-reachability.json')
    require(all(r['rom_sha256']==digest(compiled) for r in (events,direct,tutorials)), 'Evidence belongs to another compiled ROM')
    inventory=json.loads((ROOT/'build/text-inventory/catalog.json').read_text())['entries']
    fragments={e['id']:e for e in inventory if e['family']=='event' and e['language_status']=='untranslated'}
    require(len(fragments)==34,'Fragment cohort changed')
    require(direct_calls(original[:0x5E000],BASE+0x50270)==direct['getter_calls'],'Getter call domain changed')
    require(struct.pack('<I',BASE+0x50271) not in original,'Indirect event getter owner needs investigation')
    lengths=operand_lengths(original); npc_banks=[]; references=[]; executed=set(); tutorial_contexts=set()
    for bank in range(7):
        data,_=decompress(compiled,struct.unpack_from('<I',compiled,0x14CD68+4*bank)[0]-BASE)
        h=struct.unpack_from('<5I',data); lo,hi=h[3:5]
        table={(e['group'],e['index']):e for e in table_entries(banks()[bank])}
        roots={}
        for node in range(32):
            relative=struct.unpack_from('<I',data,h[0]+4*node)[0]
            first,count=struct.unpack_from('<HH',data,h[1]+4*node)
            if relative==0xffffffff or first==0xffff:continue
            require(h[2]+4*(first+count)<=lo,'Actor selector table exceeds owned span')
            for actor in range(count):
                record=data[h[4]+8*(first+actor):h[4]+8*(first+actor)+8]
                require(len(record)==8,'Actor record missing')
                selector=record[4]
                if selector==255:continue
                index=first-1+selector
                require(0<=index and h[2]+4*(index+1)<=lo,'Actor selector out of table')
                start=lo+relative+struct.unpack_from('<I',data,h[2]+4*index)[0]
                require(lo<=start<hi,'Compiled actor still selects outside script region')
                roots.setdefault(start,[]).append(dict(map=node,actor=actor,selector=selector,record=first+actor))
        paths=[]
        for start,actors in sorted(roots.items()):
            pending=[start]; seen=set(); instructions=[]
            while pending:
                pc=pending.pop()
                if pc in seen:continue
                seen.add(pc);require(lo<=pc<hi,'NPC branch escapes instruction region')
                op=data[pc]; size=1+(lengths[op] if op<len(lengths) else 0)
                require(pc+size<=hi,'NPC operand span truncated')
                successors=[] if op==21 else [pc+size]
                if op==6:successors.append(pc+struct.unpack_from('<b',data,pc+4)[0])
                elif op==16:successors.append(pc+data[pc+1])
                ins=dict(at=pc,opcode=op,hex=data[pc:pc+size].hex(),successors=successors)
                if op==8 and data[pc+4]==2:
                    tutorial_contexts.add((bank,data[pc+5]))
                if op==8 and data[pc+4]!=2:
                    entry=table.get((data[pc+2],data[pc+3]));require(entry,'NPC dialogue outside text table')
                    require(entry['id'] not in fragments,'Unrepaired fragment is executable')
                    references.append(dict(bank=bank,root=start,at=pc,id=entry['id']))
                    ins['id']=entry['id']
                executed.add((bank,pc));instructions.append(ins);pending.extend(successors)
            paths.append(dict(start=start,actors=actors,instructions=sorted(instructions,key=lambda x:x['at'])))
        npc_banks.append(dict(bank=bank,decoded_sha256=digest(data),instruction_range=[lo,hi],roots=paths))
    for root in events['roots']:
        if root['mode']!=2:continue
        for ins in root['instructions']:
            raw=bytes.fromhex(ins['hex'])
            if ins['opcode']==8 and raw[4]==2:tutorial_contexts.add((root['bank'],raw[5]))
    tutorial_contexts|={(bank,19) for bank,index in tutorial_contexts if index==18}
    tutorial_refs=[]
    for bank,index in sorted(tutorial_contexts):
        group=ledger['tutorial_help']['groups'][index]
        repair=next((r for r in ledger['tutorial_help']['repairs'] if r['configuration']==index),None)
        if group['mode']!=1 or repair:continue # Owned direct-prose component.
        table={(e['group'],e['index']):e for e in table_entries(banks()[bank])}
        skip=2 if group['menu'] in (8,19,21,22) else 1
        pointers=bytes.fromhex(group['intro_table_hex'])
        for pos in range(group['descriptor'][7]-1):
            pointer=struct.unpack_from('<I',pointers,4*(pos+skip))[0]-BASE
            pair=tuple(original[pointer:pointer+2]);entry=table.get(pair)
            require(entry and entry['id'] not in fragments,'Tutorial topic reaches a fragment')
            tutorial_refs.append(dict(bank=bank,configuration=index,topic=pos,pair=pair,id=entry['id']))
    known={r['id'] for r in references+events['references']+direct['direct_references']+tutorial_refs}
    require(not known.intersection(fragments),'Fragment entered known getter graph')
    candidates=events['fragment_candidates']
    require(len(candidates)==4,'Fragment byte candidates changed')
    require(all((c['bank'],c['at']) not in executed for c in candidates if c['kind']=='npc'),
            'Previously dead fragment bytes gained an NPC entry')
    rows=[]
    for ident,entry in sorted(fragments.items()):
        matches=[c for c in candidates if c['id']==ident]
        if ident in ('event-bank-2.382a','event-bank-2.382d','event-bank-2.3830'):
            disposition='after-unconditional-end'
            require(len(matches)==1 and matches[0]['kind']=='npc','Post-END evidence missing')
            require(any(ins['at']==0x5ae and ins['opcode']==21 for b in npc_banks if b['bank']==2
                        for root in b['roots'] if root['start']==0x5ab for ins in root['instructions']), 'Native END path differs')
            explanation='Only encoded selector is after END at decoded NPC bank 2:5AE. No compiled actor root or conservative branch enters it.'
        elif ident=='event-bank-3.03b6':
            disposition='operand-byte-coincidence'
            require(len(matches)==1 and matches[0]['at']==0x43eb65,'Operand candidate differs')
            explanation='The sole byte candidate begins inside operands of event instruction 43EB62. Neither event interpreter graph enters 43EB65.'
        else:
            disposition='no-selector-in-shipped-script-graph'
            require(not matches,'New fragment byte candidate')
            explanation='No encoded dialogue selector in any of the seven NPC instruction spans or seven event spans; no reference in direct getter or tutorial contexts.'
        rows.append(dict(id=ident,source_sha256=entry['source_sha256'],raw_hex=entry['raw_hex'],
            japanese=entry['japanese'],disposition=disposition,evidence=explanation,candidates=matches))
    report=dict(passed=True,source_rom_sha256=digest(original),rom_sha256=digest(compiled),
        tool_sha256=digest(Path(__file__).read_bytes()),inputs=inputs,npc_banks=npc_banks,
        npc_references=references,tutorial_contexts=sorted(tutorial_contexts),tutorial_references=tutorial_refs,sources=rows,
        counts=dict(fragments=34,npc_roots=sum(len(b['roots']) for b in npc_banks),
                    npc_reference_contexts=len(references),after_end=3,operand_coincidence=1,no_selector=30),
        scope=__doc__,limits='The graph is bounded by shipped event roots, compiled actor map records and recovered direct/tutorial getter contexts. Arbitrary RAM mutation, corrupt saves and unknown synthesized entry mechanisms are excluded. Original fragment bytes are retained; no whole-game or ordinary-access claim.')
    OUT.mkdir(parents=True,exist_ok=True);(OUT/'event-fragment-dispositions.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Event fragments:',report['counts'])
    return report

if __name__=='__main__':run()
