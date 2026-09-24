"""Native monster level loss, minimum/transformed branches and player names."""
import argparse
import json
import struct
import mgba.log
from tools.compact_font import encode
from tools.level_drain_text import add_level_drain
from tools.emulator import Debugger, Session, ffi
from tools.name_entry import HERO
from tools.dialogue_checks import player_layout_cases
from tools.rom import ROOT, digest, require
from tools.verify_inventory_action_prototype import ActionCheck
from tools.verify_service_ui import materialize

OUT = ROOT / 'build/level-drain-prototype'


def candidate():
    from tools.build_english import build_rom
    rom, build = build_rom(include_story=False)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'game.gba').write_bytes(rom)
    (OUT / 'build.json').write_text(json.dumps(build, indent=2) + '\n')
    return rom, build


def run(cumulative=False):
    global OUT
    from tools import verify_player_status_prototype as status
    mgba.log.silence()
    if cumulative:
        OUT = ROOT / 'build/english/level-drain-validation'
        rom = (ROOT / 'build/english/torneko-2-english.gba').read_bytes()
        build = json.loads((ROOT / 'build/english/build.json').read_text())
        require(digest(rom) == build['output_sha256'], 'Stale cumulative level_drain ROM')
    else:
        rom, build = candidate()
    prior = status.OUT
    try:
        status.OUT = OUT
        fixture = status.ready(rom, build)
    finally:
        status.OUT = prior
    direct = {r['offset'] + 0x08000000: r for r in build['level_drain']['entries']}
    notices = {r['source']['offset'] + 0x08000000: r for r in build['combat']['queue_notices']['entries']}
    configs = [(branch + '-' + label, branch, label, name)
               for branch in ('one', 'two', 'clamp', 'minimum', 'transformed', 'resistant')
               for label, name in player_layout_cases()]
    results = []
    for case, branch, label, name in configs:
        level = 2 if branch == 'clamp' else 1 if branch == 'minimum' else 5
        amount = 2 if branch in ('two', 'clamp') else 1
        expected_level = level if branch in ('minimum', 'transformed', 'resistant') else max(1, level - amount)
        print('Level drain:', case, flush=True)
        with Session(rom, OUT / case) as game:
            game.restore(fixture)
            m = game.core.memory
            hero = m.u32[0x02001624]
            initial, returns, checks, slots, overrides, formats, images = [], [], [], [], [], [], []
            pending, formatted = [], {}
            gold = m.u32[hero + 0x60]
            inventory = bytes(m[0x0200DF28:0x0200DF28 + 2400])
            expected = [0x348 if branch == 'resistant' else 0x904 if branch == 'transformed'
                        else 0xC8 if branch == 'minimum' else 0xEC]
            def write(address, data):
                overrides.append({'address': address, 'before': bytes(m[address:address + len(data)]).hex(),
                                  'after': data.hex()})
                for i, value in enumerate(data):
                    m.u8[address + i] = value
            def callback(event):
                address, regs = event['address'], event['registers']
                if address == 0x08008F4C and not initial:
                    initial.append(event | {'guard': bytes(m[regs[13]:regs[13] + 32]).hex()})
                    write(hero + 0x88, struct.pack('<H', level))
                    write(hero + 0xBF, bytes([1 if branch == 'transformed' else 0]))
                    write(HERO, name.ljust(16, b'\0'))
                    actors = [m.u32[0x02001624 + 4 * i] for i in range(1, 56)]
                    actor = next(a for a in actors if 0x02000000 <= a < 0x02040000 and
                                 m.u32[a + 8] & 0x80000000 and m.u16[a + 0x84] > 0)
                    overrides.append({'event': event, 'pc_after': 0x0802BC4C, 'r0_after': actor, 'r1_after': amount})
                    game.core.cpu.gprs[0], game.core.cpu.gprs[1] = actor, amount
                    require(game.core._core.writeRegister(game.core._core, b'pc',
                            ffi.new('uint32_t*', 0x0802BC4C)), 'Level drain entry redirect failed')
                if initial and address == 0x0802BC56:
                    value = int(branch == 'resistant')
                    overrides.append({'event': event, 'r0_after': value})
                    game.core.cpu.gprs[0] = value
                if initial and address == 0x08000FB8 and regs[1] in direct:
                    row = direct[regs[1]]
                    require(row['table_offset'] in expected and regs[0] == regs[13], 'Level drain formatter owner differs')
                    payload = materialize(bytes.fromhex(row['encoded_hex']), [regs[2], regs[3]], m)
                    require(len(payload) <= row['maximum_bytes'] <= 256, 'Level drain output overflow')
                    pending.append((regs, row, payload, bytes(m[regs[0] + 256:regs[0] + 272])))
                if pending and address == (pending[-1][0][14] & ~1):
                    before, row, payload, guard = pending.pop()
                    require(regs[4:12] == before[4:12] and regs[13] == before[13] and
                            bytes(m[before[0]:before[0] + len(payload)]) == payload and
                            bytes(m[before[0] + 256:before[0] + 272]) == guard, 'Level drain formatter bytes/guard/ABI differ')
                    formatted[before[0]] = (row, payload, guard)
                    formats.append({'id': row['id'], 'hex': payload.hex(), 'bytes': len(payload), 'capacity': 256})
                if initial and address == 0x0801588C and (regs[0] in notices or regs[0] in formatted):
                    require(not checks or checks[-1].complete and checks[-1].returned, 'Level drain queues overlap')
                    if regs[0] in formatted:
                        row, payload, guard = formatted.pop(regs[0])
                        capacity = 256
                    else:
                        row = notices[regs[0]]
                        payload, capacity, guard = bytes.fromhex(row['encoded_hex']), None, b''
                    slots.append(row['table_offset'])
                    require(slots == expected[:len(slots)], 'Level drain message order differs: ' + repr((case, slots)))
                    checks.append(ActionCheck(game, payload[:-1], regs[14], capacity, guard))
                if initial and address == 0x0802BCE6:
                    before = initial[0]
                    require(regs[4:12] == before['registers'][4:12] and regs[13] == before['registers'][13]
                            and regs[0] == before['registers'][14] and
                            bytes(m[regs[13]:regs[13] + 32]).hex() == before['guard'], 'Level drain caller ABI differs')
                    require(m.u16[hero + 0x88] == expected_level, 'Native level result differs')
                    returns.append(event | {'level_before': level, 'level_after': m.u16[hero + 0x88]})
                for check in checks:
                    if not (check.complete and check.returned):
                        check.callback(event)
            with Debugger(game, callback, max_events=150000) as debug:
                for address in (0x08008F4C, 0x0802BC56, 0x08000FB8, 0x0802BCBC, 0x0802BCD0,
                                0x0801588C, 0x080158CE, 0x08001BC4, 0x08001C14, 0x08001C68,
                                0x0802BC6A, 0x0802BCD8, 0x0802BCE6):
                    debug.breakpoint(address)
                game.press('A', wait=0)
                captured = 0
                for _ in range(1500):
                    game.frames(1)
                    if len(checks) > captured and checks[-1].complete:
                        name = f'message-{captured}.png'
                        game.capture(name[:-4])
                        images.append(name)
                        captured = len(checks)
                    if returns and all(c.complete and c.returned for c in checks):
                        break
            require(len(initial) == len(returns) == 1 and slots == expected and
                    all(c.complete and c.returned and c.queued['one_line'] for c in checks) and not pending and not formatted,
                    'Level drain chain incomplete: ' + repr((case, slots, len(returns))))
            require(m.u32[hero + 0x60] == gold and bytes(m[0x0200DF28:0x0200DF28 + 2400]) == inventory
                    and game.snapshot().battery == fixture.battery, 'Level drain changed gold/items/save')
            results.append({'case': case, 'queue_slots': slots, 'queues': [c.queued for c in checks],
                            'draws': [c.draws for c in checks], 'formats': formats, 'overrides': overrides,
                            'return': returns[0], 'inputs': game.inputs,
                            'images': {p: digest((game.output / p).read_bytes()) for p in images}})
    report = {'passed': True, 'rom_sha256': digest(rom), 'cases': results,
              'scope': 'Controlled native monster level-drain entry, starting level/transformation/resistance. '
                       'Native one/two-level loss, minimum clamp, transformed/no-effect and resistance, '
                       'all three player-name bounds and complete single-line messages pass. Original256-byte '
                       'formatter guards, ABI and items/gold/save pass. Ordinary AI, transformation and '
                       'resistance acquisition remain separate.'}
    (OUT / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print('Level drain:', len(results), 'cases passed', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cumulative', action='store_true')
    run(parser.parse_args().cumulative)
