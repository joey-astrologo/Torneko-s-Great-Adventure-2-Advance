"""Follow both event interpreters and verify their branch arithmetic natively.

Setup roots use 4F280, which skips dialogue and choice commands. Scene roots
use 4EF40, whose out-of-range opcodes are one-byte no-ops. Both branch outcomes
are included; this is a conservative script graph, not scene eligibility.
"""
import json
from pathlib import Path
import struct

import mgba.log
from tools.audit_reader_routes import direct_calls
from tools.bakery_playtest import service_ready
from tools.emulator import Debugger, Session, ffi
from tools.event_text import table_entries
from tools.lz77 import decompress
from tools.npc_script_model import operand_lengths
from tools.opening_text import banks
from tools.research_event_relocation import invoke
from tools.rom import ROOT, default_rom, digest, load_base, require

BASE = 0x08000000
SCRIPT = 0x02010138
FLAGS = 0x020101AC
CHOICE = 0x0201017C
OUT = ROOT/'build/oct07-text/event-script-paths'


def walk(rom, start, end, mode, lengths):
    pending, seen, instructions, errors = [start], set(), [], []
    while pending:
        pc = pending.pop()
        if pc in seen:
            continue
        seen.add(pc)
        if not start <= pc < end:
            errors.append(dict(at=pc, reason='Outside root'))
            continue
        opcode = rom[pc]
        if mode == 1 and opcode >= len(lengths):
            errors.append(dict(at=pc, reason='Setup operand-table overread'))
            continue
        size = 1 + (lengths[opcode] if opcode < len(lengths) else 0)
        if pc+size > end:
            errors.append(dict(at=pc, reason='Truncated operands'))
            continue
        successors = [] if opcode == 21 else [pc+size]
        if opcode == 6:
            successors.append(pc+struct.unpack_from('<b', rom, pc+4)[0])
        elif opcode == 16 and mode == 2:
            successors.append(pc+rom[pc+1])
        instructions.append(dict(address=pc, opcode=opcode,
            hex=rom[pc:pc+size].hex(), successors=successors))
        pending.extend(successors)
    return sorted(instructions, key=lambda row: row['address']), errors


def run():
    mgba.log.silence()
    OUT.mkdir(parents=True, exist_ok=True)
    original = load_base()
    source_save = default_rom().with_suffix('.sav')
    save_hash = digest(source_save.read_bytes())
    compiled = (ROOT/'build/torneko-2-english.gba').read_bytes()
    build = json.loads((ROOT/'build/english/build.json').read_text())
    require(digest(compiled) == build['output_sha256'], 'Root ROM differs from build')
    lengths = operand_lengths(original)
    setup_lengths = list(original[0x14CEBC:0x14CEE0])
    guards = []
    for lo, hi in ((0x4E848, 0x4E8B0), (0x4EF40, 0x4EF7E),
                   (0x4F280, 0x4F380), (0x4F888, 0x4F8E4),
                   (0x4FE28, 0x4FE68), (0x52DB0, 0x52DDA),
                   (0x14CE30, 0x14CEE0)):
        require(original[lo:hi] == compiled[lo:hi], 'Interpreter code changed')
        guards.append(dict(start=lo, end_exclusive=hi,
                           sha256=digest(original[lo:hi])))
    require(direct_calls(original[:0x5E000], BASE+0x4F280) == [BASE+0x4E87E],
            'Setup interpreter has another caller')
    switch = list(struct.unpack_from('<34I', original, 0x4F2A0))
    expected = {2: 0x4F328, 3: 0x4F33A, 6: 0x4F334,
                11: 0x4F32E, 34: 0x4F346, 35: 0x4F340}
    require(switch == [BASE+expected.get(op, 0x4F34C) for op in range(2, 36)],
            'Setup interpreter dispatch differs')
    require(struct.unpack_from('<I', original, 0x52DD0)[0] == FLAGS and
            struct.unpack_from('<I', original, 0x4FE48)[0] == CHOICE,
            'Branch state addresses differ')
    linear_path = ROOT/'build/event-script-audit/script-text-refs.json'
    linear = json.loads(linear_path.read_text())
    require(linear['source_rom_sha256'] == digest(original), 'Linear input differs')
    tables = [{(r['group'], r['index']): r for r in table_entries(b)} for b in banks()]
    selected = {r['id']: r for r in build['dialogue']['entries']}
    roots, references, branches, anomalies = [], [], [], []
    for bank in linear['banks']:
        lo, hi = bank['rom_start'], bank['rom_end_exclusive']
        require(original[lo:hi] == compiled[lo:hi], 'Event script bytes changed')
        for script in bank['scripts']:
            start, end = script['start'], script['end_exclusive']
            mode = original[start]
            require(mode in (1, 2), 'Unknown event header mode')
            instructions, errors = walk(original, start+4, end, mode,
                                        setup_lengths if mode == 1 else lengths)
            require(not errors, 'Unresolved event control flow: '+str(errors))
            linear_starts = {i['address'] for i in script['instructions']}
            for row in instructions:
                pc, opcode = row['address'], row['opcode']
                context = dict(bank=bank['bank'], root=script['index'], mode=mode)
                if pc not in linear_starts:
                    anomalies.append(context | row)
                if opcode == 6 or (opcode == 16 and mode == 2):
                    branches.append(context | row)
                if opcode != 8 or mode != 2:
                    continue
                _, actor, group, index, display, extra = original[pc:pc+6]
                entry = tables[bank['bank']].get((group, index))
                require(entry is not None, 'Event selector is outside text table')
                ref = context | dict(address=pc, actor=actor, group=group, index=index,
                                     display=display, extra=extra, id=entry['id'])
                if display != 2:
                    require(entry['id'] in selected, 'Untranslated scene dialogue')
                    english = selected[entry['id']]
                    target, raw = english['rom_offset'], bytes.fromhex(english['encoded_hex'])
                    require(compiled[target:target+len(raw)] == raw, 'English bytes differ')
                    ref['english_offset'] = target
                references.append(ref)
            roots.append(dict(bank=bank['bank'], index=script['index'], mode=mode,
                start=start, end_exclusive=end, header_hex=original[start:start+4].hex(),
                instructions=instructions, errors=errors))
    require({(r['bank'], r['address']) for r in references} ==
            {(r['bank'], r['address']) for r in linear['references']},
            'Dialogue set differs from linear scan')

    # Search every byte as well as instruction starts. An embedded 08 byte is
    # not an entry by itself; retain candidates and their graph disposition.
    inventory = json.loads((ROOT/'build/text-inventory/catalog.json').read_text())
    fragments = {r['id'] for r in inventory['entries']
                 if r['family'] == 'event' and r['language_status'] == 'untranslated'}
    candidates = []
    for bank in range(7):
        pointer = struct.unpack_from('<I', compiled, 0x14CD68+4*bank)[0]-BASE
        npc, _ = decompress(compiled, pointer)
        header = struct.unpack_from('<5I', npc)
        script_bank = linear['banks'][bank]
        spans = [('npc', npc, header[3], header[4]),
                 ('event', original, script_bank['scripts'][0]['start'],
                  script_bank['rom_end_exclusive'])]
        for kind, data, lo, hi in spans:
            for pc in range(lo, hi-5):
                if data[pc] != 8:
                    continue
                entry = tables[bank].get((data[pc+2], data[pc+3]))
                if entry and entry['id'] in fragments:
                    reachable = kind == 'event' and any(
                        r['bank'] == bank and any(i['address'] == pc for i in r['instructions'])
                        for r in roots)
                    require(not reachable, 'Fragment has an event entry path')
                    candidates.append(dict(kind=kind, bank=bank, at=pc, id=entry['id'],
                        hex=data[pc:pc+6].hex(), event_entry_reached=reachable))

    # Both outcomes of every recovered flag/choice branch execute the native
    # handlers using unchanged cartridge operands. No scene side effects or
    # ordinary flag eligibility are inferred from these isolated calls.
    fixture = service_ready(compiled, OUT)
    native = []
    with Session(compiled, OUT/'native-branches') as game:
        for branch in branches:
            pc, opcode = branch['address'], branch['opcode']
            for value in (0, 1):
                game.restore(fixture)
                m = game.core.memory
                controls = [dict(address=SCRIPT, size=4, before=m.u32[SCRIPT], after=BASE+pc+1)]
                m.u32[SCRIPT] = BASE+pc+1
                if opcode == 6:
                    flag = original[pc+2]
                    address, mask = FLAGS+flag//8, 1 << (flag % 8)
                    before = m.u8[address]
                    m.u8[address] = (before & ~mask) | (value*mask)
                    controls.append(dict(address=address, size=1, before=before, after=m.u8[address]))
                    condition = int(bool(original[pc+3]))
                    handler = BASE+0x4F888
                else:
                    controls.append(dict(address=CHOICE, size=4, before=m.u32[CHOICE], after=value))
                    m.u32[CHOICE] = value
                    condition = int(bool(original[pc+2]))
                    handler = BASE+0x4FE28
                invoke(game, handler, [])
                expected = BASE+branch['successors'][int(value == condition)]
                require(m.u32[SCRIPT] == expected, 'Native branch/model disagreement')
                require(game.snapshot().battery == fixture.battery, 'Branch probe wrote save')
                native.append(dict(bank=branch['bank'], root=branch['root'], opcode=opcode,
                    instruction=pc, value=value, after=m.u32[SCRIPT], controls=controls,
                    abi_preserved=True, battery_preserved=True))

        # Verify the normal interpreter's unexpected 28h byte advances once.
        # Continue at the final handler's controlled return boundary. Restoring
        # the raw fixture here would instead re-enter its suspended BIOS wait.
        require(native, 'No native branch boundary available')
        m = game.core.memory
        address = BASE+0x43D694
        require(m.u8[address] == 40, 'Unexpected-opcode source differs')
        before = m.u32[SCRIPT]
        m.u32[SCRIPT] = address
        cpu = game.core.cpu
        r4_before, pc_before = int(cpu.gprs[4]), int(cpu.gprs[15])
        cpu.gprs[4] = SCRIPT
        cpsr_before = int(cpu.cpsr.packed)
        require(game.core._core.writeRegister(game.core._core, b'cpsr',
                    ffi.new('uint32_t*', cpsr_before | 0x20)), 'Thumb mode failed')
        require(game.core._core.writeRegister(game.core._core, b'pc',
                    ffi.new('uint32_t*', BASE+0x4EF54)), 'Dispatcher entry failed')
        with Debugger(game) as debug:
            debug.breakpoint(BASE+0x4EF70)
            debug.run_until(lambda events: bool(events), max_steps=1000)
        require(m.u32[SCRIPT] == address+1, 'Unknown opcode did not advance once')
        require(game.snapshot().battery == fixture.battery, 'Dispatcher probe wrote save')
        no_op = dict(instruction=address, after=m.u32[SCRIPT],
            starting_state='Final branch probe at controlled return 08000354',
            controls=[dict(address=SCRIPT, before=before, after=address),
                      dict(register='r4', before=r4_before, after=SCRIPT,
                           note='Isolated dispatcher scratch register; no ABI claim'),
                      dict(register='cpsr', before=cpsr_before, after=cpsr_before | 0x20),
                      dict(register='pc', before=pc_before, after=BASE+0x4EF54)],
            stop=BASE+0x4EF70, battery_preserved=True)

    require(digest(default_rom().read_bytes()) == digest(original) and
            digest(source_save.read_bytes()) == save_hash, 'Source files changed')
    report = dict(passed=True, source_rom_sha256=digest(original),
        rom_sha256=digest(compiled), source_save_sha256=save_hash,
        tool_sha256=digest(Path(__file__).read_bytes()), guards=guards,
        linear_report_sha256=digest(linear_path.read_bytes()), roots=roots,
        references=references, non_linear_entries=anomalies, fragment_candidates=candidates,
        native_branches=native, native_unknown_opcode=no_op,
        scope='Both native event interpreter modes; both flag/choice outcomes and WAIT '
              'continuations, bounded by the 133 original roots. Header eligibility, actor '
              'job completion, arbitrary RAM writes, direct getters and NPC selection '
              'remain separate. Native branch probes verify pointer arithmetic, not '
              'ordinary access or complete scenes. No new dialogue references or ROM changes.')
    (OUT/'report.json').write_text(json.dumps(report, indent=2)+'\n')
    print('Event script paths:', len(roots), 'roots;', len(references), 'dialogues;',
          len(native), 'native branch outcomes;', len(candidates), 'fragment byte candidates')
    return report


if __name__ == '__main__':
    run()
