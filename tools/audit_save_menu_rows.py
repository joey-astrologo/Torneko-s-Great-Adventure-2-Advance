"""Resolve the bounded initial/save menu row loop from both native selectors.

This seeds the original row builder after its two disassembled selector stores.
It is static consumer evidence, not a claim to execute every save-state branch.
"""
import argparse
import json
from pathlib import Path
import struct

from tools.audit_text_callers import BASE, trace
from tools.rom import ROOT, digest, load_base, require


def run(source, output):
    original = load_base()
    compiled = (source/'torneko-2-english.gba').read_bytes()
    build = json.loads((source/'build.json').read_text())
    require(digest(compiled) == build['output_sha256'], 'Save menu ROM differs')
    # 14848: mov r1,0; str r1,[sp,138]. 14864: mov r3,1; str r3,[sp,138].
    require(original[0x14848:0x1484C] == compiled[0x14848:0x1484C] == bytes.fromhex('00214e91')
            and original[0x14864:0x14868] == compiled[0x14864:0x14868] == bytes.fromhex('01234e93'),
            'Reinspect native menu selector stores')
    require(original[0x1486E:0x148F2] == compiled[0x1486E:0x148F2], 'Row loop code changed')
    descriptor = struct.unpack_from('<I', original, 0x148F8)[0]-BASE
    require(descriptor == 0x147DD4 and original[descriptor:descriptor+16] == compiled[descriptor:descriptor+16],
            'Row descriptors changed')
    tables = [struct.unpack_from('<I', image, 0x148FC)[0] for image in (original, compiled)]
    cases = []
    for selector, count in ((0,1),(1,3)):
        raw = original[descriptor+8*selector:descriptor+8*selector+8]
        record = struct.unpack('<4h', raw)
        require(record[0] == count, 'Menu row count differs')
        slots = list(record[1:count+1])
        details = []
        rows, limits, stops = trace(original, compiled, {0x1486E},
            {BASE+0x148CA: BASE+0x2298}, budget=12000, max_path_length=900,
            stack_model=True, initial_registers={0x1486E:{1000+0x138:(selector,selector)}},
            stop_observer=details.append)
        expected = [(struct.unpack_from('<I', original,tables[0]-BASE+4*slot)[0],
                     struct.unpack_from('<I', compiled,tables[1]-BASE+4*slot)[0]) for slot in slots]
        actual = [(r['original_argument'],r['compiled_argument']) for r in rows]
        require(set(actual) == set(expected) and len(actual) == count,
                'Row-loop text bindings incomplete or unexpected')
        require(all(old != new and new >= BASE+len(original) for old,new in actual),
                'Save menu row did not use its private English resource')
        cases.append(dict(selector=selector,descriptor_hex=raw.hex(),slots=slots,
            bindings=rows, downstream_limits=limits, downstream_stops=stops,stop_details=details))
    report = dict(passed=True,rom_sha256=digest(compiled),source_sha256=digest(original),
        tool_sha256=digest(Path(__file__).read_bytes()),
        tracer_sha256=digest((ROOT/'tools/audit_text_callers.py').read_bytes()),
        descriptor_range=[descriptor,descriptor+16],table_pointers=tables,cases=cases,
        scope=__doc__+'\nDownstream stops remain recorded; no text or ROM patches added.')
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(report,indent=2)+'\n')
    print('Save menu rows: both selectors / four English bindings verified')
    return report


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,default=ROOT/'build/english')
    parser.add_argument('--output',type=Path,default=ROOT/'build/caller-branches/save-menu-rows.json')
    args=parser.parse_args()
    run(args.source,args.output)
