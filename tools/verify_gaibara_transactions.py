"""Execute actual gaibara exchanges/tip branches from controlled inventories."""
import argparse
import json
import struct
import mgba.log
from tools.rom import ROOT, digest, require
from tools.emulator import Session, Debugger, Snapshot
from tools.dialogue_checks import TextChecks
from tools.audit_menu_layouts import Observer
from tools.verify_service_ui import materialize
from tools.verify_gaibara import OUT


def run(cumulative=False):
    global OUT
    mgba.log.silence()
    if cumulative:
        OUT = ROOT / 'build/english/gaibara-validation'
        rom = (ROOT / 'build/english/torneko-2-english.gba').read_bytes()
        build = json.loads((ROOT / 'build/english/build.json').read_text())
    else:
        rom = (OUT / 'game.gba').read_bytes()
        build = json.loads((OUT / 'build.json').read_text())
    require(digest(rom) == build['output_sha256'], 'Gaibara transaction ROM differs')
    fixture = Snapshot.load(OUT / 'native/entry')
    require(fixture.rom_sha256 == digest(rom), 'Gaibara entry fixture differs')
    rows = build['gaibara']['entries']
    resources = {r['offset'] + 0x08000000: r for r in rows if r['layout']['direct_rom_stream']}
    resources.update({r['offset'] + 0x08000000: r for r in build['selection_prompt']['entries']})
    formats = {r['offset'] + 0x08000000: r for r in rows if not r['layout']['direct_rom_stream']}
    choice = next(r for r in build['dialogue']['entries'] if r['id'] == 'rom.0006309c')
    resources[choice['rom_offset'] + 0x08000000] = choice
    results = []
    for joke, answer in [(0, 'yes')] + [(i, answer) for i in range(1, 13) for answer in ('yes', 'no')]:
        case = f'joke-{joke}-{answer}'
        print('Gaibara exchange:', case, flush=True)
        with Session(rom, OUT / ('exchange-' + case)) as game:
            game.restore(fixture)
            m = game.core.memory
            initial = [int(v) & 0xFFFFFFFF for v in game.core.cpu.gprs]
            caller_guard = bytes(m[initial[13]:initial[13] + 32])
            overrides = []
            def write(address, data):
                overrides.append({'address': address, 'before': bytes(m[address:address + len(data)]).hex(), 'after': data.hex()})
                for i, value in enumerate(data):
                    m.u8[address + i] = value
            mapping = bytes(m[0x020013D0:0x020014D0])
            inventory = bytearray(20 * 120)
            for slot, ident in enumerate((1, 2)):
                struct.pack_into('<I', inventory, slot * 120, 0xC8000000)
                inventory[slot * 120 + 4] = 3 + slot
                inventory[slot * 120 + 5] = 1
                inventory[slot * 120 + 8] = mapping.index(ident)
                address = 0x02003BAC + ident * 20
                write(address, struct.pack('<I', m.u32[address] | 0x40000000))
            write(0x0200DF28, inventory)
            overrides.append({'register': 1, 'before': int(game.core.cpu.gprs[1]), 'after': joke})
            game.core.cpu.gprs[1] = joke
            gold_address = m.u32[0x02001624] + 0x60
            write(gold_address, struct.pack('<I', 1000000))
            gold = m.u32[gold_address]
            check = TextChecks(game, dict(resources))
            observer = Observer(game)
            pending, rendered_formats, returned, images = {}, [], [], []
            next_button = 'A'
            questions = []
            def callback(event):
                nonlocal next_button
                a, r = event['address'], event['registers']
                if a == 0x0801D0D8:
                    selected = next((row for row in rows if row['offset'] + 0x08000000 == r[0]), None)
                    if selected:
                        index = selected['index']
                        next_button = 'B' if index == 54 or (39 <= index <= 50 and answer == 'no') else 'A'
                        questions.append({'id': selected['id'], 'button': next_button})
                    else:
                        next_button = 'A'  # Native formatted base/price questions.
                if a == 0x08000FB8 and r[1] in formats:
                    row = formats[r[1]]
                    args = r[2:4]
                    payload = materialize(bytes.fromhex(row['encoded_hex']), args, m)
                    require(len(payload) <= row['layout']['maximum_formatted_bytes'] <= 256, 'Gaibara exchange format exceeds capacity')
                    require(r[0] == r[13] + 0xF8, 'Gaibara exchange output address differs')
                    pending[r[14] & ~1] = (r[0], payload, bytes(m[r[0] + 256:r[0] + 288]), r[4:12], r[13], row, args)
                if a in pending:
                    dest, payload, guard, regs, sp, row, args = pending.pop(a)
                    require(bytes(m[dest:dest + len(payload)]) == payload and bytes(m[dest + 256:dest + 288]) == guard
                            and r[4:12] == regs and r[13] == sp, 'Gaibara exchange formatter/guard/ABI differs')
                    check.resources[dest] = row | {'encoded_hex': payload.hex()}
                    rendered_formats.append({'id': row['id'], 'arguments': args, 'hex': payload.hex(), 'bytes': len(payload)})
                if a == 0x0801D822:
                    require(r[4:12] == initial[4:12] and r[13] == initial[13] and r[0] == initial[14]
                            and bytes(m[r[13]:r[13] + 32]) == caller_guard, 'Gaibara exchange return ABI/guard differs')
                    returned.append(event)
                check.callback(event); observer.callback(event)
            ends = (0x0801D660, 0x0801D6B0, 0x0801D758)
            with Debugger(game, callback, max_events=300000) as debug:
                for address in set(check.ADDRESSES + observer.ADDRESSES + (0x08000FB8, 0x0801D822, 0x0801D0D8) + ends):
                    debug.breakpoint(address)
                for page in range(110):
                    game.frames(90)
                    name = f'page-{page:03}'
                    game.capture(name); images.append(name + '.png')
                    if returned:
                        break
                    game.press(next_button, wait=0)
            require(returned and check.active is None and not pending, 'Gaibara exchange did not finish')
            remaining = [(m.u8[0x020013D0 + m.u8[0x0200DF28 + 120 * i + 8]], m.u8[0x0200DF28 + 120 * i + 4])
                         for i in range(20) if m.u32[0x0200DF28 + 120 * i] & 0x80000000]
            require(remaining == [(1, 7)], 'Synthesis did not preserve base and add enhancements')
            prices = [row for row in rendered_formats if row['id'] == 'gaibara.52']
            require(len(prices) == 1 and 10 <= prices[0]['arguments'][0] <= gold, 'Synthesis native price missing')
            require(m.u32[gold_address] == gold - prices[0]['arguments'][0], 'Synthesis gold deduction differs')
            seen = {row['id'] for row in check.reads}
            require('selection-prompt.which' in seen, 'English item selector heading missing')
            heading = build['selection_prompt']['entries'][0]
            heading_reads = [r for r in observer.reads if r['raw_hex'] == heading['encoded_hex']]
            require(len(heading_reads) >= 2 and all(r['screen_x'] == 8 and r['window_width'] == 40 and r['rows'] == 1 and r['initial_x'] == 0 for r in heading_reads),
                    'Item selector heading geometry differs')
            require({'gaibara.113', 'gaibara.114', 'gaibara.118', 'gaibara.119'} <= seen, 'Synthesis selection/result prose missing')
            if joke:
                require('gaibara.' + str(38 + joke) in seen and 'gaibara.51' in seen, 'Synthesis joke/reveal missing')
                require({'id': 'gaibara.' + str(38 + joke), 'button': 'A' if answer == 'yes' else 'B'} in questions, 'Synthesis joke answer not exercised')
            require(game.snapshot().battery == fixture.battery, 'Gaibara exchange wrote battery')
            results.append({'case': case, 'controlled_overrides': overrides, 'remaining_items': remaining, 'joke': joke, 'joke_answer': answer, 'questions': questions, 'gold_before': gold, 'gold_after': m.u32[gold_address],
                            'formats': rendered_formats, 'reads': check.reads, 'glyph_checks': check.glyph_checks, 'heading_reads': heading_reads,
                            'inputs': game.inputs, 'images': {p: digest((game.output / p).read_bytes()) for p in images}})
    report = {'passed': True, 'rom_sha256': digest(rom), 'cases': results,
              'scope': 'Controlled native synthesis invocation with two known weapons enhanced+3/+4, a valid gold balance and joke selector0..12. Ordinary buttons select the base/partner, confirm the price and decline another synthesis. Native output retains base ID1 with+7, consumes both inputs, deducts the displayed fee and restores caller ABI/battery. Both answers to every joke retain its reveal and normal transaction. Ordinary unlocking, other item categories and preview shared-text coverage remain separate.'}
    (OUT / 'transactions.json').write_text(json.dumps(report, indent=2) + '\n')
    print('Gaibara exchanges:', len(results), 'cases passed', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cumulative', action='store_true')
    run(parser.parse_args().cumulative)
