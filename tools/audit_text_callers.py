"""Trace bounded Thumb constants to text consumers in source and compiled ROMs.

This is caller triage, not a proof of reachability or complete disassembly.
Every matching call is retained, including unresolved arguments. Source review
status never filters callers. Findings require disassembly and native follow-up.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import struct
import re

from tools.audit_reader_routes import BASE, direct_calls
from tools.rom import ROOT, digest, load_base, require
from tools.text_codec import tokenize, readable

LIMIT = 0x5E000
CONSUMERS = {0x08000FB8: ('formatter', 1), 0x08015848: ('player-wrapper', 0),
             0x0801588C: ('queue', 0), 0x08017068: ('modal', 0),
             0x08002298: ('window-reader', 1), 0x080021B4: ('text-reader', 1)}
PRIMARY_CONSUMERS = tuple(CONSUMERS)
CONSUMERS.update({0x08015A18: ('choice-modal-wrapper', 0),
                  0x08015A34: ('positioned-modal-wrapper', 0),
                  0x08015A50: ('modal-reader', 0),
                  0x0805CF54: ('string-copy', 1)})
FORWARDERS = {0x0801C958: ('relic-message-helper', 1),
              0x08057B54: ('link-status-window', 0),
              0x08057BDC: ('link-notice-modal', 0),
              0x0801D0A0: ('town-service-modal', 0),
              0x0801D0D8: ('town-service-choice', 0)}
CONSUMERS.update(FORWARDERS)


def resources(value):
    if isinstance(value, dict):
        if isinstance(value.get('source'), dict) and 'raw_hex' in value['source'] and 'english' in value:
            yield value
        for child in value.values():
            yield from resources(child)
    elif isinstance(value, list):
        for child in value:
            yield from resources(child)


def compare_flags(a, b):
    """NZCV for the Thumb CMP subtraction, without signed Python overflow."""
    result = (a-b) & 0xFFFFFFFF
    return ((result >> 31) << 3 | (result == 0) << 2 | (a >= b) << 1 |
            bool((a ^ b) & (a ^ result) & 0x80000000))


def condition(code, flags):
    n, z, c, v = (bool(flags & bit) for bit in (8, 4, 2, 1))
    return (z, not z, c, not c, n, not n, v, not v,
            c and not z, not c or z, n == v, n != v,
            not z and n == v, z or n != v)[code]


def trace(original, compiled, seeds, calls, budget=12000, memory_images=(), read_observer=None,
          stack_model=False, initial_registers=None, call_observer=None, paired_stack_adjustments=False,
          max_path_length=900, switch_domains=None, switch_observer=None, stop_observer=None,
          unknown_operand_observer=None):
    """Conservative constants, paired across ROMs; unknown operations stop a path.

    Unknown conditional branches fork, so impossible paths can survive. Calls clear
    caller-saved constants. Patched instructions stop propagation; only changed
    literal/data reads are followed. Nearest PUSH seeds are explicitly heuristic.
    """
    observations, limits, stops = {}, [], Counter()
    def stop(reason):
        stops[reason] += 1
        if stop_observer is not None:
            stop_observer(dict(reason=reason, address=pc+BASE, seed=seed+BASE,
                original_hex=original[pc:pc+4].hex() if 0 <= pc < len(original) else None,
                compiled_hex=compiled[pc:pc+4].hex() if 0 <= pc < len(compiled) else None,
                registers={str(k):v for k,v in sorted(regs.items())},
                path_length=len(trail), tail=[BASE+p for p in trail[-32:]],
                repeated_addresses=[dict(address=BASE+p,visits=n)
                                    for p,n in Counter(trail).most_common(8) if n>1]))
    def half(at):
        return struct.unpack_from('<H', original, at)[0]
    def read(pair, size=4):
        if pair is None:
            return None
        values = []
        for side, (address, rom) in enumerate(zip(pair, (original, compiled))):
            if BASE <= address <= BASE+len(rom)-size:
                raw = rom[address-BASE:address-BASE+size]
            else:
                image = next(((start, images[side]) for start, images in memory_images
                              if start <= address <= start+len(images[side])-size), None)
                if image is None:
                    return None
                start, payload = image
                raw = payload[address-start:address-start+size]
            values.append(int.from_bytes(raw, 'little'))
        value = tuple(values)
        if read_observer is not None:
            read_observer(pc+BASE, pair, size, value, seed+BASE)
        return value
    def binary(x, y, fn):
        if unknown_operand_observer is not None and (x is None) != (y is None):
            unknown_operand_observer(pc+BASE, half(pc), x, y, seed+BASE)
        return None if x is None or y is None else tuple(fn(a, b) & 0xFFFFFFFF for a, b in zip(x, y))
    for seed in sorted(seeds):
        # Synthetic addresses identify stack-relative arguments only. They are
        # never dereferenced as real memory or treated as translated strings.
        initial = {13: (0x10000000, 0x10000000)} if stack_model else {}
        initial.update((initial_registers or {}).get(seed, {}))
        work = [(seed, initial, ())]
        seen = set()
        steps = 0
        while work and steps < budget:
            pc, regs, trail = work.pop()
            key = (pc, tuple(sorted(regs.items())))
            if key in seen:
                continue
            if not 0 <= pc < min(LIMIT, len(original)-1, len(compiled)-1):
                stop('outside_scan_range')
                continue
            if len(trail) >= max_path_length:
                stop('path_length_limit')
                continue
            seen.add(key)
            steps += 1
            v = half(pc)
            switch = (switch_domains or {}).get(pc)
            if switch and regs.get(switch['index_register']) is None:
                # The unsigned range guard proves the finite in-range domain.
                # Keep its default branch separately, with the index unknown.
                for index in range(switch['count']):
                    branch_regs = dict(regs)
                    branch_regs[switch['index_register']] = (index, index)
                    branch_regs[999] = (compare_flags(index, switch['count']-1),)*2
                    work.append((pc+4, branch_regs, trail+(pc, pc+2)))
                # CMP replaces prior flags on the default path too. For an
                # unsigned index above an eight-bit bound, these representatives
                # cover all possible NZCV results without inventing an index.
                bound = switch['count']-1
                for flags in {compare_flags(value, bound) for value in
                              (switch['count'], 0x80000000, 0x80000000+switch['count'])}:
                    branch_regs = dict(regs)
                    branch_regs[999] = (flags, flags)
                    work.append((switch['default']-BASE, branch_regs, trail+(pc, pc+2)))
                if switch_observer:
                    switch_observer(switch, seed+BASE)
                continue
            patched_stack = (paired_stack_adjustments and stack_model and v & 0xFF00 == 0xB000
                             and struct.unpack_from('<H', compiled, pc)[0] & 0xFF00 == 0xB000)
            if original[pc:pc+2] != compiled[pc:pc+2] and not patched_stack:
                stop('patched_instruction')
                continue
            n, d, s = pc+2, v & 7, (v >> 3) & 7
            def assign(dst, value):
                if value is None:
                    regs.pop(dst, None)
                else:
                    regs[dst] = value
            # Only CMP flags are modeled. Every other flag-writing operation
            # invalidates them; calls also invalidate APSR. This prunes bounded
            # table loops without inventing outcomes for unknown RAM values.
            flags = regs.get(999)
            writes_flags = (v < 0x4400 or v & 0xFC00 == 0x4400 and (v >> 8) & 3 == 1)
            if writes_flags:
                assign(999, None)
            if v & 0xF800 == 0x2000:
                assign((v >> 8) & 7, (v & 255, v & 255))
            elif v & 0xF800 in (0x3000, 0x3800):
                d = (v >> 8) & 7
                sign = 1 if v & 0xF800 == 0x3000 else -1
                assign(d, binary(regs.get(d), (v & 255, v & 255), lambda a, b: a+sign*b))
            elif v & 0xF800 == 0x4800:
                at = BASE + ((pc+4) & ~3) + (v & 255)*4
                assign((v >> 8) & 7, read((at, at)))
            elif v & 0xF800 == 0x1800:
                third = (v >> 6) & 7
                x = (third, third) if v & 0x400 else regs.get(third)
                assign(d, binary(regs.get(s), x, lambda a, b: a-b if v & 0x200 else a+b))
            elif v & 0xF800 in (0, 0x800, 0x1000):
                shift = (v >> 6) & 31
                x = regs.get(s)
                if x is not None:
                    x = tuple((a << shift if v & 0xF800 == 0 else a >> (shift or 32)
                               if v & 0xF800 == 0x800 else
                               (a-0x100000000 if a & 0x80000000 else a) >> (shift or 32)) & 0xFFFFFFFF for a in x)
                assign(d, x)
            elif v & 0xFC00 == 0x4400:
                d, s, kind = (v & 7) | ((v >> 4) & 8), (v >> 3) & 15, (v >> 8) & 3
                if kind == 0:
                    assign(d, binary(regs.get(d), regs.get(s), lambda a, b: a+b))
                elif kind == 2:
                    assign(d, regs.get(s))
                elif kind == 1:
                    assign(999, binary(regs.get(d), regs.get(s), compare_flags))
                elif kind == 3:
                    stop('indirect_branch_or_return')
                    continue
                if d == 15:
                    switch = (switch_domains or {}).get(pc-12)
                    target = regs.get(15)
                    if (switch and kind == 2 and target and target[0] == target[1]
                            and target[0] in switch['targets']):
                        n = target[0]-BASE
                        regs.pop(15, None)
                        work.append((n, regs, trail+(pc,)))
                        continue
                    stop('computed_pc')
                    continue
            elif v & 0xF800 in (0x6800, 0x7800, 0x8800):
                size = {0x6800: 4, 0x7800: 1, 0x8800: 2}[v & 0xF800]
                off = ((v >> 6) & 31)*size
                assign(d, read(binary(regs.get(s), (off, off), lambda a, b: a+b), size))
            elif v & 0xF800 == 0x9000:
                assign(1000+(v & 255)*4, regs.get((v >> 8) & 7))
            elif v & 0xF800 == 0x9800:
                assign((v >> 8) & 7, regs.get(1000+(v & 255)*4))
            elif v & 0xF800 in (0x6000, 0x7000, 0x8000):
                # Unknown stores may alias tracked stack locals.
                for k in list(regs):
                    if k >= 1000:
                        regs.pop(k)
            elif v & 0xF800 in (0xA000, 0xA800):
                if stack_model:
                    origin = regs.get(13) if v & 0x800 else ((pc+BASE+4) & ~3,)*2
                    assign((v >> 8) & 7, binary(origin, ((v & 255)*4,)*2, lambda a,b:a+b))
                else:
                    assign((v >> 8) & 7, None)
            elif v & 0xF000 == 0x5000:
                kind = (v >> 9) & 7
                if kind >= 3:
                    size = 4 if kind == 4 else 2 if kind in (5, 7) else 1
                    value = read(binary(regs.get(s), regs.get((v >> 6) & 7), lambda a, b: a+b), size)
                    if value is not None and kind in (3, 7):
                        value = tuple((a-(1 << (size*8)) if a & (1 << (size*8-1)) else a) & 0xFFFFFFFF for a in value)
                    assign(d, value)
                else:
                    for k in list(regs):
                        if k >= 1000:
                            regs.pop(k)
            elif v & 0xFC00 == 0x4000:
                kind = (v >> 6) & 15
                if kind == 10:
                    assign(999, binary(regs.get(d), regs.get(s), compare_flags))
                elif kind in (0, 1, 12, 13, 14):
                    fn = {0: lambda a,b:a&b, 1: lambda a,b:a^b,
                          12: lambda a,b:a|b, 13: lambda a,b:a*b,
                          14: lambda a,b:a&~b}[kind]
                    assign(d, binary(regs.get(d), regs.get(s), fn))
                elif kind == 15:
                    assign(d, binary(regs.get(s), (0, 0), lambda a,b:~a))
                elif kind not in (8, 11):
                    assign(d, None)
            elif v & 0xF800 == 0x2800:
                assign(999, binary(regs.get((v >> 8) & 7), (v & 255, v & 255), compare_flags))
            elif v & 0xFE00 == 0xB400:
                if stack_model:
                    size = ((v & 255).bit_count() + bool(v & 0x100))*4
                    assign(13, binary(regs.get(13), (size,)*2, lambda a,b:a-b))
            elif v & 0xFE00 == 0xBC00:
                if v & 0x100:
                    continue
                for i in range(8):
                    if v & (1 << i):
                        assign(i, None)
                if stack_model:
                    size = (v & 255).bit_count()*4
                    assign(13, binary(regs.get(13), (size,)*2, lambda a,b:a+b))
            elif v & 0xFF00 == 0xB000:
                if stack_model:
                    ops = (v, struct.unpack_from('<H', compiled, pc)[0] if paired_stack_adjustments else v)
                    deltas = tuple((op & 127)*4*(-1 if op & 128 else 1) for op in ops)
                    assign(13, binary(regs.get(13), deltas, lambda a,b:a+b))
                for k in list(regs):
                    if k >= 1000:
                        regs.pop(k)
            elif v & 0xF800 in (0xC000, 0xC800):
                base_register = (v >> 8) & 7
                base_address = regs.get(base_register)
                if v & 0xF800 == 0xC800 and v & 255:
                    # ARM7 LDMIA reads successive words before writeback. If
                    # the base is in the register list, retain its loaded value.
                    offset = 0
                    for i in range(8):
                        if v & (1 << i):
                            address = binary(base_address, (offset,)*2, lambda a,b:a+b)
                            assign(i, read(address))
                            offset += 4
                    if not v & (1 << base_register):
                        assign(base_register, binary(base_address, (offset,)*2, lambda a,b:a+b))
                else:
                    assign(base_register, None)
                    if v & 0xF800 == 0xC800:
                        stop('empty_ldmia_register_list')
                        continue
            elif v & 0xF000 == 0xD000:
                if v & 0xF00 >= 0xE00:
                    continue
                off = v & 255
                outcomes = {condition((v >> 8) & 15, f) for f in flags} if flags else {False, True}
                if True in outcomes:
                    work.append((pc+4+(off-256 if off & 128 else off)*2, dict(regs), trail+(pc,)))
                if False not in outcomes:
                    continue
            elif v & 0xF800 == 0xE000:
                off = v & 2047
                n = pc+4+(off-2048 if off & 1024 else off)*2
            elif v & 0xF800 == 0xF000 and half(pc+2) & 0xF800 == 0xF800:
                if original[pc:pc+4] != compiled[pc:pc+4]:
                    stop('patched_call')
                    continue
                if call_observer is not None:
                    hi = v & 2047
                    offset = ((hi-2048 if hi & 1024 else hi) << 12) + ((half(pc+2) & 2047) << 1)
                    call_observer(pc+BASE, pc+BASE+4+offset, [regs.get(i) for i in range(4)], seed+BASE,
                                  [p+BASE for p in trail]+[pc+BASE])
                if pc+BASE in calls:
                    target = calls[pc+BASE]
                    arg = regs.get(CONSUMERS[target][1])
                    if arg:
                        observation = {'call': pc+BASE, 'consumer': target,
                            'original_argument': arg[0], 'compiled_argument': arg[1],
                            'seed': seed+BASE, 'path': [p+BASE for p in trail]+[pc+BASE]}
                        if stack_model:
                            observation['register_arguments'] = [regs.get(i) for i in range(4)]
                            observation['argument_kind'] = ('stack-relative' if all(0x0FFF0000 <= a <= 0x10010000 for a in arg)
                                                            else 'concrete-address-or-value')
                        observations.setdefault((pc+BASE, *arg), observation)
                for i in (0, 1, 2, 3, 12, 999):
                    assign(i, None)
                n = pc+4
            else:
                stop(f'unsupported_opcode_{v:04x}')
                continue
            work.append((n, regs, trail+(pc,)))
        if work:
            limits.append({'seed': seed+BASE, 'remaining_states': len(work), 'steps': steps})
    return list(observations.values()), limits, dict(stops)


def run(source, output, expand=False, wrappers=False, forwarders=False):
    original = load_base()
    compiled = (source/'torneko-2-english.gba').read_bytes()
    build = json.loads((source/'build.json').read_text())
    require(digest(compiled) == build['output_sha256'], 'Caller audit ROM/ledger mismatch')
    inventory = json.loads((ROOT/'build/text-inventory/catalog.json').read_text())
    sources = {BASE+int(r['id'][4:], 16): r for r in inventory['entries'] if r['id'].startswith('rom.')}
    english, translated_sources = {}, {}
    for row in resources(build):
        translated_sources.setdefault(row['source']['sha256'], []).append(row['english'])
        if 'offset' in row and 'encoded_hex' in row:
            english[row['offset']+BASE] = row
    notices = {r['source']['offset']+BASE: r for r in build['combat']['queue_notices']['entries']}
    players = {r['source']['offset']+BASE: r for r in build['player_messages']['entries']}
    consumers = (CONSUMERS if forwarders else {k:v for k,v in CONSUMERS.items() if k not in FORWARDERS}
                 if wrappers else PRIMARY_CONSUMERS)
    calls = {call: target for target in consumers for call in direct_calls(original, target) if call-BASE < LIMIT}
    seeds = set()
    for call in calls:
        at = call-BASE
        entry = next((p for p in range(at, max(-1, at-6000), -2)
                      if struct.unpack_from('<H', original, p)[0] & 0xFF00 == 0xB500), at)
        seeds.add(entry)
    # Additional literal seeds recover consumers beyond computed branches.
    # They remain candidates until code/data and reachability are confirmed.
    for pc in range(0, LIMIT, 2):
        op = struct.unpack_from('<H', original, pc)[0]
        if op & 0xF800 == 0x4800:
            at = ((pc+4) & ~3) + (op & 255)*4
            value = struct.unpack_from('<I', original, at)[0]
            if 0x08140D68 <= value < 0x081417A0 or value in sources:
                seeds.add(pc)
                seeds.update(range(max(0, pc-16), pc, 2))
    rows, limits, stops = trace(original, compiled, seeds, calls)
    if expand:
        unresolved = set(calls)-{row['call'] for row in rows}
        local_seeds = {p for call in unresolved for p in range(max(0, call-BASE-64), call-BASE, 2)
                       if struct.unpack_from('<H', original, p)[0] & 0xF800 in (0x2000, 0x4800)}
        extra, extra_limits, extra_stops = trace(original, compiled, local_seeds, calls, budget=2000)
        keyed = {(r['call'],r['original_argument'],r['compiled_argument']):r for r in rows}
        for row in extra:
            key = row['call'],row['original_argument'],row['compiled_argument']
            keyed.setdefault(key, row | {'local_seed_followup': True})
        rows = list(keyed.values())
        limits += extra_limits
        stops = dict(Counter(stops)+Counter(extra_stops))
        seeds |= local_seeds
    aliases = {r['source_sha256']:r for r in inventory['entries']}
    for row in rows:
        old, pointer, target = row['original_argument'], row['compiled_argument'], row['consumer']
        src = sources.get(old)
        if src is None and BASE <= old < BASE+len(original):
            try:
                tokens, end = tokenize(original[old-BASE:old-BASE+512])
                raw = original[old-BASE:old-BASE+end]
                wording = readable(tokens)
                if re.search('[\u3040-\u30ff\u3400-\u9fff]', wording):
                    sha = digest(raw)
                    alias = aliases.get(sha)
                    src = dict(id=f'rom.{old-BASE:08x}', source_sha256=sha, raw_hex=raw.hex(),
                               japanese=wording, language_status=alias['language_status'] if alias else 'uncatalogued')
                    row['catalog_alias_id'] = alias['id'] if alias else None
                    row['outside_catalog_pointer'] = True
            except ValueError:
                pass
        row.update(consumer_name=CONSUMERS[target][0], source_id=src['id'] if src else None,
                   source_language_status=src['language_status'] if src else None,
                   japanese=src['japanese'] if src else None,
                   inserted_wording_elsewhere=translated_sources.get(src['source_sha256'], []) if src else [])
        if pointer in english:
            disposition = 'bound_english_resource'
            row['english'] = english[pointer]['english']
        elif target == 0x08015848 and pointer in players:
            disposition = 'mapped_at_player_wrapper'
        elif target in (0x08015848, 0x0801588C) and pointer in notices:
            disposition = 'mapped_at_queue'
        elif src and pointer == old:
            raw = bytes.fromhex(src['raw_hex'])
            if src['language_status'].startswith('retained-') or not any(c > 127 for c in raw):
                disposition = 'original_nonlinguistic_or_retained_needs_context'
            elif target == 0x08000FB8 and pointer in notices and b'%' not in raw:
                disposition = 'static_copy_requires_downstream_queue'
            elif target == 0x0805CF54:
                disposition = 'copied_japanese_requires_reader_followup'
            else:
                disposition = 'original_japanese_argument_needs_followup'
        else:
            disposition = 'unclassified_argument'
        row['disposition'] = disposition
    resolved = {r['call'] for r in rows}
    unresolved = [{'call': call, 'consumer': target, 'consumer_name': CONSUMERS[target][0]}
                  for call, target in sorted(calls.items()) if call not in resolved]
    report = {'rom_sha256': digest(compiled), 'source_sha256': digest(original),
              'tool_sha256': digest(Path(__file__).read_bytes()),
              'scan_range': [BASE, BASE+LIMIT], 'direct_call_patterns': len(calls),
              'expanded_local_seeds': expand,
              'include_modal_wrappers_and_string_copy': wrappers,
              'include_disassembled_forwarders': forwarders,
              'direct_patterns_outside_scan': {hex(t): [c for c in direct_calls(original, t) if c-BASE >= LIMIT]
                                              for t in consumers},
              'consumer_counts': dict(Counter(CONSUMERS[t][0] for t in calls.values())),
              'seeds': len(seeds), 'candidate_routes': sorted(rows, key=lambda r: (r['call'], r['original_argument'])),
              'disposition_counts': dict(Counter(r['disposition'] for r in rows)),
              'unresolved_calls': unresolved, 'budget_limits': limits, 'stop_reasons': stops,
              'scope': f'Bounded Thumb constant-flow candidates to {len(consumers)} selected consumers. Includes already-reviewed sources '
                       'and every matching direct call, even unresolved arguments. Conditional paths and nearest '
                       'PUSH seeds are provisional; literals may be data. Patched instructions, computed tables, '
                       'RAM strings, wrappers, indirect calls, other readers and code outside the scan remain '
                       'explicit gaps. Bound English arguments establish routing only, not native fit or gameplay.'}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
    print('Direct caller patterns:', len(calls), 'resolved candidates:', len(resolved), 'unresolved:', len(unresolved))
    print('Candidate dispositions:', report['disposition_counts'])
    print('Budget-limited seeds:', len(limits))
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=ROOT/'build/english')
    parser.add_argument('--output', type=Path, default=ROOT/'build/caller-audit/static.json')
    parser.add_argument('--expand-local-seeds', action='store_true')
    parser.add_argument('--include-wrappers', action='store_true')
    parser.add_argument('--include-forwarders', action='store_true')
    args = parser.parse_args()
    run(args.source, args.output, args.expand_local_seeds, args.include_wrappers,args.include_forwarders)
