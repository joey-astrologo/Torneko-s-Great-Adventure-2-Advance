"""Seed verified bounded jump tables and retain every resulting text binding.

Guard seeds have unknown incoming arguments. Results are discovery evidence,
not proof that an ordinary gameplay path reaches every enumerated selector.
"""
import argparse
import json
from pathlib import Path

from tools.audit_reader_routes import direct_calls, TABLE, END
from tools.audit_text_callers import BASE, CONSUMERS, LIMIT, trace
from tools.lz77 import decompress
from tools.rom import ROOT, digest, load_base, require
from tools.thumb_switches import switches
from tools.town_text import RAM, relocate, resource


def run(source, output, guard=None, budget=40000, maximum_path=4096):
    original = load_base()
    compiled = (source/'torneko-2-english.gba').read_bytes()
    build = json.loads((source/'build.json').read_text())
    require(digest(compiled) == build['output_sha256'], 'Switch audit ROM differs')
    domains = switches(original, compiled, LIMIT)
    require(budget>0 and maximum_path>0, 'Switch audit limits must be positive')
    require(guard is None or guard-BASE in domains, 'Requested guard is not a verified switch')
    seeds=set(domains) if guard is None else {guard-BASE}
    old = relocate(resource()['data'])
    new = relocate(decompress(compiled, build['dialogue']['town_resource']['rom_offset'])[0])
    consumers = {pc: target for target in CONSUMERS for pc in direct_calls(original, target)
                 if pc-BASE < LIMIT}
    reads, calls, followed = {}, {}, {}
    stop_details = []

    def read(pc, addresses, size, values, seed):
        if size == 4 and (TABLE <= addresses[0] < END or RAM <= addresses[0] < RAM+1200):
            reads.setdefault((pc, *addresses, seed), dict(load=pc, addresses=addresses,
                                                       values=values, seed=seed))

    def call(pc, target, arguments, seed, path):
        calls.setdefault((pc, target, tuple(arguments), seed),
                         dict(call=pc, target=target, arguments=arguments, seed=seed))

    def switch(domain, seed):
        followed.setdefault(domain['guard'], set()).add(seed)

    routes, limits, stops = trace(original, compiled, seeds, consumers,
        budget=budget, max_path_length=maximum_path, memory_images=((RAM, (old, new)),),
        read_observer=read, call_observer=call, switch_domains=domains,
        switch_observer=switch, stack_model=True, paired_stack_adjustments=True,
        stop_observer=stop_details.append)
    report = dict(rom_sha256=digest(compiled), source_sha256=digest(original),
        tool_sha256=digest(Path(__file__).read_bytes()),
        engines={name:digest((ROOT/'tools'/name).read_bytes()) for name in
                 ('audit_text_callers.py', 'thumb_switches.py')},
        scan_range=[BASE, BASE+LIMIT], seeds=[BASE+s for s in sorted(seeds)],
        budget_per_seed=budget, maximum_path=maximum_path,
        switches=list(domains.values()), routes=routes, limits=limits, stops=stops,
        stop_details=stop_details,
        reads=list(reads.values()), calls=list(calls.values()),
        followed=[dict(guard=guard, seeds=sorted(seeds)) for guard,seeds in sorted(followed.items())],
        scope=__doc__)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2)+'\n')
    print('Switch readers:', len(domains), 'guards;', len(routes), 'bindings;', len(limits), 'budget limits')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=ROOT/'build/english')
    parser.add_argument('--output', type=Path, default=ROOT/'build/caller-branches/switch-readers.json')
    parser.add_argument('--guard', type=lambda value:int(value,0), help='Restrict seed to one verified CPU guard address')
    parser.add_argument('--budget', type=int, default=40000)
    parser.add_argument('--maximum-path', type=int, default=4096)
    args = parser.parse_args()
    run(args.source, args.output, args.guard, args.budget, args.maximum_path)
