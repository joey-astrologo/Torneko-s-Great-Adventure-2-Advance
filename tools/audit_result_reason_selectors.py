"""Follow the disassembled direct-call graph supplying result reason codes.

This closes the listed producer graph, not arbitrary RAM writes or indirect
arithmetic calls. It does not label the legacy ranking source globally unused.
"""
import json
from pathlib import Path
import struct

from tools.audit_reader_routes import direct_calls
from tools.rom import ROOT, digest, load_base, require

# Function -> {direct call site: constants, or supplying parent's entry}.
# Original disassembly retained under build/oct04-continuation/reason-*.txt.
# Forwarded arguments: 11DA4/36CC8 r1; 12BAC/13714/12F3C r3;
# 36CAC/37978 r0; 37694 r2; 37998/37A70/37B30 r1.
GRAPH = {
    0x6644: {0x4D18: [4], 0x5276: [34], 0x59B0: [33], 0x6A72: [33],
             0x97FA: [1, 2, 3, 24], 0xCB1A: [21], 0x11ACC: [5],
             0x11E7C: 0x11DA4, 0x1AA60: [36], 0x1BA66: [33],
             0x36D72: 0x36CC8, 0x4114A: [25]},
    0x11DA4: {0x12D52: 0x12BAC, 0x13ADA: 0x13714, 0x13B36: 0x13714,
              0x13B7A: 0x13714, 0x26F04: [9], 0x277C6: [22],
              0x27964: [10], 0x2D49C: [21], 0x2D4CA: [21], 0x372F8: [13],
              0x376AC: 0x37694, 0x3798A: 0x37978, 0x379BA: 0x37998,
              0x379F0: 0x37998, 0x37A9C: 0x37A70, 0x39AD0: [16], 0x39B3A: [20]},
    0x36CC8: {0x32C76: [32], 0x36CBA: 0x36CAC},
    0x12BAC: {0x12F02: [7], 0x12F5A: 0x12F3C},
    0x13714: {0x2862E: [12], 0x37B60: 0x37B30, 0x3A042: [18]},
    0x36CAC: {0x1B292: [35], 0x3D6B6: [32], 0x40F3A: [32]},
    0x37694: {0x373DC: [14], 0x37588: [26], 0x37CDC: [27]},
    0x37978: {0x37422: [15], 0x37D1C: [27]},
    0x37998: {0x3742C: [16], 0x37D26: [27]},
    0x37A70: {0x3743E: [17], 0x37D38: [27]},
    0x12F3C: {0x9326: [6], 0xCF40: [7], 0xD7F2: [7], 0x14128: [8],
              0x248F4: [6], 0x284F4: [11], 0x38CE4: [19], 0x39F7E: [19]},
    0x37B30: {0x374C2: [18], 0x37D5A: [27]},
}


def run():
    original = load_base()
    source = ROOT/'build/english'
    compiled = (source/'torneko-2-english.gba').read_bytes()
    ledger = json.loads((source/'build.json').read_text())
    require(digest(compiled) == ledger['output_sha256'], 'Result audit ROM differs')
    rows = []
    def values(entry):
        return set().union(*(set(v) if isinstance(v, list) else values(v)
                             for v in GRAPH[entry].values()))
    for entry, calls in GRAPH.items():
        expected = sorted(0x08000000+c for c in calls)
        require(direct_calls(original[:0x5E000], 0x08000000+entry) == expected,
                'Reinspect result producer callers')
        require(direct_calls(compiled[:0x5E000], 0x08000000+entry) == expected,
                'Compiled result producer callers changed')
        require(all(original[c-20:c+4] == compiled[c-20:c+4] for c in calls),
                'Reinspect compiled result argument setup')
        needle = struct.pack('<I', 0x08000001+entry)
        occurrences, cursor = [], 0
        while (cursor := original.find(needle, cursor)) >= 0:
            occurrences.append(cursor)
            cursor += 1
        require(not occurrences, 'Result producer has an uninvestigated function-pointer reference')
        rows.append(dict(entry=entry, values=sorted(values(entry)),
            calls=[dict(call=c, constants=v if isinstance(v, list) else None,
                        forwarded_from=v if isinstance(v, int) else None,
                        original_context=original[c-20:c+4].hex(),
                        compiled_context=compiled[c-20:c+4].hex()) for c, v in calls.items()],
            function_pointer_occurrences=occurrences))
    reasons = values(0x6644)
    require(not reasons & {28, 29, 30, 31}, 'Legacy result-source selector needs investigation')
    # Both rendering paths select 196h + reason only for reasons <= 31;
    # reason 21 has its own monster-name path. 32+ uses completion paths.
    causes = {r['reason'] for r in ledger['results']['causes']}
    require({r for r in reasons if r < 32 and r != 21} <= causes,
            'Producer selects an untranslated defeat cause')
    source_at = struct.unpack_from('<I', original, 0x140D68+4*(0x196+30))[0]
    require(source_at == 0x080615A4, 'Legacy rank/score source moved')
    report = dict(passed=True, rom_sha256=digest(compiled), source_sha256=digest(original),
        tool_sha256=digest(Path(__file__).read_bytes()), functions=rows,
        result_reason_values=sorted(reasons), excluded_renderer_reasons=[28,29,30,31],
        legacy_rank_source=dict(id='rom.000615a4', shared_index=0x1B4, required_reason=30,
            disposition='Not supplied by the investigated direct setter/forwarder graph; '
                        'source remains unresolved for other readers.'),
        scope=__doc__+'\nArgument domains come from reviewed disassembly, not a whole-program proof. '
              'The report pins every direct call and source context, and rejects function-pointer '
              'references. Saved/corrupt values, synthesized indirect calls and other RAM producers '
              'remain outside this bound. No artificial reason-30 display is counted as gameplay.')
    output = ROOT/'build/oct04-continuation/result-reason-selectors.json'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2)+'\n')
    print('Result reasons:', len(rows), 'producer functions;', sum(len(v) for v in GRAPH.values()),
          'direct calls; reasons', sorted(reasons))
    return report


if __name__ == '__main__':
    run()
