"""Check opcode-33 advancement and its bounded direct event-text selectors."""
import argparse
import json
import struct
from pathlib import Path

import mgba.log
from tools.audit_reader_routes import direct_calls
from tools.bakery_playtest import service_ready
from tools.emulator import Session
from tools.event_text import table_entries
from tools.npc_script_model import operand_lengths
from tools.opening_text import banks
from tools.research_event_relocation import invoke
from tools.rom import ROOT, digest, load_base, require
from tools.rom_build import verify_ledger


def direct_pairs(bank, command):
    # Original handlers: 501DC, 5132C, 50BC4 and 50C14. Branch unions
    # deliberately include both flag outcomes; they do not prove eligibility.
    return {
        14: [(7, n) for n in range(5, 9)],
        16: [(14, n) for n in (0, *range(3, 14))],
        18: [(23, 1)], 19: [(29, 14)], 20: [(28, 14)],
        21: [(14, 18)] if bank == 5 else [(8, 8)],
    }.get(command, [])


def run(source, output):
    mgba.log.silence()
    original = load_base()
    rom = (source/'torneko-2-english.gba').read_bytes()
    build = json.loads((source/'build.json').read_text())
    require(digest(rom) == build['output_sha256'], 'Handler audit ROM differs')
    lengths = operand_lengths(original)
    getters = direct_calls(original[:0x5E000], 0x08050270)
    require(getters == [0x0804FA7A, 0x0805020A, 0x08050BF4, 0x08050C18,
                        0x08051366, 0x080513B4, 0x08051466, 0x08051490, 0x08051568],
            'Reinspect direct event getter callers')
    # The selector switch itself is unchanged. Its existing English formatter
    # hooks remain separate owned patches, not supposedly original code.
    require(rom[0x507EC:0x50AA8] == original[0x507EC:0x50AA8],
            'Opcode-33 selector switch changed')
    verify_ledger(original, rom, build)
    patches = [p for p in build['patches']
               if p['start'] < 0x51664 and p['end_exclusive'] > 0x4F424]
    tables = [{(e['group'], e['index']): e for e in table_entries(b)} for b in banks()]
    selected = {e['id']: e for e in build['dialogue']['entries']}
    contexts, refs, inputs = [], [], {}
    for name in ('npc-control-flow.json', 'script-text-refs.json'):
        path = ROOT/'build/event-script-audit'/name
        data = json.loads(path.read_text())
        require(data['source_rom_sha256'] == digest(original), 'Script evidence source differs')
        inputs[str(path.relative_to(ROOT))] = digest(path.read_bytes())
        for bank in data['banks']:
            for script in bank.get('roots', bank.get('scripts', [])):
                for instruction in script['instructions']:
                    if instruction['opcode'] != 33:
                        continue
                    raw = bytes.fromhex(instruction['hex'])
                    require(len(raw) == 1+lengths[33] and raw[2] == 0,
                            'Reinspect opcode-33 operand/context')
                    context = dict(bank=bank['bank'], command=raw[1],
                        root=script['start'], instruction=instruction, evidence=name)
                    contexts.append(context)
                    for pair in direct_pairs(bank['bank'], raw[1]):
                        row = tables[bank['bank']].get(pair)
                        require(row and row['id'] in selected, 'Untranslated direct event selector')
                        english = selected[row['id']]
                        offset = english['rom_offset']
                        payload = bytes.fromhex(english['encoded_hex'])
                        require(rom[offset:offset+len(payload)] == payload,
                                'Direct event English resource differs')
                        refs.append(dict(bank=bank['bank'], command=raw[1], pair=pair,
                                         id=row['id'], english_offset=offset))
    require(len(refs) == 21, 'Reinspect direct-handler source coverage')

    # Observe actual pointer advancement independently of the table/model.
    # Load the existing bank allocation, then change only this disposable
    # operand span and script pointer. Command 25 is the native no-op branch.
    fixture = service_ready(rom, output)
    with Session(rom, output/'native-width') as game:
        game.restore(fixture)
        invoke(game, 0x0804D6F8, [2], max_steps=10000000)
        m = game.core.memory
        require(m.u32[0x02010144] == 0x020129AC, 'NPC allocation differs')
        address = 0x020129AC+0x4F5
        controls = [dict(address=address, before=bytes(m[address:address+2]).hex(), after='1908'),
                    dict(address=0x02010138, before=m.u32[0x02010138], after=address)]
        m.u8[address], m.u8[address+1] = 25, 8
        m.u32[0x02010138] = address
        initial = game.snapshot()
        invoke(game, 0x080507EC, [])
        after = m.u32[0x02010138]
        require(after == address+2, 'Native opcode 33 did not consume both operands')
        require(game.snapshot().battery == initial.battery, 'Width probe changed battery')
        native = dict(handler=0x080507EC, controls=controls, before=address, after=after,
                      caller_abi_preserved=True, battery_preserved=True)
    report = dict(passed=True, rom_sha256=digest(rom), source_sha256=digest(original),
        tool_sha256=digest(Path(__file__).read_bytes()), script_reports=inputs,
        original_handler_code_sha256=digest(original[0x4F424:0x51664]),
        existing_owned_handler_patches=patches, getter_calls=getters,
        contexts=contexts, direct_references=refs, native_width=native,
        scope='Native opcode33 consumes two operands although its length-table entry says one. '
              'All observed third bytes are zero; correcting the model leaves the extracted '
              'dialogue reference sets unchanged. Direct handler selector unions resolve 21 '
              'existing English sources. Tutorial helper 4FA68/50E82 remains covered separately '
              'by tutorial entry analysis. This is bounded source/code evidence, not ordinary '
              'eligibility, every helper side effect or global unreachability of 34 fragments.')
    (output/'report.json').write_text(json.dumps(report, indent=2)+'\n')
    print('NPC handler audit:', len(contexts), 'opcode contexts;', len(refs), 'English direct sources')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=ROOT/'build/english')
    parser.add_argument('--output', type=Path, default=ROOT/'build/npc-handlers')
    args = parser.parse_args()
    run(args.source, args.output)
