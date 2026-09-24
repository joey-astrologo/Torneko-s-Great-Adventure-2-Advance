"""Execute actual blacksmith exchanges/tip branches from controlled inventories."""
import argparse
import json
import struct
import mgba.log
from tools.rom import ROOT, digest, require
from tools.emulator import Session, Debugger, Snapshot
from tools.dialogue_checks import TextChecks
from tools.verify_service_ui import materialize
from tools.verify_blacksmith import OUT


def run(cumulative=False):
    global OUT
    mgba.log.silence()
    if cumulative:
        OUT = ROOT / 'build/english/blacksmith-validation'
        rom = (ROOT / 'build/english/torneko-2-english.gba').read_bytes()
        build = json.loads((ROOT / 'build/english/build.json').read_text())
    else:
        rom = (OUT / 'game.gba').read_bytes()
        build = json.loads((OUT / 'build.json').read_text())
    require(digest(rom) == build['output_sha256'], 'Blacksmith transaction ROM differs')
    fixture = Snapshot.load(OUT / 'native/entry')
    require(fixture.rom_sha256 == digest(rom), 'Blacksmith entry fixture differs')
    rows = build['blacksmith']['entries']
    resources = {r['offset'] + 0x08000000: r for r in rows if r['layout']['direct_rom_stream']}
    formats = {r['offset'] + 0x08000000: r for r in rows if not r['layout']['direct_rom_stream']}
    choice = next(r for r in build['dialogue']['entries'] if r['id'] == 'rom.0006309c')
    resources[choice['rom_offset'] + 0x08000000] = choice
    results = []
    for jobs in [0] + list(range(9, 100, 10)) + [119, 120]:
        case = 'jobs-' + str(jobs)
        print('Blacksmith exchange:', case, flush=True)
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
            for slot, ident in enumerate((1, 2, 3)):
                struct.pack_into('<I', inventory, slot * 120, 0xC8000000)
                inventory[slot * 120 + 5] = 1
                inventory[slot * 120 + 8] = mapping.index(ident)
                address = 0x02003BAC + ident * 20
                write(address, struct.pack('<I', m.u32[address] | 0x40000000))
            write(0x0200DF28, inventory)
            write(0x02002C14, bytes([2, 3]))
            write(0x02002C1A, struct.pack('<H', jobs))
            gold_address = m.u32[0x02001624] + 0x60
            gold = m.u32[gold_address]
            check = TextChecks(game, dict(resources))
            pending, rendered_formats, returned, images = {}, [], [], []
            def callback(event):
                a, r = event['address'], event['registers']
                if a == 0x08000FB8 and r[1] in formats:
                    row = formats[r[1]]
                    args = r[2:4]
                    payload = materialize(bytes.fromhex(row['encoded_hex']), args, m)
                    require(len(payload) <= row['layout']['maximum_formatted_bytes'] <= 512, 'Blacksmith exchange format exceeds capacity')
                    require(r[0] == r[13], 'Blacksmith exchange output address differs')
                    pending[r[14] & ~1] = (r[0], payload, bytes(m[r[0] + 512:r[0] + 544]), r[4:12], r[13], row, args)
                if a in pending:
                    dest, payload, guard, regs, sp, row, args = pending.pop(a)
                    require(bytes(m[dest:dest + len(payload)]) == payload and bytes(m[dest + 512:dest + 544]) == guard
                            and r[4:12] == regs and r[13] == sp, 'Blacksmith exchange formatter/guard/ABI differs')
                    check.resources[dest] = row | {'encoded_hex': payload.hex()}
                    rendered_formats.append({'id': row['id'], 'arguments': args, 'hex': payload.hex(), 'bytes': len(payload)})
                if a == 0x0801D542:
                    require(r[4:12] == initial[4:12] and r[13] == initial[13] and r[0] == initial[14]
                            and bytes(m[r[13]:r[13] + 32]) == caller_guard, 'Blacksmith exchange return ABI/guard differs')
                    returned.append(event)
                check.callback(event)
            ends = (0x0801D180, 0x0801D1A6, 0x0801D1FA, 0x0801D220, 0x0801D3D8, 0x0801D3FA, 0x0801D434, 0x0801D520)
            with Debugger(game, callback, max_events=300000) as debug:
                for address in set(check.ADDRESSES + (0x08000FB8, 0x0801D542) + ends):
                    debug.breakpoint(address)
                for page in range(110):
                    game.frames(90)
                    name = f'page-{page:03}'
                    game.capture(name); images.append(name + '.png')
                    if returned:
                        break
                    game.press('A', wait=0)
            require(returned and check.active is None and not pending, 'Blacksmith exchange did not finish')
            remaining = [(m.u8[0x020013D0 + m.u8[0x0200DF28 + 120 * i + 8]], m.u8[0x0200DF28 + 120 * i + 4])
                         for i in range(20) if m.u32[0x0200DF28 + 120 * i] & 0x80000000]
            require(len(remaining) == 1 and remaining[0][0] == 1 and remaining[0][1] in (1, 3), 'Blacksmith exchange items/enhancement differ')
            after_jobs = min(jobs + 1, 120)
            require(m.u16[0x02002C1A] == after_jobs and m.u32[gold_address] == gold, 'Blacksmith exchange count/gold differs')
            seen = {r['id'] for r in check.reads}
            if after_jobs % 10 == 0:
                tip = min(after_jobs // 10, 10) + 12
                require('blacksmith.' + str(tip) in seen and 'blacksmith.70' in seen, 'Blacksmith milestone tip missing')
            else:
                require('blacksmith.69' in seen, 'Blacksmith ordinary count explanation missing')
            require(game.snapshot().battery == fixture.battery, 'Blacksmith exchange wrote battery')
            results.append({'case': case, 'controlled_overrides': overrides, 'remaining_items': remaining, 'jobs_after': after_jobs,
                            'formats': rendered_formats, 'reads': check.reads, 'glyph_checks': check.glyph_checks,
                            'inputs': game.inputs, 'images': {p: digest((game.output / p).read_bytes()) for p in images}})
    report = {'passed': True, 'rom_sha256': digest(rom), 'cases': results,
              'scope': 'Controlled native blacksmith invocation, requested payments2/3, three known inventory items and job counter. Ordinary button presses execute the exchange, native item enhancement, payment removal, counter increment, all ten tip selections and cap120. Exact formats, pages, output/return guards and unchanged gold/battery pass. Ordinary unlocking and acquisition of these inputs remain separate.'}
    (OUT / 'transactions.json').write_text(json.dumps(report, indent=2) + '\n')
    print('Blacksmith exchanges:', len(results), 'cases passed', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cumulative', action='store_true')
    run(parser.parse_args().cumulative)
