"""Bound tutorial entry evidence without declaring unreferenced records dead.

Scan every byte of the seven recovered event instruction regions and complete
NPC payloads, independently of root traversal. Matches are candidates, not proof
of instruction alignment. Retain malformed configurations and unknown entry paths.
"""
import argparse
import json
from pathlib import Path
import struct

from tools.audit_reader_routes import BASE, direct_calls
from tools.lz77 import decompress
from tools.rom import ROOT, digest, load_base, require


def candidates(data, start=0, end=None):
    end = len(data) if end is None else end
    require(0 <= start <= end <= len(data), 'Invalid script scan region')
    return [dict(offset=i, configuration=data[i+5], raw_hex=data[i:i+6].hex())
            for i in range(start, end-5) if data[i] == 8 and data[i+4] == 2]


def run(source, output):
    original = load_base()
    compiled = (source/'torneko-2-english.gba').read_bytes()
    build = json.loads((source/'build.json').read_text())
    require(digest(compiled) == build['output_sha256'], 'Tutorial audit ROM differs')
    scripts_path = ROOT/'build/event-script-audit/script-text-refs.json'
    scripts = json.loads(scripts_path.read_text())
    require(scripts['source_rom_sha256'] == digest(original), 'Script roots use another ROM')
    regions = []
    for bank in scripts['banks']:
        for script in bank['scripts']:
            lo, hi = script['start']+4, script['end_exclusive']
            require(original[lo:hi] == compiled[lo:hi], 'Event instructions changed')
            matches = candidates(original, lo, hi)
            for match in matches:
                instruction = next((row for row in script['instructions']
                    if row['address'] <= match['offset'] < row['address']+len(bytes.fromhex(row['hex']))), None)
                require(instruction is not None, 'Byte candidate needs undecoded event analysis')
                match['at_decoded_instruction_start'] = instruction['address'] == match['offset']
                match['containing_instruction'] = instruction
            regions.append(dict(kind='event-instructions', bank=bank['bank'],
                root=script['index'], address_space='ROM file', range=[lo, hi],
                sha256=digest(original[lo:hi]), candidates=matches))
    for bank in range(7):
        slot = 0x14CD68+4*bank
        old_at = struct.unpack_from('<I', original, slot)[0]-BASE
        new_at = struct.unpack_from('<I', compiled, slot)[0]-BASE
        data, end = decompress(original, old_at)
        new, _ = decompress(compiled, new_at)
        require(new == data, 'NPC script payload changed')
        header = struct.unpack_from('<5I', data)
        matches = candidates(data)
        for match in matches:
            match['within_instruction_region'] = header[3] <= match['offset'] < header[4]-5
        regions.append(dict(kind='complete-NPC-payload', bank=bank,
            address_space='decoded NPC bank', range=[0, len(data)],
            instruction_range=list(header[3:5]), source_rom_range=[old_at, end],
            sha256=digest(data), candidates=matches))

    selected = {c['configuration'] for region in regions for c in region['candidates']
                if c.get('at_decoded_instruction_start', True) and c.get('within_instruction_region', True)}
    groups = build['tutorial_help']['groups']
    require(len(groups) == 27 and all(i < 27 for i in selected), 'Unexpected tutorial configuration')
    # Ghidra: 50FB8 uses base + page, where the page counter is clamped to 0..1.
    # The only script-selected mode-2 configuration is 18; its second page is 19.
    paged = {g['index'] for g in groups if g['index'] in selected and g['mode'] == 2}
    require(paged == {18}, 'Reinspect paged tutorial dispatch')
    require(original[0x51118:0x5111E] == bytes.fromhex('012c07dd0122') and
            original[0x51146:0x51150] == bytes.fromhex('0138002802da00208246'),
            'Tutorial page bounds differ from disassembly')
    paged_second = {i+1 for i in paged}
    calls = {}
    for target, expected in ((0x0804F8F4, []),
                             (0x08050DD0, [0x0804F9EA, 0x0804FA14]),
                             (0x08050FB8, [0x0804FA26])):
        old = direct_calls(original[:0x5E000], target)
        new = direct_calls(compiled[:0x5E000], target)
        require(old == new == expected, 'Reinspect tutorial direct calls')
        calls[f'{target:08X}'] = old
    handler_word = struct.pack('<I', 0x0804F8F5)
    occurrences = [i for i in range(len(original)-3) if original[i:i+4] == handler_word]
    require(occurrences == [0x14CE4C], 'Reinspect tutorial handler pointer owners')
    require(original[0x14CE4C:0x14CE50] == compiled[0x14CE4C:0x14CE50],
            'NPC opcode 8 handler changed')

    retained = []
    catalog = json.loads((ROOT/'translations/tutorial-help-review.json').read_text())
    for index in sorted(set(range(27))-selected-paged_second):
        group = catalog['groups'][index]
        pointers = [struct.unpack_from('<I', original, group['intro_offset']+4*(pos+1))[0]
                    for pos in range(group['descriptor'][7]-1)]
        retained.append(dict(configuration=index, mode=group['mode'],
            descriptor=group['descriptor'], intro_pointers=pointers,
            selector_bytes=[original[p-BASE:p-BASE+4].hex() for p in pointers],
            cancel_label=group['labels'][-1]['japanese'],
            disposition='No instruction-aligned event reference or complete NPC payload candidate; '
                        'no entry via the sole known paged caller. Original mapping retained; '
                        'arithmetic/unknown entry paths are not disproven.',
            mapping_limit=('Direct-prose mode points at two-byte event selectors.' if group['mode']==0
                           else 'Bank-dependent selectors; label list crosses the two-row prefix and '
                                'does not end with the native Cancel label.')))
    report = dict(passed=True, source_rom_sha256=digest(original),
        rom_sha256=digest(compiled), tool_sha256=digest(Path(__file__).read_bytes()),
        script_roots_sha256=digest(scripts_path.read_bytes()), regions=regions,
        candidate_configurations=sorted(selected), paged_second_configurations=sorted(paged_second),
        direct_calls=calls, handler_pointer_offsets=occurrences,
        retained_configurations=retained,
        scope=__doc__+'\nNo new ROM text, native gameplay evidence or global unreachability claim.')
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2)+'\n')
    print('Tutorial entry audit:', len(regions), 'regions;', len(selected),
          'script candidates; second pages', sorted(paged_second),
          '; retained without entry', [r['configuration'] for r in retained])
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=ROOT/'build/english')
    parser.add_argument('--output', type=Path,
                        default=ROOT/'build/caller-branches/tutorial-reachability.json')
    args = parser.parse_args()
    run(args.source, args.output)
