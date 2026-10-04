"""Locate lost table bases and bind the investigated sites to owned consumers.

This observes conservative trace cutoffs; it does not infer runtime selectors or
classify unreferenced catalog strings as unused.
"""
import json
from pathlib import Path

from tools.audit_text_callers import BASE, trace
from tools.lz77 import decompress
from tools.rom import ROOT, digest, load_base, require
from tools.thumb_switches import switches
from tools.town_text import RAM, relocate, resource

FAMILIES = {
    'wind': [0x51EA], 'status_expiry': [0x96DC], 'hunger': [0x90FE],
    'shield_reflection': [0xCECA], 'save_preview': [0x14A58],
    'english-name-entry': [0x155C0, 0x155E6, 0x18402, 0x18424],
    'floor_notices': [0x1714A],
    'results': [0x19E1E, 0x1CB48, 0x1CBD6, 0x1CC22, 0x1CC80,
                0x56FA4, 0x5701C, 0x5704E, 0x570C0],
    'dungeon-ui': [0x1A9A8], 'companion': [0x1AB28],
    'remaining_callers': [0x1CCF8, 0x570E8], 'remi': [0x1EF62, 0x1F1BA],
    'skill_menu': [0x2121E, 0x2156A], 'skill_info': [0x21772, 0x21784],
    'spell_menu': [0x225AC], 'spell_info': [0x2285E], 'soldiers': [0x24356],
    'pickup': [0x24B70], 'monster_announcements': [0x2A9DC, 0x2ABCE],
    'dungeon_leaves': [0x350CC, 0x353C8],
}
SPECIAL = {
    0x148C0: ('save-row-loop', 'tools.audit_save_menu_rows resolves both selectors and all four English rows'),
    0x2B8F8: ('equipped-curse-queue', 'tools.audit_dynamic_text_selectors checks the three native selectors and exact queue adapter'),
    0x53DF2: ('sprite-coordinate', 'Disassembly uses sprite coordinates, not a text pointer; numeric RAM-range coincidence'),
    0x55ECC: ('sprite-coordinate', 'Disassembly uses sprite coordinates, not a text pointer; numeric RAM-range coincidence'),
}


def run():
    original = load_base()
    compiled = (ROOT/'build/english/torneko-2-english.gba').read_bytes()
    build = json.loads((ROOT/'build/english/build.json').read_text())
    require(digest(compiled) == build['output_sha256'], 'Stale compiled ROM')
    input_path = ROOT/'build/caller-branches/source-readers-final.json'
    audit = json.loads(input_path.read_text())
    old = relocate(resource()['data'])
    new = relocate(decompress(compiled, build['dialogue']['town_resource']['rom_offset'])[0])
    losses = {}
    def observe(pc, opcode, x, y, seed):
        value = x or y
        if not (0x08140D68 <= value[0] < 0x081417A0 or RAM <= value[0] < RAM+1200):
            return
        row = losses.setdefault((pc,value), dict(address=pc, opcode=opcode,
            known_value=value, known_operand='left' if x else 'right', seeds=[]))
        if seed not in row['seeds']:
            row['seeds'].append(seed)
    seeds = {x['load']-BASE for x in audit['literal_candidates']}
    _, limits, stops = trace(original, compiled, seeds, {}, budget=5000,
        max_path_length=900, stack_model=True, paired_stack_adjustments=True,
        memory_images=((RAM,(old,new)),), switch_domains=switches(original,compiled,0x5E000),
        unknown_operand_observer=observe)
    families = {pc:name for name,pcs in FAMILIES.items() for pc in pcs}
    require({pc-BASE for pc,_ in losses} == set(families) | set(SPECIAL),
            'New or missing computed reader needs investigation')
    for (pc,_), row in losses.items():
        offset = pc-BASE
        row.update(original_context=original[offset-12:offset+16].hex(),
                   compiled_context=compiled[offset-12:offset+16].hex())
        if offset in SPECIAL:
            row['family'],row['disposition'] = SPECIAL[offset]
        else:
            pointer = row['known_value'][1]-BASE
            owned = [a for a in build['allocations'] if a['start'] <= pointer < a['end_exclusive']]
            require(len(owned) == 1, 'Computed table base lacks unique allocation ownership')
            row.update(family=families[offset], disposition='Existing relocated consumer; selector remains unknown in this trace',
                       compiled_allocation=owned[0])
    report = dict(rom_sha256=digest(compiled), source_sha256=digest(original),
        generator_sha256=digest(Path(__file__).read_bytes()),
        input_report_sha256=digest(input_path.read_bytes()), literal_seeds=sorted(seeds),
        losses=list(losses.values()), limits=limits, stops=stops, scope=__doc__)
    output = ROOT/'build/caller-continuation/computed-table-losses.json'
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(report,indent=2)+'\n')
    print('Computed table losses:',len(losses),'classified sites;',len(limits),'retained budget limits')


if __name__ == '__main__':
    run()
