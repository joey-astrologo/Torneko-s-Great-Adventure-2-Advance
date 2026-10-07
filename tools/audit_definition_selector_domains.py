"""Trace complete spell/skill definition domains through computed text loads.

Record-level static coverage is separate from native gameplay and from other
callers of the unresolved catalog sources.
"""
import json
from pathlib import Path
import struct

from tools.audit_source_readers import inserted_resources
from tools.audit_text_callers import trace
from tools.extract_shared_text import START, END
from tools.extract_skills import extract as skills
from tools.extract_spells import extract as spells
from tools.rom import ROOT, digest, load_base, require


def run():
    original = load_base()
    directory = ROOT/'build/english'
    compiled = (directory/'torneko-2-english.gba').read_bytes()
    build = json.loads((directory/'build.json').read_text())
    require(digest(compiled) == build['output_sha256'], 'Definition audit ROM differs')
    english = {0x08000000+r['offset']: r for r in inserted_resources(build)}
    inventory = json.loads((ROOT/'build/text-inventory/catalog.json').read_text())
    unresolved = {0x08000000+int(r['id'][4:], 16): r['id'] for r in inventory['entries']
                  if r['id'].startswith('rom.') and r['language_status'] == 'untranslated'}
    results = []

    def check(case, seed, registers, expected_sites, memory=(), expected_indexes=None):
        reads = {}
        later_visits = []
        def observe(pc, addresses, size, values, origin):
            if pc not in expected_sites:
                return
            # This seed supplies one definition. Later menu-loop visits can
            # select a different record; never overwrite the seeded observation.
            if pc in reads:
                later_visits.append(pc)
                return
            require(size == 4 and 0x08000000+START <= addresses[0] < 0x08000000+END,
                    'Computed source left shared table')
            require(values[1] in english and values[0] not in unresolved,
                    'Computed definition selected an unresolved/untranslated source')
            row = english[values[1]]
            index = (addresses[0]-0x08000000-START)//4
            if expected_indexes is not None:
                require(index == expected_indexes[pc],
                        'Seeded definition selected another record: '+case)
            raw = bytes.fromhex(row['encoded_hex'])
            at = values[1]-0x08000000
            require(compiled[at:at+len(raw)] == raw, 'English selector bytes differ')
            reads[pc] = dict(pc=pc, original_slot=index,
                             original_pointer=values[0], compiled_pointer=values[1], id=row['id'])
        _, limits, stops = trace(original, compiled, [seed], {}, budget=300,
            max_path_length=110, stack_model=True, initial_registers={seed: registers},
            memory_images=memory, read_observer=observe)
        require(set(reads) == set(expected_sites), 'Definition trace missed a selected read')
        results.append(dict(case=case, seed=seed, initial_registers=registers,
                            reads=list(reads.values()), downstream_limits=limits,
                            downstream_stops=stops, later_visits=later_visits))

    info = {r['id']: r for r in build['spell_info']['copies']}
    for definition in spells()['entries']:
        ident = definition['id']
        old = 0x08000000+definition['record_offset']
        for family, seed, target, table, sites in (
                ('spell-menu', 0x225A2, build['spell_menu']['definition_copy_offset'],
                 build['spell_menu']['table_offset'], [0x080225AE]),
                ('spell-info', 0x22850, info['definitions']['offset'],
                 info['ui']['offset'], [0x08022860])):
            new = 0x08000000+target+12*ident
            require(original[old-0x08000000+6] == compiled[new-0x08000000+6],
                    'Native spell target selector changed')
            check(f'{family}-{ident}', seed,
                  {0: (old, new), 5: (0x08000000+START, 0x08000000+table)}, sites,
                  expected_indexes={pc:0x22F+definition['target_kind'] for pc in sites})

    lookup = struct.unpack_from('<I', original, 0x21848)[0]-0x08000000
    require(compiled[lookup:lookup+8] == original[lookup:lookup+8], 'Skill kind lookup changed')
    lookup_image = ((0x10000144, (original[lookup:lookup+8], compiled[lookup:lookup+8])),)
    for definition in skills()['entries']:
        ident = definition['id']
        check(f'skill-info-{ident}', 0x21756,
              {9: (ident, ident), 5: (0x10000144, 0x10000144)},
              [0x08021774, 0x08021786], lookup_image)

    # In the staff effect, D4h is an increment, not the final table selector.
    # Both native arms are disassembled in buffer-functions.txt; the upgrade
    # sibling similarly selects 50h/12Ch, never an unconstrained r8 argument.
    effects = []
    for lo, hi in ((0x35098, 0x350A8), (0x353A0, 0x353B8)):
        require(original[lo:hi] == compiled[lo:hi], 'Reinspect effect selector construction')
    for site, literal, indexes in ((0x350CC, 0x3510C, [0x50, 0x12C]),
                                    (0x353C8, 0x353D8, [0x59, 0x12D])):
        old_table = struct.unpack_from('<I', original, literal)[0]
        new_table = struct.unpack_from('<I', compiled, literal)[0]
        require(old_table == 0x08000000+START, 'Effect source table differs')
        for index in indexes:
            old = struct.unpack_from('<I', original, START+4*index)[0]
            new = struct.unpack_from('<I', compiled, new_table-0x08000000+4*index)[0]
            require(old not in unresolved and new in english, 'Effect selector lacks English')
            effects.append(dict(site=site, index=index, id=english[new]['id']))
    report = dict(passed=True, rom_sha256=digest(compiled), source_sha256=digest(original),
        tool_sha256=digest(Path(__file__).read_bytes()), cases=results, effects=effects,
        shared_unresolved_sources=len(unresolved), scope=__doc__+
        '\nAll 61 spell records in both computed consumers and all 128 skill records in '
        'both Info loads are checked. Skill lookup RAM is the exact native eight-byte ROM copy. '
        'Stops after the selected reads remain explicit; this is not full execution of those '
        'functions or evidence that unrelated unresolved sources have no callers.')
    output = ROOT/'build/oct04-continuation/definition-selector-domains.json'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2)+'\n')
    print('Definition selector domains:', len(results), 'record cases;',
          sum(len(r['reads']) for r in results), 'computed reads;', len(effects), 'effect bindings')
    return report


if __name__ == '__main__':
    run()
