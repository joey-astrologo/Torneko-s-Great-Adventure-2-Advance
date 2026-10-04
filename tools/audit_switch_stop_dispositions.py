"""Classify recorded switch-scan stops using exact original/compiled bytes.

These dispositions explain bounded scan exits, not whole-function branch
coverage. No missing reference is classified as globally unreachable text.
"""
import argparse
import json
from pathlib import Path
import struct

from tools.rom import ROOT, digest, load_base, require


def run(source, evidence, output):
    original = load_base()
    compiled = (source/'torneko-2-english.gba').read_bytes()
    build = json.loads((source/'build.json').read_text())
    require(digest(compiled) == build['output_sha256'], 'Stop disposition ROM differs')
    reports = []
    for name in ('all-switch-stop-details.json','save-switch-stop-details.json','save-menu-rows.json'):
        path=evidence/name
        report=json.loads(path.read_text())
        require(report['rom_sha256'] == digest(compiled), 'Stop evidence ROM differs')
        reports.append(report)
    require(len(reports[0]['switches']) == 25 and len(reports[0]['seeds']) == 25,
            'Switch guard cohort differs')
    require({row['seed'] for row in reports[0]['limits']} == {0x080147F8}
            and reports[1]['seeds'] == [0x080147F8] and not reports[1]['limits'],
            'Budget stop lacks its expanded scan')
    require(reports[2]['passed'] and [c['slots'] for c in reports[2]['cases']] == [[363],[364,365,366]],
            'Save-row consumer evidence incomplete')
    rows = {}
    for report in reports[:2]:
        for stop in report['stop_details']:
            pc=stop['address']-0x08000000
            key=(stop['reason'],pc)
            if key in rows:
                rows[key]['observations'] += 1
                continue
            disposition=None
            if stop['reason'] == 'indirect_branch_or_return':
                previous,branch=struct.unpack_from('<HH',original,pc-2)
                register=(branch>>3)&15
                require(branch & 0xFF87 == 0x4700 and register < 8
                        and previous == 0xBC00 | (1<<register)
                        and original[pc-2:pc+2] == compiled[pc-2:pc+2],
                        'Indirect exit is not the expected POP/BX epilogue')
                disposition='Native POP/BX epilogue; saved return address, not an unresolved text dispatch.'
            elif stop['reason'] == 'patched_instruction':
                require(pc == 0x14BE6, 'Unclassified patched instruction')
                owner=next(p for p in build['patches'] if p['start'] == pc)
                require(owner['owner'] == 'english-name-entry'
                        and owner['before_hex'] == '0622' and owner['after_hex'] == '0722'
                        and original[pc:pc+2].hex() == owner['before_hex']
                        and compiled[pc:pc+2].hex() == owner['after_hex'],
                        'Name-limit patch ownership differs')
                disposition='Owned six-to-seven character editor-limit patch; existing native name-entry family covers it.'
            elif stop['reason'] == 'path_length_limit':
                require(0x148B0 <= pc < 0x148EA and
                        any(r['address'] == 0x080148B0 and r['visits'] > 100
                            for r in stop['repeated_addresses']), 'Unclassified path-length stop')
                disposition='Unknown menu-row count caused repeated traversal; separate selectors 0/1 resolve all four row bindings.'
            require(disposition is not None, 'Unclassified stop: '+stop['reason'])
            rows[key]=dict(reason=stop['reason'],address=stop['address'],
                source_range=[max(0,pc-2),pc+4],source_hex=original[max(0,pc-2):pc+4].hex(),
                compiled_hex=compiled[max(0,pc-2):pc+4].hex(),
                observations=1,disposition=disposition)
    result=dict(passed=True,rom_sha256=digest(compiled),source_sha256=digest(original),
        tool_sha256=digest(Path(__file__).read_bytes()),
        evidence_sha256={name:digest((evidence/name).read_bytes()) for name in
            ('all-switch-stop-details.json','save-switch-stop-details.json','save-menu-rows.json')},
        dispositions=list(rows.values()),
        limits='The additional stops from the narrowly seeded save-row follow-up remain in its report. '
               'Only the 25-guard scan and expanded save-menu seed are classified here. '
               'Unknown initial arguments, unvisited paths and the 62 unresolved sources are not closed.',
        scope=__doc__)
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(result,indent=2)+'\n')
    print('Switch stop dispositions:',len(rows),'distinct exits;',
          sum(r['reason']=='indirect_branch_or_return' for r in rows.values()),'POP/BX returns; no new ROM patch')
    return result


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,default=ROOT/'build/english')
    parser.add_argument('--evidence',type=Path,default=ROOT/'build/caller-branches')
    parser.add_argument('--output',type=Path,default=ROOT/'build/caller-branches/switch-stop-dispositions.json')
    args=parser.parse_args()
    run(args.source,args.evidence,args.output)
