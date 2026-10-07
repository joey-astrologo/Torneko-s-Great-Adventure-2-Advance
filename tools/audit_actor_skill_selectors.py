"""Bound soldier producers, both monster announcement readers and skill labels.

These are paired static traces of the selected instructions and record domains.
They do not establish ordinary encounters, arbitrary RAM writers or global
unreachability of the unresolved source catalog.
"""
import json
from pathlib import Path
import struct

from tools.audit_reader_routes import BASE, direct_calls
from tools.audit_source_readers import inserted_resources
from tools.audit_text_callers import trace
from tools.extract_monsters import COUNT, DEFINITIONS, LINK_BASE, RAM, RESOURCE
from tools.extract_shared_text import START, END
from tools.extract_skills import extract as skills
from tools.lz77 import decompress
from tools.rom import ROOT, digest, load_base, require


def run():
    original = load_base()
    directory = ROOT/'build/english'
    compiled = (directory/'torneko-2-english.gba').read_bytes()
    build = json.loads((directory/'build.json').read_text())
    require(digest(compiled) == build['output_sha256'], 'Selector audit ROM differs')
    english = {BASE+r['offset']: r for r in inserted_resources(build)}
    inventory = json.loads((ROOT/'build/text-inventory/catalog.json').read_text())
    unresolved = {BASE+int(r['id'][4:], 16) for r in inventory['entries']
                  if r['id'].startswith('rom.') and r['language_status'] == 'untranslated'}
    cases, guards = [], []

    def unchanged(lo, hi):
        require(original[lo:hi] == compiled[lo:hi], 'Reinspect selector code '+hex(lo))
        guards.append(dict(start=BASE+lo, end_exclusive=BASE+hi,
                           raw_hex=original[lo:hi].hex()))

    def check(name, seed, registers, site, indexes, memory=(), record_site=None):
        reads, records = [], []
        def observe(pc, addresses, size, values, origin):
            if pc == record_site:
                records.append(dict(pc=pc, addresses=addresses, size=size, values=values))
            if pc != site:
                return
            require(size == 4 and BASE+START <= addresses[0] < BASE+END,
                    'Computed selector left shared source table')
            index = (addresses[0]-BASE-START)//4
            require(index in indexes and values[0] not in unresolved and values[1] in english,
                    'Computed selector lacks reviewed English: '+name)
            row = english[values[1]]
            raw = bytes.fromhex(row['encoded_hex'])
            require(compiled[values[1]-BASE:values[1]-BASE+len(raw)] == raw,
                    'Selected English bytes differ')
            reads.append(dict(pc=pc, index=index, source_pointer=values[0],
                              compiled_pointer=values[1], id=row['id']))
        _, limits, stops = trace(original, compiled, [seed], {}, budget=160,
            max_path_length=65, stack_model=True, initial_registers={seed: registers},
            memory_images=memory, read_observer=observe)
        require({r['index'] for r in reads} == set(indexes), 'Missing computed read: '+name)
        require(record_site is None or records, 'Missing definition load: '+name)
        cases.append(dict(case=name, seed=BASE+seed, initial_registers=registers,
            reads=reads, record_reads=records, downstream_limits=limits, downstream_stops=stops))

    # The creation function has only these direct calls. Species 57h produces
    # type 1 / selector 0; species 89h produces type 2 / random(7). The native
    # random source returns the unsigned upper 16 bits; 5CAF8 is signed remainder,
    # with nonnegative dividend and divisor 7 here, hence the exact domain 0..6.
    for rom in (original, compiled):
        require(direct_calls(rom[:0x5E000], BASE+0x31CD4) ==
                [BASE+0x28BE2, BASE+0x28C2E], 'Object creation call domain changed')
        require(struct.pack('<I', BASE+0x31CD5) not in rom,
                'Object creator has a function-pointer reference to inspect')
    for lo, hi in ((0x28B9E, 0x28C34), (0x31CB8, 0x31E0A),
                   (0x421EC, 0x42220), (0x5CAF8, 0x5CBC6),
                   (0x24346, 0x2435A), (0x210EE, 0x21122),
                   (0x2113C, 0x2116C), (0x21170, 0x211EC),
                   (0x21214, 0x21228), (0x21534, 0x21556),
                   (0x21560, 0x21588), (0x2A9BC, 0x2A9F8),
                   (0x2ABB6, 0x2ABEE)):
        unchanged(lo, hi)
    require(struct.unpack_from('<I', original, 0x31DC8)[0] == 0x0200D048 and
            original[0x28C0C:0x28C0E] == bytes.fromhex('0720') and
            original[0x28C2A:0x28C2E] == bytes.fromhex('00930223'),
            'Soldier type/random bound differs')
    for selector in range(7):
        record = bytearray(68)
        struct.pack_into('<I', record, 0, 2)
        record[0x40] = selector
        check('soldier-'+str(selector), 0x24346, {2: (0x0200D048,)*2},
              BASE+0x24358, [0x200+selector],
              ((0x0200D048, (record, record)),), BASE+0x2434C)

    # Check complete records through both readers, including zero-selector
    # suppression. The second reader's 141 cases deliberately overapproximate
    # normal projectile eligibility, so they are not 141 native encounters.
    old_data = bytearray(decompress(original, RESOURCE)[0])
    new_data = bytearray(decompress(compiled, build['monsters']['replacement_resource'])[0])
    require(len(old_data) == len(new_data) == 64668, 'Dungeon resource size differs')
    require(all(old_data[DEFINITIONS+28*i+4:DEFINITIONS+28*(i+1)] ==
                new_data[DEFINITIONS+28*i+4:DEFINITIONS+28*(i+1)] for i in range(COUNT)),
            'Monster attributes changed')
    for payload in (old_data, new_data):
        for at in range(0, len(payload)-3, 4):
            value = struct.unpack_from('<I', payload, at)[0]
            offset = (value-LINK_BASE) & 0xFFFFFFFF
            if offset <= 0xFFFF:
                struct.pack_into('<I', payload, at, RAM+offset)
    require(struct.unpack_from('<I', original, 0x2AA50)[0] == RAM ==
            struct.unpack_from('<I', original, 0x2AC28)[0], 'Monster header address differs')
    for ident in range(COUNT):
        selector = struct.unpack_from('<h', old_data, DEFINITIONS+28*ident+20)[0]
        require(selector >= 0, 'Negative monster announcement selector')
        # A synthetic actor is a static-analysis input, not a GBA allocation.
        actor = bytearray(0xC0)
        actor[0x91] = ident
        memory = ((RAM, (old_data, new_data)), (0x10001000, (actor, actor)))
        for family, seed, registers, site, record_site in (
                ('ability', 0x2A9BC, {5: (0x10001000,)*2}, 0x2A9DE, 0x2A9D0),
                ('projectile', 0x2ABB6, {5: (0x10001091,)*2, 4: (RAM,)*2},
                 0x2ABD0, 0x2ABC4)):
            check(f'{family}-{ident}', seed, registers, BASE+site,
                  [selector] if selector else [], memory, BASE+record_site)

    # The selected skill's action list starts empty; optional Set/disabled Set
    # stores 0/5, and the mandatory Info row stores 3. No other action is appended.
    require(struct.unpack_from('<I', original, 0x2128C)[0] == 0x227,
            'Skill action base differs')
    tables = (BASE+START, BASE+build['skill_menu']['table_offset'])
    for action in (0, 3, 5):
        check('skill-action-'+str(action), 0x21218,
              {1: (action,)*2, 8: tables}, BASE+0x21220, [0x227+action])
    require(struct.unpack_from('<I', original, 0x21594)[0] == 0x1F3,
            'Skill row default selector differs')
    for definition in skills()['entries']:
        for mode in (6, 0):
            # All values other than six take the same native comparison branch.
            selected = 0x1F0 if mode == 6 and definition['hunger_cost'] else 0x1F3
            check(f'skill-row-{definition["id"]}-mode-{mode}', 0x21534,
                  {4: (definition['id'],)*2, 9: (mode,)*2}, BASE+0x2156C, [selected])

    report = dict(passed=True, rom_sha256=digest(compiled), source_sha256=digest(original),
        tool_sha256=digest(Path(__file__).read_bytes()), checked_code=guards, cases=cases,
        soldier_producer=dict(entry=BASE+0x31CD4, callers=[BASE+0x28BE2, BASE+0x28C2E],
            soldier_species=0x89, type=2, selector_domain=list(range(7)),
            object_base=0x0200D048, stride=68, records=56, selector_offset=0x40,
            other_call='Species 57h supplies type 1 and selector 0; not the type-2 dialogue path.',
            evidence=['build/oct07-text/soldier-floor-producer.txt',
                      'build/oct07-text/soldier-object-producers.txt',
                      'build/oct07-text/soldier-rng-skill.txt',
                      'build/oct07-text/monster-selectors.txt']),
        shared_unresolved_sources=len(unresolved), scope=__doc__+
        '\nSoldier creation is a reviewed direct-call domain, not a whole-program RAM-write proof. '
        'All 141 monster records are passed to both selected readers, including zero suppression; '
        'this overapproximates projectile eligibility. Skill rows use all 128 definitions, mode '
        'six and a representative of the identical non-six branch. Static memory relocation '
        'matches the previously verified native dungeon loader. Downstream stops are retained. '
        'No ROM patches, new encounters or closure of the 62/34 unresolved records are claimed.')
    output = ROOT/'build/oct07-text/actor-skill-selectors.json'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2)+'\n')
    print('Actor/skill selectors:', len(cases), 'cases;',
          sum(len(c['reads']) for c in cases), 'English shared-table reads')
    return report


if __name__ == '__main__':
    run()
