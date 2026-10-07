"""Resolve the 52 shared-source candidates against disassembled reader domains.

This combines complete exported SSA operations, the earlier paired Thumb trace,
and explicit selector-producer domains. It classifies the recovered graph;
it does not claim a proof for arbitrary code pointers or corrupt saved state.
"""
import json
from pathlib import Path
import struct
import subprocess

from tools.audit_town_source_dispositions import parse
from tools.rom import ROOT, digest, load_base, require

OUT=ROOT/'build/oct07-source-dispositions'
BASE=0x08000000
START=0x140D68
END=0x1417A0


def inspect(functions, r):
    rows=[]
    for f in functions:
     nodes=f['nodes'];defs={o['output']:o for o in f['ops'] if o['output']!='-'}
     cache={};active=set()
     def calc(n,path=()):
      if n in cache:return cache[n]
      if n in active:return None
      active.add(n)
      result=calculate(n)
      active.remove(n);cache[n]=result
      return result
     def calculate(n,path=()):
      if n in path:return None
      no=nodes[n]
      if no['constant'] is not None:return {no['constant']}
      if no['address'] and no['address'].startswith('08') and no['size']<=4:
       a=int(no['address'],16)-0x8000000;return {int.from_bytes(r[a:a+no['size']],'little')}
      if n.startswith('input:08'):
       a=int(n.split(':')[1],16)
       return {a if no['size']==8 else int.from_bytes(r[a-0x8000000:a-0x8000000+no['size']],'little')}
      o=defs.get(n)
      if not o:return None
      v=[calc(i,path+(n,)) for i in o['inputs']];k=o['kind']
      if k in ('COPY','CAST','INT_ZEXT'):return v[0]
      if k=='INDIRECT' and no['address'] and no['address'].startswith('08'):return v[0]
      if k=='INT_SEXT' and v[0] is not None:
       bits=8*nodes[o['inputs'][0]]['size'];return {((x if x<1<<(bits-1) else x-(1<<bits))&0xffffffff) for x in v[0]}
      if k=='MULTIEQUAL':return set().union(*v) if all(x is not None for x in v) else None
      if any(x is None for x in v):return None
      if k=='LOAD':
       size=nodes[o['output']]['size'];return {int.from_bytes(r[a-0x8000000:a-0x8000000+size],'little') for a in v[1]} if all(0x8000000<=a<0x8800000-size for a in v[1]) else None
      if k=='PTRADD':return {(a+b*c)&0xffffffff for a in v[0] for b in v[1] for c in v[2]}
      funcs={'INT_ADD':lambda a,b:a+b,'PTRSUB':lambda a,b:a+b,'INT_SUB':lambda a,b:a-b,'INT_MULT':lambda a,b:a*b,'INT_LEFT':lambda a,b:a<<b,'INT_AND':lambda a,b:a&b,'INT_RIGHT':lambda a,b:a>>b}
      if k in funcs:return {funcs[k](a,b)&0xffffffff for a in v[0] for b in v[1]}
      return None
     def expr(n,depth=0,seen=()):
      v=calc(n)
      if v is not None:return '|'.join(hex(x) for x in sorted(v))
      o=defs.get(n)
      if not o or depth>6 or n in seen:return n
      return o['kind']+'@'+hex(o['pc'])+'('+','.join(expr(x,depth+1,seen+(n,)) for x in o['inputs'] if not (o['kind']=='LOAD' and x==o['inputs'][0]))+')'
     taint=set()
     for n,no in nodes.items():
      if n.startswith(('input:08','constant:')):
       val=calc(n)
       if val and any(0x8140d68<=x<0x81417a0 for x in val):taint.add(n)
      if n.startswith('input:08'):
       a=int(n.split(':')[1],16)
       if 0x8140d68<=a<0x81417a0:rows.append({'entry':f['entry'],'kind':'direct-memory','node':n,'addresses':[a]})
     while True:
      before=len(taint)
      for o in f['ops']:
       if o['kind'] not in ('LOAD','CALL','CALLIND') and o['output']!='-' and taint.intersection(o['inputs']):taint.add(o['output'])
      if before==len(taint):break
     for o in f['ops']:
      if o['kind']=='LOAD' and o['inputs'][1] in taint:rows.append({'entry':f['entry'],'pc':o['pc'],'kind':'computed','node':o['inputs'][1],'addresses':sorted(calc(o['inputs'][1]) or []),'expression':expr(o['inputs'][1]) if calc(o['inputs'][1]) is None else None})
      if o['kind'] in ('CALL','STORE','RETURN') and taint.intersection(o['inputs']):rows.append({'entry':f['entry'],'pc':o['pc'],'kind':'escape','op':o['kind'],'values':[sorted(calc(x) or []) for x in o['inputs']]})
    return rows


def domains(original):
    from tools.audit_status_expiry import TIMERS
    from tools.audit_result_reason_selectors import GRAPH
    result={}; evidence=[]
    def add(sites, indexes, reason, spans=()):
        for pc in sites:
            result[BASE+pc]=dict(indexes=sorted(set(indexes)),reason=reason,
                code=[dict(start=lo,end_exclusive=hi,hex=original[lo:hi].hex()) for lo,hi in spans])
    add([0x51EC],set(struct.unpack_from('<5H',original,0x13EDF0))-{0},
        'Five-entry wind stage lookup; stages 0/1 select zero and skip the read.',[(0x51CE,0x51F0),(0x13EDF0,0x13EDFA)])
    add([0x96DE],{i for timer,i in TIMERS},
        'Complete recovered timer-expiry append branches; 20 native timer probes previously passed.',[(0x8F4C,0x9712)])
    add([0xCECC],[0,0x67,0x89],
        'Five direct callers supply only 0,67h,89h; zero suppresses the queue. audit_dynamic_text_selectors checks every caller.',[(0xCD4C,0xCD50),(0xCEC4,0xCEFA)])
    add([0xF5A8],[0x112],
        'SSA phi joins shared slot112h with a separate item-description table at08143EE0 + 4*u8. The latter cannot overlap the shared table.',[(0xF31E,0xF328),(0xF548,0xF5AC)])
    records=struct.unpack_from('<8h',original,0x147DD4)
    add([0x148C4],[records[1],*records[5:8]],
        'The two row descriptors contain one/three selectors; both stores and complete loop are checked by audit_save_menu_rows.',[(0x14848,0x148CE),(0x147DD4,0x147DE4)])
    add([0x14A5A,0x19E20,0x1CB4A,0x1CC24,0x1CC82,0x1EF64,0x1F1BC,
         0x56FA6,0x57050,0x570C2],range(0x174,0x181),
        'Dungeon/location enum 0..12, added to174h. Covers all thirteen native location names; Remi is a subset. Arbitrary corrupted location fields are excluded.')
    for sites,start in (([0x155C2,0x18404],0x147EE8),([0x155E8,0x18426],0x147EF4)):
        add(sites,struct.unpack_from('<3I',original,start),
            'Original keyboard page domain0..2. Compiled editors replace this entire lookup with their owned five-page component.',[(start,start+12)])
    add([0x1A9AA],struct.unpack_from('<32h',original,0x6B736),
        'Four status-help rows: three native vocations plus explicit alternate mode3; eight halfwords per row.',[(0x1A95C,0x1A9BC),(0x6B736,0x6B776)])
    add([0x1AB2A],range(0x1E0,0x1E6),
        'Baker producer requires Cemetery before its completion flag; native exit threshold7 bounds floors1..6. audit_companion_domain checks producer and threshold.')
    def reason_values(entry):
        return set().union(*(set(v) if isinstance(v,list) else reason_values(v) for v in GRAPH[entry].values()))
    reasons={x for x in reason_values(0x6644) if x<32 and x!=21}
    add([0x1CBD8,0x5701E],{0x196+x for x in reasons},
        'Result-reason producer graph:12 functions/58 calls, no28..31; reason21 takes its separate monster-name path. History uses saved copies of these native reasons.')
    voc=struct.unpack_from('<3h',original,0x6B8CC)
    add([0x1CCFA,0x570EA],{0x32,0,0x1C8,0x1C9,0x1B7,0x1C3,*voc},
        'Completion branch constants plus the three s16 vocation messages copied from6B8CC; current/history readers use the same domain.',[(0x1CC3A,0x1CCFC),(0x6B8CC,0x6B8D2)])
    add([0x207CC],range(0x26C,0x26F),
        'Three-iteration service loop starts at slot26Ch and increments its text pointer only for a displayed entry.',[(0x2079A,0x207EC)])
    add([0x1714C],[0xF2,0x102],
        'Floor notice chooses exactly F2h or102h before the shared load; both branches are in the paired Thumb trace.',[(0x17132,0x17150)])
    add([0x2B8FA],[0x99,0x9A,0x9B],
        'Three direct equipped-curse callers; native queue adapter owns all three source pointers. audit_dynamic_text_selectors checks call constants and final mapping.')
    for name in ('build/oct07-text/actor-skill-selectors.json',
                 'build/oct04-continuation/definition-selector-domains.json'):
        path=ROOT/name; data=json.loads(path.read_text())
        require(data['passed'] and data['source_sha256']==digest(original),'Definition domain receipt differs')
        evidence.append(dict(path=name,sha256=digest(path.read_bytes()),rom_sha256=data['rom_sha256']))
        grouped={}
        for case in data['cases']:
            for read in case['reads']:
                grouped.setdefault(read['pc'],set()).add(read.get('index',read.get('original_slot')))
        for pc,indexes in grouped.items():
            if pc in (0x8021220,0x8021786,0x80225AE,0x8022860,0x8024358,0x802A9DE,0x802ABD0):
                add([pc-BASE],indexes,'Complete original actor/skill/spell record and producer domain: '+name)
    return result,evidence


def run():
    original=load_base();compiled=(ROOT/'build/torneko-2-english.gba').read_bytes()
    ledger=json.loads((ROOT/'build/english/build.json').read_text())
    require(digest(compiled)==ledger['output_sha256'],'Shared disposition ROM differs')
    old_path=ROOT/'build/caller-branches/source-readers-final.json'
    prior=json.loads(old_path.read_text())
    require(prior['source_sha256']==digest(original),'Previous reader source differs')
    entries=sorted({r['entry_seed'] for r in prior['literal_candidates'] if r.get('entry_seed') is not None})
    exports={};functions=[]
    for filename,addresses in (('shared-flow.tsv',entries),('shared-extra-flow.tsv',
            [0x08017068,0x08017132,0x0802B6A8,0x08041312,0x080416EE,0x0804199A])):
        path=OUT/filename
        subprocess.run(['bash','tools/ghidra.sh','dataflow',str(path),*map(hex,addresses)],cwd=ROOT,check=True)
        parsed=parse(path); require(len(parsed)==len(addresses),'Incomplete shared SSA export')
        functions.extend(parsed);exports[filename]=digest(path.read_bytes())
    rows=inspect(functions,original);manual,domain_evidence=domains(original)
    unresolved=[];selectors=set()
    for row in rows:
        require(row['kind']!='escape','Shared table base escaped to uninspected callee/storage')
        if not row['addresses']:
            pc=row['pc']
            if pc not in manual:unresolved.append(row);continue
            row['domain']=manual[pc]
            row['addresses']=[BASE+START+4*i for i in manual[pc]['indexes']]
        row['shared_indexes']=sorted({(a-BASE-START)//4 for a in row['addresses'] if BASE+START<=a<BASE+END})
        selectors.update(row['shared_indexes'])
    (OUT/'shared-read-domains.json').write_text(json.dumps(dict(reads=rows,unresolved=unresolved),indent=2)+'\n')
    require(not unresolved,'Unresolved shared SSA domains: '+str([hex(x['pc']) for x in unresolved]))
    # Retain the older tracer as an independent coverage cross-check. A decompiler
    # export cannot silently drop one of its known load instructions.
    sites={r['pc'] for r in rows if 'pc' in r}
    old_sites={r['load'] for r in prior['table_reads'] if r['family']=='shared'}
    missing=old_sites-sites
    require(not missing,'Prior read sites missing from SSA: '+str([hex(x) for x in sorted(missing)]))
    by_site={pc:set().union(*(set(r['shared_indexes']) for r in rows if r.get('pc')==pc)) for pc in sites}
    rejected_prior=[]
    for read in prior['table_reads']:
        if read['family']=='shared':
            index=(read['addresses'][0]-BASE-START)//4
            if index not in by_site[read['load']]:
                require(read['load']==0x080225AE and index in (0x271,0x27F,0x28A,0x28D),
                        'SSA domain dropped a previously resolved selector at '+hex(read['load']))
                rejected_prior.append(dict(observation=read,index=index,
                    reason='The unbounded menu-loop trace loses the valid spell-record domain. Every one of the61 original records has target_kind0..8; selector22Fh+target_kind cannot produce this value. Corrected per-record first-read checks independently verify all61 cases.'))
    candidates=json.loads((ROOT/'build/oct07-text/unresolved-pointer-owners.json').read_text())['sources']
    inventory={r['id']:r for r in json.loads((ROOT/'build/text-inventory/catalog.json').read_text())['entries']}
    dispositions=[]
    for row in candidates:
        if not row['id'].startswith('rom.'):continue
        require(not selectors.intersection(row['shared_indexes']),'Recovered selector reaches unresolved source: '+row['id'])
        source=inventory[row['id']]
        dispositions.append(dict(id=row['id'],indexes=row['shared_indexes'],source_sha256=source['source_sha256'],
            japanese=source['japanese'],disposition='dormant-in-recovered-shared-reader-graph',
            evidence='Exact pointer owners are only the shared table. No selection in recovered SSA loads, including complete bounded computed domains and all earlier tracer load sites. Original bytes retained.'))
    require(len(dispositions)==52,'Shared candidate cohort changed')
    report=dict(passed=True,source_sha256=digest(original),rom_sha256=digest(compiled),
        tool_sha256=digest(Path(__file__).read_bytes()),exports=exports,
        prior_reader_report_sha256=digest(old_path.read_bytes()),domain_evidence=domain_evidence,
        rejected_prior_observations=rejected_prior,
        functions=len(functions),unique_read_sites=len(sites),prior_read_sites=len(old_sites),
        selected_indexes=sorted(selectors),sources=dispositions,scope=__doc__,
        limits='Recovered literal-seeded code graph and valid native data domains; unknown synthesized pointers/entries, arbitrary RAM mutation and corrupt imported saves are excluded. ROM storage is immutable in SSA analysis. No global unreachable proof or ordinary-scene coverage claim. No ROM changes.')
    (OUT/'shared-dispositions.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Shared source dispositions:',len(dispositions),'dormant records;',len(sites),'load sites;',len(functions),'exports')
    return report

if __name__=='__main__':run()
