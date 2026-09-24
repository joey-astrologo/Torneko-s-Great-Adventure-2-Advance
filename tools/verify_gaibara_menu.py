"""Original-sized synthesis menu: choice results, help and repeated reopening."""
import argparse
from tools.service_validation import load_candidate
import json
import mgba.log
from tools.rom import digest, require
from tools.emulator import Session, Debugger, Snapshot
from tools.dialogue_checks import TextChecks
from tools.audit_menu_layouts import Observer
from tools.verify_gaibara import OUT


def run(cumulative=False):
    global OUT
    mgba.log.silence()
    OUT, rom, build = load_candidate('gaibara', cumulative)
    require(digest(rom) == build['output_sha256'], 'Synthesis menu ROM differs')
    fixture = Snapshot.load(OUT / 'native/entry')
    require(fixture.rom_sha256 == digest(rom), 'Synthesis menu fixture differs')
    rows = build['gaibara']['entries']
    resources = {r['offset'] + 0x08000000: r for r in rows if r['layout']['direct_rom_stream']}
    resources.update({r['offset'] + 0x08000000: r for r in build['selection_prompt']['entries']})
    menu = next(r for r in rows if r['index'] == 112)
    results = []
    for case in ('cancel', 'leave', 'explain-reopen', 'synth-empty', 'first-time'):
        print('Synthesis menu:', case, flush=True)
        with Session(rom, OUT / ('menu-' + case)) as game:
            game.restore(fixture); m = game.core.memory
            initial = [int(v) & 0xFFFFFFFF for v in game.core.cpu.gprs]
            guard = bytes(m[initial[13]:initial[13] + 32]); overrides = []
            def write(address, data):
                overrides.append({'address': address, 'before': bytes(m[address:address + len(data)]).hex(), 'after': data.hex()})
                for i, value in enumerate(data): m.u8[address + i] = value
            if case == 'synth-empty': write(0x0200DF28, bytes(20 * 120))
            if case == 'first-time': write(0x02002C17, b'\0')
            before = bytes(m[0x0200DF28:0x0200DF28 + 20 * 120])
            gold_address = m.u32[0x02001624] + 0x60; gold = m.u32[gold_address]
            check = TextChecks(game, dict(resources)); observer = Observer(game)
            choices, returned, images = [], [], []
            def callback(event):
                a, r = event['address'], event['registers']
                if a == 0x0801D59A: choices.append(r[0])
                if a == 0x0801D822:
                    require(r[4:12] == initial[4:12] and r[13] == initial[13] and r[0] == initial[14]
                            and bytes(m[r[13]:r[13] + 32]) == guard, 'Synthesis menu caller ABI/guard differs')
                    returned.append(event)
                check.callback(event); observer.callback(event)
            def menu_count(): return sum(r['id'] == menu['id'] for r in check.reads)
            def reach_menu(count):
                for _ in range(24):
                    if menu_count() >= count and check.active is None: return
                    game.frames(90)
                    if menu_count() >= count and check.active is None: return
                    game.press('A', wait=0)
                raise ValueError('Synthesis root menu did not reopen')
            def capture(name):
                game.capture(name); images.append(name + '.png')
            with Debugger(game, callback, max_events=180000) as debug:
                for address in set(check.ADDRESSES + observer.ADDRESSES + (0x0801D59A, 0x0801D822)):
                    debug.breakpoint(address)
                reach_menu(1); capture('root')
                if case == 'explain-reopen':
                    for cycle in range(3):
                        game.press('DOWN', wait=20); capture(f'explain-selection-{cycle}')
                        game.press('A', wait=90)
                        reach_menu(cycle + 2); capture(f'reopened-{cycle}')
                    game.press('B', wait=90)
                elif case == 'leave':
                    game.press('DOWN', wait=20); game.press('DOWN', wait=20); capture('leave-selection')
                    game.press('A', wait=90)
                elif case == 'synth-empty': game.press('A', wait=90)
                else: game.press('B', wait=90)
                for page in range(20):
                    capture('after-' + str(page))
                    if returned: break
                    game.press('A', wait=90)
            require(returned and check.active is None, 'Synthesis menu did not finish')
            native = [r for r in observer.reads if r['raw_hex'] == menu['encoded_hex']]
            require(native and all(r['screen_x'] == 8 and r['window_width'] == 72 and r['rows'] == 3 and r['initial_x'] == 0 for r in native),
                    'Synthesis menu changed original geometry')
            for read in native:
                for line in range(3):
                    glyphs = [g for g in read['glyph_positions'] if g['row'] == line]
                    require(glyphs[0]['x'] == 0 and glyphs[1]['x'] == 6 and glyphs[2]['x'] == 12, 'Synthesis cursor reserve differs')
                    require(all(g['x'] < 72 for g in glyphs), 'Synthesis label clips')
            if case == 'leave': require(choices == [2], 'Synthesis Leave action differs')
            elif case == 'synth-empty': require(choices == [0] and check.completed('gaibara.33'), 'Synthesis empty-inventory result differs')
            elif case == 'explain-reopen':
                require(len(choices) == 4 and choices[:3] == [1,1,1] and choices[-1] not in (0,1), 'Synthesis help/reopen choices differ')
                require(sum(r['id'] == 'gaibara.199' for r in check.reads) == 3 and sum(r['id'] == 'gaibara.111' for r in check.reads) == 3,
                        'Synthesis complete tutorial/repeated help missing')
            else: require(len(choices) == 1 and choices[0] not in (0,1), 'Synthesis cancellation differs')
            if case == 'first-time': require(check.completed('gaibara.110') and m.u8[0x02002C17] == 1, 'Synthesis first greeting flag differs')
            require(bytes(m[0x0200DF28:0x0200DF28 + 20 * 120]) == before and m.u32[gold_address] == gold
                    and game.snapshot().battery == fixture.battery, 'Synthesis menu changed inventory/gold/battery')
            results.append({'case': case, 'overrides': overrides, 'choices': choices, 'reads': check.reads,
                            'native_menu_reads': native, 'glyph_checks': check.glyph_checks, 'inputs': game.inputs,
                            'images': {p: digest((game.output / p).read_bytes()) for p in images}})
    (OUT / 'menus.json').write_text(json.dumps({'passed': True, 'rom_sha256': digest(rom), 'cases': results,
        'scope': 'Controlled service entry. All three root choices, empty inventory, first-time introduction and three complete help/reopen cycles use native controls. Original x8/72px/three-row geometry and12px cursor reserve are preserved; Synthesise55px fits the60px label region. Caller ABI and inventory/gold/battery pass. Other synthesis panels and ordinary unlocking remain separate.'}, indent=2) + '\n')
    print('Synthesis menus:', len(results), 'cases passed', flush=True)


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--cumulative',action='store_true');run(parser.parse_args().cumulative)
