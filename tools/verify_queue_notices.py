"""Native static-notice pointer mapping, queue flags, fallbacks, pixels and ABI."""
import argparse
import json
import struct
from pathlib import Path
import mgba.log

from tools.compact_font import encode
from tools.emulator import Debugger, Session
from tools.extract_shared_text import extract
from tools.name_entry import HERO
from tools.rom import ROOT, digest, require
from tools.verify_inventory_action_prototype import ActionCheck

OUT = ROOT / 'build/english/queue-notice-validation'


def run(source=ROOT / 'build/english', output=OUT, copied=False):
    global OUT
    OUT = Path(output)
    from tools import verify_player_status_prototype as status
    mgba.log.silence()
    rom = (source / 'torneko-2-english.gba').read_bytes()
    build = json.loads((source / 'build.json').read_text())
    require(digest(rom) == build['output_sha256'], 'Queue-notice ROM differs')
    prior = status.OUT
    try:
        status.OUT = OUT
        fixture = status.ready(rom, build)
    finally:
        status.OUT = prior
    rows = build['combat']['queue_notices']['entries']
    cases = [{'id': r['id'], 'pointer': r['source']['offset'] + 0x08000000,
              'payload': bytes.fromhex(r['encoded_hex']), 'mapped': True} for r in rows]
    if copied:
        cases += [{'id': r['id'] + '-copied', 'pointer': r['source']['offset'] + 0x08000000,
                   'payload': bytes.fromhex(r['encoded_hex']), 'mapped': True, 'copied': True,
                   'original_payload': bytes.fromhex(r['source']['raw_hex'])} for r in rows]
        prefix = next(r for r in rows if r['table_offset'] == 0x214)
        raw = bytes.fromhex(prefix['source']['raw_hex'])
        cases.append({'id': 'fallback-japanese-prefix', 'pointer': prefix['source']['offset'] + 0x08000000,
                      'payload': raw[:-1] + b'\x81\x49\0', 'mapped': False, 'copied': True,
                      'original_payload': raw, 'append_to_copy': True})
    sources = {r['table_offset']: r['source'] for r in extract()['entries']}
    mapped_offsets = {r['source']['offset'] for r in rows}
    fallback = next(sources[slot] for slot in (0x388, 0x414)
                    if sources[slot]['offset'] not in mapped_offsets)
    require(all(r['source']['offset'] != fallback['offset'] for r in rows), 'Fallback is mapped')
    cases += [
        {'id': 'fallback-japanese', 'pointer': fallback['offset'] + 0x08000000,
         'payload': bytes.fromhex(fallback['raw_hex']), 'mapped': False},
        {'id': 'fallback-english', 'pointer': rows[0]['offset'] + 0x08000000,
         'payload': bytes.fromhex(rows[0]['encoded_hex']), 'mapped': False},
        {'id': 'fallback-ram', 'pointer': HERO, 'payload': encode('Torneko'), 'mapped': False},
    ]
    results = []
    for config in cases:
        for flag in (0, 1):
            case = config['id'] + f'-flag{flag}'
            print('Queue notice:', case, flush=True)
            with Session(rom, OUT / case) as game:
                game.restore(fixture)
                m = game.core.memory
                initial, checks, overrides, returns, copied_buffers = [], [], [], [], []
                def write(address, data):
                    overrides.append({'address': address, 'before': bytes(m[address:address+len(data)]).hex(),
                                      'after': data.hex()})
                    for i, value in enumerate(data):
                        m.u8[address+i] = value
                if config['id'] == 'fallback-ram':
                    write(HERO, config['payload'].ljust(16, b'\0'))
                # A real Drink action opens the native message window before the
                # controlled source/flag substitution. Direct turn-callback
                # injection rendered glyphs while the window could be hidden.
                item = bytearray(120)
                struct.pack_into('<I', item, 0, 0xC8000000)
                item[4] = item[5] = 1
                item[8] = bytes(m[0x020013D0:0x020014D0]).index(177)
                write(0x0200DF28, item)
                address = 0x02003BAC + 177 * 20
                write(address, struct.pack('<I', m.u32[address] | 0x40000000))

                def callback(event):
                    address, regs = event['address'], event['registers']
                    entry = 0x08015848 if config.get('copied') else 0x0801588C
                    if address == entry and not initial:
                        initial.append(event | {'guard': bytes(m[regs[13]:regs[13] + 32]).hex()})
                        overrides.append({'event': event, 'r0_after': config['pointer'], 'r1_after': flag})
                        game.core.cpu.gprs[0] = config['pointer']
                        game.core.cpu.gprs[1] = flag
                        debug.breakpoint(regs[14] & ~1)
                        if not config.get('copied'):
                            checks.append(ActionCheck(game, config['payload'][:-1], regs[14], None, b''))
                            controlled = list(regs)
                            controlled[0:2] = [config['pointer'], flag]
                            event = event | {'registers': controlled}
                            regs = controlled
                    if initial and config.get('copied') and address == 0x0801588C and not checks:
                        original = config['original_payload']
                        require(regs[14] == 0x08015869 and regs[1] == flag and
                                bytes(m[regs[0]:regs[0] + len(original)]) == original,
                                'Native wrapper did not produce the original RAM copy')
                        if config.get('append_to_copy'):
                            replacement = config['payload']
                            overrides.append({'address': regs[0], 'before': original.hex(), 'after': replacement.hex()})
                            for i, value in enumerate(replacement):
                                m.u8[regs[0] + i] = value
                            original = replacement
                        copied_buffers.append((regs[0], original, bytes(m[regs[0] + 256:regs[0] + 272])))
                        checks.append(ActionCheck(game, config['payload'][:-1], regs[14], None, b''))
                    if copied_buffers and address == 0x08015868:
                        pointer, original, guard = copied_buffers[0]
                        require(bytes(m[pointer:pointer + len(original)]) == original and
                                bytes(m[pointer + 256:pointer + 272]) == guard,
                                'Copied notice changed caller buffer or guard')
                    if checks and not (checks[0].complete and checks[0].returned):
                        checks[0].callback(event)
                    if checks and address == (initial[0]['registers'][14] & ~1):
                        before = initial[0]
                        require(regs[4:12] == before['registers'][4:12] and
                                regs[13] == before['registers'][13] and
                                bytes(m[regs[13]:regs[13] + 32]).hex() == before['guard'],
                                'Queue mapping changed caller registers/stack')
                        returns.append(event)

                with Debugger(game, callback, max_events=60000) as debug:
                    for address in (0x08015848, 0x0801588C, 0x080158CE,
                                    0x08001BC4, 0x08001C14, 0x08001C68, 0x08015868):
                        debug.breakpoint(address)
                    game.press('B', hold=8, wait=30)
                    game.press('A', wait=30)
                    game.press('A', wait=30)
                    actions = []
                    for i in range(7):
                        value = m.u16[0x0200CDD0+i*2]
                        if not value:
                            break
                        actions.append(value)
                    require(13 in actions, 'Native Life herb Drink action absent')
                    for _ in range(actions.index(13)):
                        game.press('DOWN', wait=20)
                    game.capture('selection')
                    game.press('A', wait=0)
                    for _ in range(900):
                        game.frames(1)
                        if returns and checks[0].complete and checks[0].returned:
                            break
                    require(len(initial) == len(checks) == len(returns) == 1 and
                            checks[0].complete and checks[0].returned and
                            checks[0].queued['one_line'] == (b'\r' not in config['payload']),
                            'Queue notice did not render and return: ' + repr((case, len(initial),
                                len(checks), len(returns), [(c.complete, c.returned, c.queued) for c in checks],
                                [hex(e['address']) for e in debug.events[:24]])))
                    picture = game.capture('rendered')
                    # Prove the captured frame displays every authored glyph, not
                    # merely that the renderer prepared off-screen tile pixels.
                    origin_x, origin_y = m.u8[0x02000000], m.u8[0x02000001]
                    screen_pixels = 0
                    require(len(checks[0].queued['line_widths']) <= 2, 'Static notice needs an owned paged reader')
                    visible_draws = []
                    for draw in checks[0].draws:
                        if draw['native_scroll']:
                            shift = draw['key'][-1] - draw['y']
                            require(shift > 0, 'Unexpected native scroll direction')
                            for prior_draw in visible_draws:
                                prior_draw['final_y'] -= shift
                        visible_draws.append(draw | {'final_y': draw['y']})
                    for draw in visible_draws:
                        require(draw['final_y'] >= 0, 'Static notice scrolled its own text out of view')
                        glyph, _ = checks[0].glyph_record(draw['code'])
                        for y, row in enumerate(glyph['rows']):
                            for x, bit in enumerate(row):
                                px = origin_x + draw['x'] + x
                                py = origin_y + draw['final_y'] * 16 + y
                                require(0 <= px < 240 and 0 <= py < 160 and
                                        (picture.getpixel((px, py)) == (255, 255, 255)) == (bit == '#'),
                                        'Queue capture does not display the authored glyph pixels')
                                screen_pixels += 1
                require(game.snapshot().battery == fixture.battery, 'Queue mapping changed battery save')
                results.append({'case': case, 'id': config['id'], 'mapped': config['mapped'],
                                'flag': flag, 'copied': bool(config.get('copied')),
                                'caller_buffer_unchanged': bool(copied_buffers),
                                'overrides': overrides, 'queue': checks[0].queued,
                                'draws': checks[0].draws, 'inputs': game.inputs,
                                'final_screen_glyph_pixels_match': True, 'screen_pixels_checked': screen_pixels,
                                'images': {name: digest((game.output / name).read_bytes()) for name in ('selection.png', 'rendered.png')}})
    report = {'passed': True, 'rom_sha256': digest(rom), 'cases': results, 'copied_strings_tested': copied,
              'visible_window_recipe': 'Native Life herb Drink action before controlled source/flag substitution.',
              'scope': 'Native Drink dispatch with controlled static source and flag arguments at its queue or player wrapper. '
                       'Each reviewed static notice passes both flags with exact authored line counts, bounded output, glyph '
                       'pixels/cursors, caller ABI/stack and unchanged gameplay during queue execution. '
                       'Unmapped Japanese, already-English and RAM strings remain unchanged. '
                       'No shared table mutation or ordinary gameplay reachability claim. '
                       'Dynamic formatted-message parsing is outside this mapping.'}
    if copied:
        report['scope'] += (' Additional cases run every original static string through the native player '
                            'formatter before queuing its RAM copy. Exact copies translate without modifying '
                            'the caller buffer/guard. A Japanese message with an appended suffix stays unchanged. '
                            'This prototype tests complete static copies, not dynamic formatted-message parsing.')
    (OUT / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print('Queue notices:', len(results), 'cases passed', flush=True)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=ROOT / 'build/english')
    parser.add_argument('--output', type=Path, default=OUT)
    parser.add_argument('--copied', action='store_true')
    args = parser.parse_args()
    run(args.source, args.output, args.copied)
