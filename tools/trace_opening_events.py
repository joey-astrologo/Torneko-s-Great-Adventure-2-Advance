"""Observe opening table slots, command side effects and both natural choices."""

import json

import mgba.log

from tools.emulator import Debugger, Session
from tools.event_text import opening_entries
from tools.opening_text import BANK_RAM, banks
from tools.rom import ROOT, digest, load_base, require
from tools.text_codec import readable, tokenize

OUTPUT = ROOT / 'build/opening-dialogue/research'


def run(branch):
    original = load_base()
    bank = banks()[0]
    rows = {(row['group'], row['index']): row for row in opening_entries()}
    output = OUTPUT / branch
    events, reads, slots, commands, choices = [], [], [], [], []
    choice_active = False
    reached_help = False
    with Session(original, output) as game:
        def callback(event):
            nonlocal choice_active, reached_help
            r, address = event['registers'], event['address']
            memory = game.core.memory
            if address == 0x0804F938:
                script = memory.u32[0x02010138]
                group, index = memory.u8[script + 1], memory.u8[script + 2]
                row = rows[group, index]
                require(r[5] == BANK_RAM + row['slot'], 'Native event offset slot differs')
                require(r[6] + memory.u32[r[3]] + memory.u32[r[5]] == BANK_RAM + row['start'],
                        'Native relative address differs')
                slots.append(dict(id=row['id'], group=group, index=index, slot=row['slot'],
                                  script=script, script_hex=bytes(memory[script:script + 5]).hex(),
                                  frame=event['frame']))
            elif address == 0x08051664:
                commands.append({'frame': event['frame'], 'raw_hex': bytes(memory[r[0]:r[0] + 3]).hex(),
                                 'before_flags': memory.u8[0x0201020E], 'source': r[0]})
            elif address == 0x080516AE:
                commands[-1]['after_flags'] = memory.u8[0x0201020E]
            elif address == 0x08015CE8:
                choice_active = True
                game.snapshot().save(output / 'choice')
            elif address == 0x08015E28:
                choice_active = False
                choices.append({'frame': event['frame'], 'result': r[0]})
            elif address == 0x080021B4:
                pointer = r[1]
                if BANK_RAM <= pointer < BANK_RAM + len(bank['data']):
                    start = pointer - BANK_RAM
                    tokens, end = tokenize(bank['data'], start)
                    reads.append({'id': f'event-bank-0.{start:04x}', 'source': {'kind': 'compressed-bank',
                                  'bank': bank['id'], 'offset': start, 'end_exclusive': end,
                                  'compressed_rom_offset': bank['rom_offset']},
                                  'raw_hex': bank['data'][start:end].hex(), 'tokens': tokens,
                                  'japanese': readable(tokens), 'frame': event['frame'],
                                  'window_hex': bytes(memory[r[0]:r[0] + 24]).hex()})
                if pointer == 0x0806B0E8:
                    reached_help = True
        with Debugger(game, callback, max_events=10000) as trace:
            for address in (0x0804F938, 0x08051664, 0x080516AE, 0x08015CE8, 0x08015E28, 0x080021B4):
                trace.breakpoint(address)
            route = json.loads((ROOT / 'config/routes/opening.json').read_text())
            for step in route['steps']:
                if 'frames' in step:
                    game.frames(step['frames'])
                elif 'press' in step:
                    game.press(step['press'], wait=step.get('wait', 120), hold=step.get('hold', 3))
                if step.get('capture') == 'opening-1':
                    break
            for i in range(130):
                if choice_active and not choices and branch == 'no':
                    game.press('RIGHT', wait=30)
                    game.capture('choice-no-selected')
                game.press('A', wait=240)
                game.capture(f'page-{i:03}')
                if reached_help:
                    break
            require(reached_help and len(choices) == 1, 'Opening route did not reach help with one choice')
            require(choices[0]['result'] == (branch == 'yes'), 'Choice outcome differs')
        inputs = game.inputs
    report = {'passed': True, 'branch': branch, 'source_rom_sha256': digest(original),
              'inputs': inputs, 'slots': slots, 'commands': commands, 'choices': choices, 'reads': reads}
    (output / 'trace.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(branch, len(reads), len(slots), commands, choices)
    return report


if __name__ == '__main__':
    mgba.log.silence()
    for branch in ('yes', 'no'):
        run(branch)
