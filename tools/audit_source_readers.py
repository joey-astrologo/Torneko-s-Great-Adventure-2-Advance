"""Trace shared and relocated town table reads before following text consumers.

Missing reads remain unproven reachability, never automatically unused text.
The RAM image represents the town resource after its verified loader; other
overlaid uses of those addresses require caller/context review.
"""

import argparse
from collections import Counter
import json
from pathlib import Path
import struct

from tools.audit_text_callers import BASE, CONSUMERS, LIMIT, trace
from tools.audit_reader_routes import direct_calls, TABLE, END
from tools.lz77 import decompress
from tools.rom import ROOT, digest, load_base, require
from tools.town_text import RAM, relocate, resource


def inserted_resources(value):
    """Include both source-object and source-hex catalog schema families."""
    if isinstance(value, dict):
        if all(key in value for key in ('offset', 'encoded_hex', 'english')):
            yield value
        elif 'rom_offset' in value and 'encoded_hex' in value and value.get('language_status') == 'reviewed':
            from tools.screen_text_audit import display_text
            from tools.text_codec import tokenize
            yield value | {'offset':value['rom_offset'], 'english':display_text(tokenize(bytes.fromhex(value['encoded_hex']))[0])}
        for child in value.values():
            yield from inserted_resources(child)
    elif isinstance(value, list):
        for child in value:
            yield from inserted_resources(child)


def run(source, output, computed_switches=False):
    original = load_base()
    compiled = (source/'torneko-2-english.gba').read_bytes()
    build = json.loads((source/'build.json').read_text())
    require(digest(compiled) == build['output_sha256'], 'Source-reader ROM differs')
    inventory = json.loads((ROOT/'build/text-inventory/catalog.json').read_text())['entries']
    town_old = relocate(resource()['data'])
    town_new = relocate(decompress(compiled, build['dialogue']['town_resource']['rom_offset'])[0])
    images = ((RAM, (town_old, town_new)),)
    from tools.thumb_switches import switches
    domains = switches(original, compiled, LIMIT) if computed_switches else {}
    followed = {}

    def switch_observer(domain, seed):
        followed.setdefault(domain['guard'], set()).add(seed)

    switch_options = dict(switch_domains=domains, switch_observer=switch_observer)
    calls = {c: target for target in CONSUMERS for c in direct_calls(original, target) if c-BASE < LIMIT}
    seeds, literals = set(), []
    for pc in range(0, LIMIT, 2):
        op = struct.unpack_from('<H', original, pc)[0]
        if op & 0xF800 != 0x4800:
            continue
        literal = ((pc+4) & ~3) + (op & 255)*4
        value = struct.unpack_from('<I', original, literal)[0]
        if not (TABLE <= value < END or RAM <= value < RAM+1200):
            continue
        entry = next((p for p in range(pc, max(-1, pc-6000), -2)
                      if struct.unpack_from('<H', original, p)[0] & 0xFF00 == 0xB500), pc)
        seeds.update((pc, entry))
        seeds.update(range(max(0, pc-20), pc, 2))
        literals.append({'load': pc+BASE, 'literal': literal, 'original_value': value,
                         'compiled_value': struct.unpack_from('<I', compiled, literal)[0], 'entry_seed': entry+BASE})
    for call in calls:
        seeds.add(next((p for p in range(call-BASE, max(-1, call-BASE-6000), -2)
                        if struct.unpack_from('<H', original, p)[0] & 0xFF00 == 0xB500), call-BASE))
    reads = {}

    def observe(pc, addresses, size, values, seed):
        at = addresses[0]
        if size == 4 and (TABLE <= at < END or RAM <= at < RAM+1200):
            reads.setdefault((pc, at, addresses[1]), {'load': pc, 'addresses': addresses,
                              'values': values, 'seed': seed,
                              'family': 'shared' if TABLE <= at < END else 'town-overlay'})

    routes, limits, stops = trace(original, compiled, seeds, calls, budget=20000,
                                  memory_images=images, read_observer=observe, **switch_options)
    found = {r['call'] for r in routes}
    extra_seeds = {pc for call in set(calls)-found for pc in range(max(0, call-BASE-64), call-BASE, 2)
                   if struct.unpack_from('<H', original, pc)[0] & 0xF800 in (0x2000, 0x4800)}
    extra, more_limits, more_stops = trace(original, compiled, extra_seeds, calls, budget=2500,
                                          memory_images=images, read_observer=observe, **switch_options)
    routes = list({(r['call'], r['original_argument'], r['compiled_argument']): r for r in routes+extra}.values())
    found = {r['call'] for r in routes}
    unresolved = [{'call': c, 'consumer': calls[c], 'consumer_name': CONSUMERS[calls[c]][0]}
                  for c in sorted(set(calls)-found)]
    observed_calls = {}

    def observe_call(pc, target, arguments, seed, path):
        key = (pc, target, tuple(arguments), seed)
        observed_calls.setdefault(key, dict(call=pc, target=target, arguments=arguments, seed=seed, path=path))
    # Follow stack-relative destinations as a separate analysis layer. This
    # identifies producers to investigate, without declaring their contents English.
    stack_routes, stack_limits, stack_stops = trace(original, compiled, seeds | extra_seeds,
        calls, budget=20000, memory_images=images, stack_model=True, read_observer=observe,
        call_observer=observe_call, paired_stack_adjustments=True, **switch_options)
    # These existing entry hooks replay the original eight-byte prologue
    # and replace the incoming town-table pointer. Validate their actual code,
    # then resume constant propagation at their original continuation.
    private_entries, initial = [], {}
    for key, entry in (('blacksmith', 0x1D110), ('gaibara', 0x1D544),
                       ('remi', 0x1E75C), ('mayor', 0x20564), ('town_actions', 0x1E490)):
        owner = build[key]
        helper = owner['helper_offset']
        table = owner['message_table_offset' if key == 'town_actions' else 'table_offset']+BASE
        require(compiled[helper:helper+8] == original[entry:entry+8], 'Private entry prologue differs')
        op, branch_load, bx = struct.unpack_from('<3H', compiled, helper+8)
        require(op & 0xFF00 == 0x4800 and branch_load & 0xF800 == 0x4800,
                'Private entry table/continuation loads differ')
        table_literal = ((helper+12) & ~3)+(op & 255)*4
        return_literal = ((helper+14) & ~3)+(branch_load & 255)*4
        target = struct.unpack_from('<I', compiled, return_literal)[0]
        require(struct.unpack_from('<I', compiled, table_literal)[0] == table
                and target == BASE+entry+9 and bx == 0x4700 | (((branch_load >> 8) & 7) << 3),
                'Private entry native target differs')
        initial[entry+8] = {0: (RAM, table), 13: (0x0FFFFFEC,)*2}
        private_entries.append({'family': key, 'entry': entry+BASE, 'helper': helper+BASE,
                                'continuation': target & ~1, 'original_table': RAM, 'compiled_table': table})
    private_routes, private_limits, private_stops = trace(original, compiled, set(initial), calls,
        budget=120000, memory_images=images, read_observer=observe, stack_model=True, initial_registers=initial,
        call_observer=observe_call, paired_stack_adjustments=True, max_path_length=4096, **switch_options)
    stack_routes += private_routes
    # Follow only observed calls passing the verified town-table base. The
    # original dispatcher and storage selector pass this table in r0. This
    # propagates the actual argument instead of guessing it for every service.
    town_contexts, done_contexts = [], set()
    for depth in range(4):
        pending = []
        for call in list(observed_calls.values()):
            args, target = call['arguments'], call['target']
            if args[0] != (RAM, RAM) or not BASE <= target < BASE+LIMIT:
                continue
            context = (target, tuple(args))
            if context not in done_contexts:
                done_contexts.add(context);pending.append(call)
        if not pending:
            break
        for call in pending:
            target = call['target']-BASE
            regs = {i: value for i, value in enumerate(call['arguments']) if value is not None
                    and not any(0x0FFF0000 <= a <= 0x10010000 for a in value)}
            extra_rows, extra_limits, extra_stops = trace(original, compiled, {target}, calls,
                budget=120000, memory_images=images, read_observer=observe, stack_model=True,
                initial_registers={target: regs}, call_observer=observe_call, paired_stack_adjustments=True,
                max_path_length=4096, **switch_options)
            stack_routes += extra_rows
            town_contexts.append(dict(call=call['call'], target=call['target'], arguments=call['arguments'],
                                      depth=depth, limits=extra_limits, stops=extra_stops))
    english = {r['offset']+BASE:r for r in inserted_resources(build)}
    for pointer, row in english.items():
        raw = bytes.fromhex(row['encoded_hex'])
        require(compiled[pointer-BASE:pointer-BASE+len(raw)] == raw, 'English resource bytes differ')
    for route in stack_routes:
        resource_row = english.get(route['compiled_argument'])
        if resource_row:
            route.update(binding='bound-english-resource', english=resource_row['english'])
    sources = []
    for row in inventory:
        if row['language_status'] != 'untranslated' or row['family'] not in ('shared-system', 'town'):
            continue
        pointer = (BASE+int(row['id'][4:], 16) if row['id'].startswith('rom.')
                   else RAM+int(row['id'].split('.')[1], 16))
        uses = [r for r in reads.values() if r['values'][0] == pointer]
        consumers = [r for r in routes+stack_routes if r['original_argument'] == pointer]
        sources.append({'id': row['id'], 'japanese': row['japanese'], 'source_sha256': row['source_sha256'],
                        'table_reads': uses, 'consumer_candidates': consumers,
                        'disposition': 'reader-candidate-needs-context' if uses or consumers
                                       else 'no-resolved-reader-in-bounded-scan'})
    prior_unresolved = {r['call'] for r in unresolved}
    producer_index = {}
    for producer in observed_calls.values():
        register = {0x08000FB8:0, 0x0805CF54:0, 0x0800EF30:1, 0x0800EEF0:1, 0x0800F244:1}.get(producer['target'])
        dest = producer['arguments'][register] if register is not None else None
        if dest:
            producer_index.setdefault((*dest, producer['seed']), []).append(producer)
    followup = []
    for call in sorted(prior_unresolved):
        matches = [r for r in stack_routes if r['call'] == call]
        producers = []
        for match in matches:
            key = match['original_argument'], match['compiled_argument'], match['seed']
            for producer in producer_index.get(key, ()):
                if producer['call'] in match['path'][:-1]:
                    producers.append(producer)
        kind = ('bound-english-resource' if matches and all(r.get('binding') == 'bound-english-resource' for r in matches) else
                'stack-buffer-with-producer-candidate' if producers else
                'stack-buffer-needs-producer' if any(r['argument_kind'] == 'stack-relative' for r in matches)
                else 'concrete-argument-needs-context' if matches else 'unresolved-data-flow')
        followup.append({'call': call, 'consumer': calls[call], 'classification': kind,
                         'routes': matches, 'producer_candidates': producers})
    report = {'rom_sha256': digest(compiled), 'source_sha256': digest(original),
              'tool_sha256': digest(Path(__file__).read_bytes()), 'scan_range': [BASE, BASE+LIMIT],
              'engine_sha256': digest((ROOT/'tools/audit_text_callers.py').read_bytes()),
              'service_context_path_limit':4096,
              'computed_switches': list(domains.values()),
              'followed_switches': [dict(guard=guard, seeds=sorted(seeds)) for guard,seeds in sorted(followed.items())],
              'switch_engine_sha256': digest((ROOT/'tools/thumb_switches.py').read_bytes()) if domains else None,
              'sources': sources, 'source_dispositions': dict(Counter(r['disposition'] for r in sources)),
              'literal_candidates': literals, 'table_reads': list(reads.values()),
              'candidate_routes': routes, 'unresolved_calls': unresolved,
              'argument_followup': followup,
              'argument_followup_counts': dict(Counter(r['classification'] for r in followup)),
              'stack_model_limits': stack_limits, 'stack_model_stop_reasons': stack_stops,
              'private_entry_models': private_entries, 'private_entry_limits': private_limits,
              'town_call_contexts': town_contexts,
              'private_entry_stop_reasons': private_stops,
              'budget_limits': limits+more_limits, 'stop_reasons': dict(Counter(stops)+Counter(more_stops)),
              'scope': __doc__ + ' Constant propagation and local seeds are conservative candidates. '
                       'Patched instructions, unknown RAM, indirect control flow and unresolved arguments remain explicit; '
                       'absence of a resolved read is not proof of unused code.'}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
    print('Source readers:', report['source_dispositions'], 'table reads:', len(reads),
          'resolved calls:', len(found), 'unresolved:', len(unresolved), flush=True)
    for row in sources:
        if row['table_reads'] or row['consumer_candidates']:
            print(row['id'], 'reads', [hex(r['load']) for r in row['table_reads']],
                  'calls', [hex(r['call']) for r in row['consumer_candidates']])
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=ROOT/'build/english')
    parser.add_argument('--output', type=Path, default=ROOT/'build/localization-closure/source-readers.json')
    parser.add_argument('--computed-switches', action='store_true', help='Follow verified bounded jump-table patterns')
    args = parser.parse_args()
    run(args.source, args.output, args.computed_switches)
