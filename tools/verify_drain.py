"""Native strength/max-HP drain messages, clamping, fields and resistance."""
import argparse
import json
import struct
import mgba.log
from tools.compact_font import encode
from tools.drain_text import add_drain
from tools.emulator import Debugger, Session, ffi
from tools.name_entry import HERO
from tools.dialogue_checks import player_layout_cases
from tools.rom import ROOT, digest, require
from tools.verify_inventory_action_prototype import ActionCheck
from tools.verify_service_ui import materialize

OUT = ROOT / 'build/drain-prototype'


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
        OUT = ROOT / 'build/english/drain-validation'
        rom = (ROOT / 'build/english/torneko-2-english.gba').read_bytes()
        build = json.loads((ROOT / 'build/english/build.json').read_text())
        require(digest(rom) == build['output_sha256'], 'Stale cumulative drain ROM')
    else:
        rom, build = candidate()
    prior = status.OUT
    try:
        status.OUT = OUT
        fixture = status.ready(rom, build)
    finally:
        status.OUT = prior
    direct = {r['offset'] + 0x08000000: r for r in build['drain']['entries']}
    wrapper = {r['offset'] + 0x08000000: r for r in build['player_messages']['entries']}
    notices = {r['source']['offset'] + 0x08000000: r for r in build['combat']['queue_notices']['entries']}
    fields = {'maximum-width': encode('W' * 31), 'maximum-bytes': encode('i' * 31),
              'coloured': b'\x03\x05' + encode('Monster')[:-1] + b'\x05\0'}
    configs = [('strength', 0, 1, 8, 8, 40, 40), ('strength-clamp', 0, 5, 2, 2, 40, 40),
               ('strength-minimum', 0, 1, 1, 1, 40, 40), ('strength-current-low', 0, 2, 3, 8, 40, 40),
               ('hp', 1, 1, 8, 8, 40, 40), ('hp-clamp', 1, 5, 8, 8, 20, 20),
               ('hp-minimum', 1, 1, 8, 8, 19, 19), ('hp-current-low', 1, 1, 8, 8, 10, 40),
               ('resistant', 0, 1, 8, 8, 40, 40), ('strength-protected', 0, 1, 8, 8, 40, 40)]
    configs += [(f'{kind}-{name}', branch, 1, 8, 8, 40, 40)
                for kind, branch in [('strength', 0), ('hp', 1)] for name in fields]
    configs += [(f'player-{name}', 0, 1, 8, 8, 40, 40) for name, _ in player_layout_cases()]
    results = []
    for case, branch, amount, strength, maximum_strength, hp, maximum_hp in configs:
        print('Drain:', case, flush=True)
        with Session(rom, OUT / case) as game:
            game.restore(fixture)
            m = game.core.memory
            hero = m.u32[0x02001624]
            initial, returns, checks, slots, overrides, formats, images = [], [], [], [], [], [], []
            pending, formatted = [], {}
            gold = m.u32[hero + 0x60]
            inventory = bytes(m[0x0200DF28:0x0200DF28 + 2400])
            expected = ([0x344] if case == 'resistant' else
                        [0x258, 0x2FC if case == 'strength-protected' else 0xA18] if not branch else
                        [0x94C] + ([0x2BC] if maximum_hp > 19 else []))
            expected_strength = maximum_strength if case in ('resistant', 'strength-protected') or branch else max(1, maximum_strength - amount)
            expected_hp = max(2, maximum_hp - 5 * amount) if branch and maximum_hp > 19 else maximum_hp
            def write(address, data):
                overrides.append({'address': address, 'before': bytes(m[address:address + len(data)]).hex(),
                                  'after': data.hex()})
                for i, value in enumerate(data):
                    m.u8[address + i] = value
            def callback(event):
                address, regs = event['address'], event['registers']
                if address == 0x08008F4C and not initial:
                    initial.append(event | {'guard': bytes(m[regs[13]:regs[13] + 32]).hex()})
                    write(hero + 0x76, struct.pack('<HH', strength, maximum_strength))
                    write(hero + 0x84, struct.pack('<HH', hp, maximum_hp))
                    write(hero + 8, struct.pack('<I', (m.u32[hero + 8] & ~0x40000000) |
                                              (0x40000000 if case == 'strength-protected' else 0)))
                    if case.startswith('player-'):
                        name = dict(player_layout_cases())[case[7:]]
                        write(HERO, name.ljust(16, b'\0'))
                    actors = [m.u32[0x02001624 + 4 * i] for i in range(1, 56)]
                    actor = next(a for a in actors if 0x02000000 <= a < 0x02040000 and
                                 m.u32[a + 8] & 0x80000000 and m.u16[a + 0x84] > 0)
                    overrides.append({'event': event, 'pc_after': 0x0802BACC, 'r0_after': amount, 'r1_after': actor})
                    game.core.cpu.gprs[0], game.core.cpu.gprs[1] = amount, actor
                    require(game.core._core.writeRegister(game.core._core, b'pc',
                            ffi.new('uint32_t*', 0x0802BACC)), 'Drain entry redirect failed')
                if initial and address in (0x0802BADC, 0x0802BAFE):
                    value = int(case == 'resistant') if address == 0x0802BADC else branch * 99
                    overrides.append({'event': event, 'r0_after': value})
                    game.core.cpu.gprs[0] = value
                if initial and address in (0x0802BB12, 0x0802BBC6):
                    field = next((v for k, v in fields.items() if case.endswith('-' + k)), None)
                    if field:
                        write(0x02008D08, field.ljust(64, b'\0'))
                        overrides.append({'event': event, 'r0_after': 0x02008D08})
                        game.core.cpu.gprs[0] = 0x02008D08
                if initial and address == 0x08000FB8 and regs[1] in direct | wrapper:
                    row = (direct | wrapper)[regs[1]]
                    require(row['table_offset'] in expected and regs[0] == regs[13], 'Drain formatter owner differs')
                    if row['table_offset'] == 0xA18:
                        require(regs[3] == maximum_strength - expected_strength, 'Drain actual loss argument differs')
                    payload = materialize(bytes.fromhex(row['encoded_hex']), [regs[2], regs[3]], m)
                    require(len(payload) <= row['maximum_bytes'] <= 256, 'Drain output overflow')
                    pending.append((regs, row, payload, bytes(m[regs[0] + 256:regs[0] + 272])))
                if pending and address == (pending[-1][0][14] & ~1):
                    before, row, payload, guard = pending.pop()
                    require(regs[4:12] == before[4:12] and regs[13] == before[13] and
                            bytes(m[before[0]:before[0] + len(payload)]) == payload and
                            bytes(m[before[0] + 256:before[0] + 272]) == guard, 'Drain formatter bytes/guard/ABI differ')
                    formatted[before[0]] = (row, payload, guard)
                    formats.append({'id': row['id'], 'hex': payload.hex(), 'bytes': len(payload), 'capacity': 256})
                if initial and address == 0x0801588C and (regs[0] in notices or regs[0] in formatted):
                    require(not checks or checks[-1].complete and checks[-1].returned, 'Drain queues overlap')
                    if regs[0] in formatted:
                        row, payload, guard = formatted.pop(regs[0])
                        capacity = 256
                    else:
                        row = notices[regs[0]]
                        payload, capacity, guard = bytes.fromhex(row['encoded_hex']), None, b''
                    slots.append(row['table_offset'])
                    require(slots == expected[:len(slots)], 'Drain message order differs: ' + repr((case, slots)))
                    checks.append(ActionCheck(game, payload[:-1], regs[14], capacity, guard))
                if initial and address == 0x0802BC3C:
                    before = initial[0]
                    require(regs[4:12] == before['registers'][4:12] and regs[13] == before['registers'][13]
                            and regs[0] == before['registers'][14] and
                            bytes(m[regs[13]:regs[13] + 32]).hex() == before['guard'], 'Drain caller ABI differs')
                    state = [m.u16[hero + a] for a in (0x76, 0x78, 0x84, 0x86)]
                    require(state == [min(strength, expected_strength), expected_strength,
                                      min(hp, expected_hp), expected_hp], 'Drain native stats differ: ' + repr(state))
                    returns.append(event | {'stats': state})
                for check in checks:
                    if not (check.complete and check.returned):
                        check.callback(event)
            with Debugger(game, callback, max_events=150000) as debug:
                for address in (0x08008F4C, 0x0802BADC, 0x0802BAFE, 0x0802BB12, 0x0802BBC6,
                                0x08000FB8, 0x0802BB1C, 0x0802BBA8, 0x0802BBD0, 0x08015860,
                                0x0801588C, 0x080158CE, 0x08001BC4, 0x08001C14, 0x08001C68,
                                0x0802BAF0, 0x0802BB24, 0x0802BBB0, 0x0802BBD8, 0x08015868, 0x0802BC3C):
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
                    all(c.complete and c.returned for c in checks) and not pending and not formatted,
                    'Drain chain incomplete: ' + repr((case, slots, len(returns))))
            for i, check in enumerate(checks):
                wraps = (i == 0 and case.endswith('-maximum-width') or
                         i == 1 and case == 'player-widest-Japanese')
                require(check.queued['one_line'] == (not wraps), 'Drain conditional line choice differs')
            require(m.u32[hero + 0x60] == gold and bytes(m[0x0200DF28:0x0200DF28 + 2400]) == inventory
                    and game.snapshot().battery == fixture.battery, 'Drain changed gold/items/save')
            results.append({'case': case, 'queue_slots': slots, 'queues': [c.queued for c in checks],
                            'draws': [c.draws for c in checks], 'formats': formats, 'overrides': overrides,
                            'return': returns[0], 'inputs': game.inputs,
                            'images': {p: digest((game.output / p).read_bytes()) for p in images}})
    report = {'passed': True, 'rom_sha256': digest(rom), 'cases': results,
              'scope': 'Controlled native drain handler, random branch/resistance and initial stats. '
                       'Actual strength/max-HP loss, lower clamps and current-stat clamps, protection, '
                       'actor/player width/bytes/colours, native text and256-byte guards/ABI pass. '
                       'Ordinary monster AI and resistance acquisition remain separate.'}
    (OUT / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print('Drain:', len(results), 'cases passed', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cumulative', action='store_true')
    run(parser.parse_args().cumulative)
