"""Account for town sources against the complete recovered service read graph.

Ghidra SSA enumerates reads across branches without path-budget cutoffs. Explicit
native-code domains resolve the six computed selections and five stack-alias
loads. This is a shipped-service graph disposition, not arbitrary RAM safety.
"""
import json
from pathlib import Path
import struct
import subprocess

from tools.audit_reader_routes import direct_calls
from tools.rom import ROOT, digest, load_base, require
from tools.thumb_switches import switches
from tools.town_text import entries

OUT = ROOT/'build/oct07-source-dispositions'
GROUPS = {
    'town-flow.tsv': [0x1D110,0x1D544,0x1DFAC,0x1F2D8,0x1E394,0x20760],
    'town-children-flow.tsv': [0x1F3E0,0x1F80C,0x1F944,0x1FB50,0x1F6AC,
        0x1F83C,0x1E490,0x1FB90,0x1FD3C,0x1FB20,0x1FAAC,0x1E75C,0x20564,0x2068C],
}
SECOND_ARGUMENT = {0x1F3E0,0x1F80C,0x1F944,0x1FB50,0x1F6AC,0x1F83C,
                   0x1FB90,0x1FD3C,0x1FB20,0x1FAAC}
# Site, complete native index domain, supporting machine-code span, explanation.
DOMAINS = {
 0x1D4F8: (range(12,23), (0x1D4D8,0x1D4FC),
     'Signed quotient is narrowed to s16, clamped below zero to 0 and above 9 to 10; index=12+clamp.'),
 0x1D736: (range(39,51), (0x50054,0x50084),
     'Only caller initializes r4=0; random low bits optionally increment the u8 counter, resetting >11 to 1. Argument=0..12; zero bypasses the load; index=38+argument.'),
 0x1E842: (range(201,206), (0x1E78C,0x1E852),
     'Five five-byte ROM profiles at 6B8F6 contain only 0/201..205. Zero entries are skipped; filtering only removes entries.'),
 0x1ED6E: (range(164,167), (0x1ED5C,0x1ED70),
     'Native vocation byte 0=Merchant,1=Warrior,2=Mage; index=164+vocation. Corrupt/imported out-of-domain RAM is excluded.'),
 0x1ED8E: (range(154,157), (0x1ED7E,0x1ED90),
     'The same three-valued native vocation byte selects index=154+vocation.'),
 0x1EDDC: (range(157,160), (0x1EDC0,0x1EDDE),
     'Native choice maps through the six s16 alternative-vocation entries copied from ROM; index=157+mapped vocation.'),
 0x1F404: ([191], (0x1F3FC,0x1F406), 'Local SP+14C preserves the input table; constant offset BFh*4.'),
 0x1F42E: ([182], (0x1F426,0x1F430), 'Same local table; constant offset B6h*4.'),
 0x1F4EA: ([181], (0x1F4E2,0x1F4EC), 'Same local table; constant offset B5h*4.'),
 0x1F57C: ([182], (0x1F574,0x1F57E), 'Same local table; constant offset B6h*4.'),
 0x1F68E: ([184], (0x1F686,0x1F690), 'Same local table; constant offset B8h*4.'),
}


def parse(path):
    functions = []
    for line in path.read_text().splitlines():
        t = line.split('\t')
        if t[0] == 'FUNCTION':
            f = dict(entry=int(t[1],16), nodes={}, ops=[]); functions.append(f)
        elif t[0] == 'NODE':
            f['nodes'][t[1]] = dict(size=int(t[2]), constant=None if t[3]=='-' else int(t[3]), register=t[4], address=t[6] if len(t)>6 else None)
        elif t[0] == 'OP':
            f['ops'].append(dict(pc=int(t[1],16), sequence=int(t[2]), kind=t[3], output=t[4], inputs=t[5:]))
    return functions


def inspect(f, rom):
    register = 'r1' if f['entry']-0x08000000 in SECOND_ARGUMENT else 'r0'
    definitions = {o['output']:o for o in f['ops'] if o['output']!='-'}
    def calc(n, path=()):
        if n in path: return None
        node = f['nodes'][n]
        if node['constant'] is not None: return {('constant',node['constant'])}
        if n.startswith('input:08'):
            address = int(n.split(':')[1],16)
            if node['size']==8: return {('constant',address)} # CALL target, not data.
            return {('constant',int.from_bytes(rom[address-0x08000000:address-0x08000000+node['size']],'little'))}
        if n.startswith('input:') and node['register']==register: return {('table',0)}
        op = definitions.get(n)
        if not op: return None
        v = [calc(i,path+(n,)) for i in op['inputs']]; k=op['kind']
        if k in ('COPY','CAST','INT_ZEXT','INT_SEXT'): return v[0]
        if any(x is None for x in v): return None
        if k=='MULTIEQUAL': return set().union(*v)
        if k=='PTRADD':
            if any(c!='constant' or e!='constant' for c,d in v[1] for e,g in v[2]): return None
            return {(a,(b+d*g)&0xffffffff) for a,b in v[0] for c,d in v[1] for e,g in v[2]}
        if k not in ('INT_ADD','PTRSUB','INT_SUB','INT_MULT','INT_LEFT'): return None
        result=set()
        for a,x in v[0]:
            for b,y in v[1]:
                if k in ('INT_ADD','PTRSUB'):
                    if a==b=='table': return None
                    result.add(('table' if 'table' in (a,b) else 'constant',(x+y)&0xffffffff))
                elif k=='INT_SUB':
                    if a=='constant' and b=='table': return None
                    result.add(('constant' if a==b else a,(x-y)&0xffffffff))
                else:
                    if a!='constant' or b!='constant': return None
                    result.add(('constant',(x*y if k=='INT_MULT' else x<<y)&0xffffffff))
        return result
    tainted={n for n,node in f['nodes'].items() if n.startswith('input:') and node['register']==register}
    while True:
        before=len(tainted)
        for op in f['ops']:
            if op['kind'] not in ('LOAD','CALL','CALLIND') and op['output']!='-' and tainted.intersection(op['inputs']):
                tainted.add(op['output'])
        if before==len(tainted): break
    reads=[]; forwards=[]; control=[]
    switch_jumps={v['jump']:v for v in switches(rom,rom,0x5E000).values()}
    for op in f['ops']:
        if op['kind']=='LOAD' and op['inputs'][1] in tainted:
            pc=op['pc']-0x08000000; values=calc(op['inputs'][1])
            if values is None:
                require(pc in DOMAINS,'Unresolved town read '+hex(pc))
                indexes, span, reason=DOMAINS[pc]
                row=dict(pc=op['pc'],indexes=list(indexes),method='native domain',evidence=reason,
                    source_span=list(span),source_hex=rom[span[0]:span[1]].hex())
            else:
                require(all(k=='table' and n%4==0 and n<1200 for k,n in values),'Town read outside table')
                row=dict(pc=op['pc'],indexes=sorted(n//4 for k,n in values),method='SSA constant offsets')
            reads.append(row)
        if op['kind'] in ('CALL','CALLIND','STORE','RETURN') and tainted.intersection(op['inputs']):
            require(op['kind']=='CALL','Town base escape needs inspection')
            target=calc(op['inputs'][0]); require(target and len(target)==1,'Unknown town callee')
            forwards.append(dict(pc=op['pc'],target=next(iter(target))[1]))
        if op['kind'] in ('CALLIND','BRANCHIND'):
            pc=op['pc']-0x08000000
            # Native POP scratch; BX scratch is an epilogue, not a dispatch.
            half=struct.unpack_from('<H',rom,pc)[0]
            previous=struct.unpack_from('<H',rom,pc-2)[0]
            is_return=half&0xff87==0x4700 and previous&0xff00==0xbc00
            require(is_return or op['pc'] in switch_jumps,'Unresolved town indirect control')
            control.append(dict(pc=op['pc'],kind=op['kind'],opcode=half,
                disposition='saved-return epilogue' if is_return else 'bounded switch',
                switch=switch_jumps.get(op['pc'])))
    return dict(entry=f['entry'],table_register=register,reads=reads,forwards=forwards,indirect_control=control)


def run():
    original=load_base(); OUT.mkdir(parents=True,exist_ok=True)
    build=json.loads((ROOT/'build/english/build.json').read_text())
    compiled=(ROOT/'build/english/torneko-2-english.gba').read_bytes()
    require(digest(compiled)==build['output_sha256'],'Town audit build differs')
    functions=[]; exports={}
    for filename, addresses in GROUPS.items():
        path=OUT/filename
        subprocess.run(['bash','tools/ghidra.sh','dataflow',str(path),
                        *[hex(0x08000000+x) for x in addresses]],cwd=ROOT,check=True)
        parsed=parse(path)
        require({f['entry'] for f in parsed}=={0x08000000+x for x in addresses},'Incomplete SSA export')
        functions.extend(inspect(f,original) for f in parsed); exports[filename]=digest(path.read_bytes())
    roots={f['entry'] for f in functions}
    require(all(call['target'] in roots for f in functions for call in f['forwards']),'Uninspected forwarded table')
    require(direct_calls(original[:0x5E000],0x0801D544)==[0x08050080],'Additional synthesis caller')
    require(struct.pack('<I',0x0801D545) not in original,'Indirect synthesis entry')
    profiles=original[0x6B8F6:0x6B90F]
    require(set(profiles)=={0,201,202,203,204,205},'Remi profile selectors changed')
    require(set(struct.unpack_from('<6h',original,0x6B910))=={0,1,2},'Alternative vocation map changed')
    used={i for f in functions for r in f['reads'] for i in r['indexes']}
    sources=json.loads((ROOT/'build/oct07-text/unresolved-pointer-owners.json').read_text())['sources']
    descriptions={1:'Superseded two-item blacksmith offer',2:'Superseded matching-item blacksmith offer',
        35:'Old synthesis farewell',37:'Old synthesis selection instructions',214:'Version-error filler in 86 unused table slots',
        180:'Old storage deposit-choice menu',185:'Old storage withdrawal-choice menu',
        193:'Old storage save question',195:'Old storage save confirmation',196:'Old storage farewell'}
    dispositions=[]
    for row in sources:
        if not row['id'].startswith('town-'): continue
        require(not used.intersection(row['table_indexes']),'Town source has a recovered reader: '+row['id'])
        dispositions.append(dict(id=row['id'],indexes=row['table_indexes'],description=descriptions[min(row['table_indexes'])],
            disposition='dormant-in-recovered-service-graph',
            evidence='No read in 20 recovered service functions; complete branch SSA plus explicit computed-selector domains. Exact source pointers occur only in the town table.',
            source_sha256=next(e['source_sha256'] for e in json.loads((ROOT/'build/text-inventory/catalog.json').read_text())['entries'] if e['id']==row['id'])))
    require(len(dispositions)==10,'Town source cohort changed')
    report=dict(passed=True,source_sha256=digest(original),rom_sha256=digest(compiled),
        tool_sha256=digest(Path(__file__).read_bytes()),exports=exports,functions=functions,
        table_read_sites=sum(len(f['reads']) for f in functions),selected_indexes=sorted(used),
        sources=dispositions,scope=__doc__,
        limits='Native vocation state is 0..2, supported by existing 18 transaction cases; corrupt saves/RAM are excluded. Decompiler epilogues and original instruction spans are retained. Other unknown entry mechanisms remain outside this recovered graph. These dispositions do not translate or delete original dormant bytes.')
    (OUT/'town-dispositions.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Town source dispositions:',len(dispositions),'dormant records;',report['table_read_sites'],'read sites;',len(used),'selected indexes')
    return report

if __name__=='__main__': run()
