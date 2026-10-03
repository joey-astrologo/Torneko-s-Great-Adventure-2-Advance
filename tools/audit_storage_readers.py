"""Follow all eight verified storage switch branches with the actual town table.

This supplies dispatcher context to bounded static analysis. It does not prove
ordinary gameplay reaches every choice, and unknown paths remain unresolved.
"""
import argparse
import json
from pathlib import Path
import struct

from tools.audit_reader_routes import direct_calls
from tools.audit_source_readers import inserted_resources
from tools.audit_text_callers import BASE, CONSUMERS, LIMIT, trace
from tools.lz77 import decompress
from tools.rom import ROOT, digest, load_base, require
from tools.town_text import RAM, relocate, resource


def run(source=ROOT/'build/english', output=ROOT/'build/localization-closure/storage-readers.json'):
    original = load_base()
    compiled = (source/'torneko-2-english.gba').read_bytes()
    build = json.loads((source/'build.json').read_text())
    require(digest(compiled) == build['output_sha256'], 'Storage audit ROM differs')
    require(original[0x1F2D8:0x1F2E4] == compiled[0x1F2D8:0x1F2E4]
            == bytes.fromhex('f0b582b0041c0d1c171c1e1c'), 'Storage prologue differs')
    require(original[0x1F354:0x1F3D6] == compiled[0x1F354:0x1F3D6], 'Storage switch changed')
    require(struct.unpack_from('<I', original, 0x1F360)[0] == BASE+0x1F364,
            'Storage switch table differs')
    branches = struct.unpack_from('<8I', original, 0x1F364)
    require(branches == tuple(BASE+p for p in (0x1F384,0x1F398,0x1F3AC,0x1F3BE,
                                               0x1F38E,0x1F3A2,0x1F3B6,0x1F3CA)),
            'Storage branch identities differ')
    require(struct.unpack_from('<I', original, 0x5019C)[0]
            == struct.unpack_from('<I', compiled, 0x5019C)[0] == RAM,
            'Native storage dispatcher town argument differs')
    require(struct.unpack_from('<I', original, 0x501A0)[0]
            == struct.unpack_from('<I', compiled, 0x501A0)[0] == 0x020096B4,
            'Native storage dispatcher fourth argument differs')
    images = ((RAM, (relocate(resource()['data']),
                    relocate(decompress(compiled, build['dialogue']['town_resource']['rom_offset'])[0]))),)
    calls = {c:t for t in CONSUMERS for c in direct_calls(original,t) if c-BASE < LIMIT}
    reads, observed, routes, contexts = {}, {}, [], []

    def observe(pc, addresses, size, values, seed):
        if size == 4 and RAM <= addresses[0] < RAM+1200:
            reads.setdefault((pc,*addresses),dict(load=pc,addresses=addresses,values=values,seed=seed))

    def observe_call(pc, target, args, seed, path):
        if (RAM,RAM) in args and BASE <= target < BASE+LIMIT and target not in CONSUMERS:
            observed.setdefault((target,tuple(args)),dict(call=pc,target=target,arguments=args,seed=seed))

    def follow(seed, regs, provenance):
        rows, limits, stops = trace(original,compiled,{seed},calls,budget=30000,
            max_path_length=2000,memory_images=images,read_observer=observe,
            stack_model=True,initial_registers={seed:regs},call_observer=observe_call,
            paired_stack_adjustments=True)
        routes.extend(rows)
        contexts.append(dict(seed=seed+BASE,registers=regs,provenance=provenance,limits=limits,stops=stops))
        print('Storage context',hex(seed+BASE),'routes',len(rows),'limits',len(limits),flush=True)

    for choice, branch in enumerate(branches):
        follow(branch-BASE,{4:(RAM,RAM),5:(0,0),6:(0x020096B4,)*2,13:(0x0FFFFFE4,)*2},
               dict(kind='verified-selector-switch',choice=choice,selector=BASE+0x1F2D8))
    done = set()
    for depth in range(4):
        pending = [(key,value) for key,value in observed.items() if key not in done]
        if not pending:
            break
        for key, call in pending:
            done.add(key)
            regs = {i:v for i,v in enumerate(call['arguments']) if v is not None
                    and not any(0x0FFF0000 <= a <= 0x10010000 for a in v)}
            follow(call['target']-BASE,regs,dict(kind='observed-call',depth=depth,**call))
    english = {r['offset']+BASE:r for r in inserted_resources(build)}
    for row in routes:
        target = english.get(row['compiled_argument'])
        if target:
            raw = bytes.fromhex(target['encoded_hex'])
            require(compiled[row['compiled_argument']-BASE:row['compiled_argument']-BASE+len(raw)] == raw,
                    'Storage English binding bytes differ')
            row.update(binding='bound-english-resource',english=target['english'])
    inventory = json.loads((ROOT/'build/text-inventory/catalog.json').read_text())['entries']
    sources = []
    for row in inventory:
        if row['language_status'] == 'untranslated' and row['family'] == 'town':
            pointer = RAM+int(row['id'].split('.')[1],16)
            sources.append(dict(id=row['id'],japanese=row['japanese'],source_sha256=row['source_sha256'],
                table_reads=[r for r in reads.values() if r['values'][0] == pointer],
                consumer_candidates=[r for r in routes if r['original_argument'] == pointer]))
    report = dict(rom_sha256=digest(compiled),source_sha256=digest(original),
        tool_sha256=digest(Path(__file__).read_bytes()),
        engine_sha256=digest((ROOT/'tools/audit_text_callers.py').read_bytes()),
        switch_branches=branches,contexts=contexts,table_reads=list(reads.values()),
        routes=routes,sources=sources,scope=__doc__)
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print('Storage unresolved-source candidates:',
          [(r['id'],len(r['table_reads']),len(r['consumer_candidates'])) for r in sources],flush=True)
    return report


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,default=ROOT/'build/english')
    parser.add_argument('--output',type=Path,default=ROOT/'build/localization-closure/storage-readers.json')
    args=parser.parse_args();run(args.source,args.output)
