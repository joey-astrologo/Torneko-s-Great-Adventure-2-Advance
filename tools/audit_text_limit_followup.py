"""Expand the 49 limited table-reader seeds and classify non-length exits.

The two profiles complement one another; neither is whole-program coverage.
Instruction/path limits remain explicit even when no new reader is found.
"""
import json
from pathlib import Path
import struct

from tools.audit_reader_routes import direct_calls
from tools.audit_text_callers import BASE, trace
from tools.lz77 import decompress
from tools.rom import ROOT, digest, load_base, require
from tools.thumb_switches import switches
from tools.town_text import RAM, relocate, resource


def run():
    original = load_base()
    compiled = (ROOT/'build/torneko-2-english.gba').read_bytes()
    build = json.loads((ROOT/'build/english/build.json').read_text())
    require(digest(compiled) == build['output_sha256'], 'Root ROM identity differs')
    prior_path = ROOT/'build/caller-continuation/computed-table-losses.json'
    prior = json.loads(prior_path.read_text())
    require(prior['source_sha256'] == digest(original), 'Source evidence differs')
    seeds = [r['seed']-BASE for r in prior['limits']]
    known = {r['address'] for r in prior['losses']}
    require(len(seeds) == 49, 'Limited seed cohort changed')
    old = relocate(resource()['data'])
    new = relocate(decompress(compiled, build['dialogue']['town_resource']['rom_offset'])[0])
    domains = switches(original, compiled, 0x5E000)
    profiles = []
    for budget, maximum_path in ((40000, 256), (200000, 900)):
        losses, stop_rows = {}, {}
        def observe(pc, opcode, x, y, seed):
            value = x or y
            if not (0x08140D68 <= value[0] < 0x081417A0 or RAM <= value[0] < RAM+1200):
                return
            row = losses.setdefault((pc, value), dict(address=pc, opcode=opcode,
                                                      value=value, seeds=[]))
            if seed not in row['seeds']:
                row['seeds'].append(seed)
        def stopped(row):
            stop_rows.setdefault((row['reason'], row['address']), row)
        _, limits, counts = trace(original, compiled, seeds, {}, budget=budget,
            max_path_length=maximum_path, stack_model=True, paired_stack_adjustments=True,
            memory_images=((RAM, (old, new)),), switch_domains=domains,
            unknown_operand_observer=observe, stop_observer=stopped)
        require(not {r['address'] for r in losses.values()}-known,
                'New computed reader requires investigation')
        dispositions = []
        for row in stop_rows.values():
            reason, pc = row['reason'], row['address']-BASE
            if reason == 'path_length_limit':
                continue
            if reason == 'indirect_branch_or_return':
                previous, branch = struct.unpack_from('<HH', original, pc-2)
                register = (branch >> 3) & 15
                require(branch & 0xFF87 == 0x4700 and register < 8 and
                        previous == 0xBC00 | (1 << register) and
                        original[pc-2:pc+2] == compiled[pc-2:pc+2],
                        'New indirect exit is not a native POP/BX return')
                disposition = 'Native POP/BX epilogue.'
            elif reason == 'patched_instruction':
                owner = next(p for p in build['patches'] if p['start'] <= pc < p['end_exclusive'])
                require((pc, owner['owner']) in ((0xF012, 'item-text'),
                                                (0x14BE6, 'english-name-entry')),
                        'Unclassified patched path')
                disposition = 'Existing owned patch: '+owner['owner']
            elif reason == 'unsupported_opcode_fd58':
                require(pc == 0xBE8C and direct_calls(original[:0x5E000], BASE+0xCC82) ==
                        [BASE+0xBE88], 'Long branch disposition differs')
                require(original[0xBE88:0xBE90] == compiled[0xBE88:0xBE90] and
                        original[0xCC82:0xCC96] == compiled[0xCC82:0xCC96] ==
                        bytes.fromhex('aa239b009d4438bc9846a146aa46f0bc02bc0847'),
                        'Shared function epilogue changed')
                disposition = ('BL at BE88 is a long branch to the shared CC82 epilogue. '
                    'That epilogue restores SP/high registers and pops the enclosing return '
                    'address; it does not return to BE8C. The trace incorrectly continued '
                    'into a literal pool after treating this branch as a returning call.')
            else:
                raise ValueError('Unclassified non-length stop: '+reason)
            dispositions.append(dict(address=BASE+pc, reason=reason, disposition=disposition))
        profiles.append(dict(budget=budget, maximum_path=maximum_path,
            losses=list(losses.values()), new_reader_sites=[], limits=limits,
            stop_counts=counts, stop_details=list(stop_rows.values()), dispositions=dispositions))
    report = dict(passed=True, rom_sha256=digest(compiled), source_sha256=digest(original),
        tool_sha256=digest(Path(__file__).read_bytes()),
        engine_sha256=digest((ROOT/'tools/audit_text_callers.py').read_bytes()),
        prior_report_sha256=digest(prior_path.read_bytes()), prior_rom_sha256=prior['rom_sha256'],
        seeds=seeds, profiles=profiles,
        scope='Two complementary expansions of the 49 formerly budget-limited literal seeds. '
              'No new computed table-reader site. Non-length exits are verified native '
              'returns, existing item/name patches and one shared epilogue reached with BL. '
              'Path limits and remaining instruction budgets are retained; this does not '
              'close arbitrary RAM producers or classify the 62 sources globally unused.')
    out = ROOT/'build/oct07-text/limit-followup.json'
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2)+'\n')
    print('Text limit follow-up:', len(seeds), 'seeds; no new readers;',
          len(profiles[-1]['dispositions']), 'non-length exit dispositions')


if __name__ == '__main__':
    run()
