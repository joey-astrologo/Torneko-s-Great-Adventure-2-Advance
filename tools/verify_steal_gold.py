"""Native monster gold theft, actual transfers, refusals and bounded fields."""
import argparse
import json
import struct
import mgba.log
from tools.compact_font import encode
from tools.steal_gold_text import add_steal_gold
from tools.emulator import Debugger, Session, ffi
from tools.name_entry import HERO
from tools.dialogue_checks import player_layout_cases
from tools.rom import ROOT, digest, require
from tools.verify_inventory_action_prototype import ActionCheck
from tools.verify_service_ui import materialize

OUT = ROOT / 'build/steal-gold-prototype'


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
        OUT = ROOT / 'build/english/steal-gold-validation'
        rom = (ROOT / 'build/english/torneko-2-english.gba').read_bytes()
        build = json.loads((ROOT / 'build/english/build.json').read_text())
        require(digest(rom) == build['output_sha256'], 'Stale cumulative steal_gold ROM')
    else:
        rom, build = candidate()
    prior = status.OUT
    try:
        status.OUT = OUT
        fixture = status.ready(rom, build)
    finally:
        status.OUT = prior
    direct = {r['offset'] + 0x08000000: r for r in build['steal_gold']['entries']}
    fields = {'maximum-width': encode('W' * 31), 'maximum-bytes': encode('i' * 31),
              'coloured': b'\x03\x05' + encode('Monster')[:-1] + b'\x05\0'}
    configs = [('ordinary', 100, 10), ('empty', 0, 10), ('all-gold', 7, 10),
               ('maximum-gold', 99999999, 99999999), ('protected', 100, 10),
               ('ability', 100, 10), ('transformed', 100, 10)]
    configs += [(name, 99999999, 99999999) for name in fields]
    configs += [('combined-' + name, 99999999, 99999999) for name in ('maximum-width', 'maximum-bytes')]
    configs += [('player-' + label, 99999999, 99999999) for label, _ in player_layout_cases()]
    results = []
    for case, gold, roll in configs:
        failed = case in ('protected', 'ability', 'transformed')
        stolen = 0 if failed else min(gold, min(99999999, roll * 4))
        print('Gold theft:', case, flush=True)
        with Session(rom, OUT / case) as game:
            game.restore(fixture)
            m = game.core.memory
            hero = m.u32[0x02001624]
            initial, returns, checks, slots, overrides, formats, images = [], [], [], [], [], [], []
            pending, formatted = [], {}
            hp = m.u16[hero + 0x84]
            actors_used, rolls = [], []
            inventory = bytes(m[0x0200DF28:0x0200DF28 + 2400])
            expected = [0x710 if failed else 0x2B0]
            def write(address, data):
                overrides.append({'address': address, 'before': bytes(m[address:address + len(data)]).hex(),
                                  'after': data.hex()})
                for i, value in enumerate(data):
                    m.u8[address + i] = value
            def callback(event):
                address, regs = event['address'], event['registers']
                if address == 0x08008F4C and not initial:
                    initial.append(event | {'guard': bytes(m[regs[13]:regs[13] + 32]).hex()})
                    write(hero + 0x60, struct.pack('<I', gold))
                    write(hero + 0xBF, bytes([1 if case == 'transformed' else 0]))
                    if case.startswith(('player-', 'combined-')):
                        name = dict(player_layout_cases())['widest-Japanese' if case.startswith('combined-') else case[7:]]
                        write(HERO, name.ljust(16, b'\0'))
                    actors = [m.u32[0x02001624 + 4 * i] for i in range(1, 56)]
                    actor = next(a for a in actors if 0x02000000 <= a < 0x02040000 and
                                 m.u32[a + 8] & 0x80000000 and m.u16[a + 0x84] > 0)
                    actors_used.append(actor)
                    write(actor + 0x60, struct.pack('<I', 0))
                    overrides.append({'event': event, 'pc_after': 0x0802BCEC, 'r0_after': actor})
                    game.core.cpu.gprs[0] = actor
                    require(game.core._core.writeRegister(game.core._core, b'pc',
                            ffi.new('uint32_t*', 0x0802BCEC)), 'Gold theft entry redirect failed')
                if initial and address in (0x0802BD06, 0x0802BD44, 0x0802BDB0):
                    value = int(case == 'protected') if address == 0x0802BD06 else int(case == 'ability')
                    if address == 0x0802BDB0:
                        value = roll
                        rolls.append(event)
                    overrides.append({'event': event, 'r0_after': value})
                    game.core.cpu.gprs[0] = value
                if initial and address in (0x0802BD1A, 0x0802BD64, 0x0802BDFC):
                    field = next((v for k, v in fields.items() if case == k or case == 'combined-' + k), None)
                    if field:
                        write(0x02008D08, field.ljust(64, b'\0'))
                        overrides.append({'event': event, 'r0_after': 0x02008D08})
                        game.core.cpu.gprs[0] = 0x02008D08
                if initial and address == 0x08000FB8 and regs[1] in direct:
                    row = direct[regs[1]]
                    slot = row['table_offset']
                    capacity = row['capacity']
                    require(slot in expected + [0x2B4] and regs[0] == regs[13] + (0x104 if slot == 0x2B4 else 4),
                            'Gold theft formatter owner differs')
                    args = [regs[2], regs[3], m.u32[regs[13]]]
                    if slot == 0x2B4:
                        require(regs[2] == stolen, 'Gold theft amount differs')
                    if slot == 0x710:
                        require(regs[3] in direct and direct[regs[3]]['table_offset'] == 0x714, 'Gold kind source differs')
                        formats.append({'id': direct[regs[3]]['id'], 'role': 'kind', 'source_pointer': regs[3]})
                    if slot == 0x2B0:
                        require(args[2] == regs[13] + 0x104, 'Gold amount field owner differs')
                    payload = materialize(bytes.fromhex(row['encoded_hex']), args, m)
                    require(len(payload) <= row['maximum_bytes'] <= capacity, 'Gold theft output overflow')
                    pending.append((regs, row, payload, bytes(m[regs[0] + capacity:regs[0] + capacity + 16])))
                if pending and address == (pending[-1][0][14] & ~1):
                    before, row, payload, guard = pending.pop()
                    capacity = row['capacity']
                    require(regs[4:12] == before[4:12] and regs[13] == before[13] and
                            bytes(m[before[0]:before[0] + len(payload)]) == payload and
                            bytes(m[before[0] + capacity:before[0] + capacity + 16]) == guard, 'Gold theft formatter bytes/guard/ABI differ')
                    if row['table_offset'] != 0x2B4:
                        formatted[before[0]] = (row, payload, guard)
                    formats.append({'id': row['id'], 'hex': payload.hex(), 'bytes': len(payload), 'capacity': capacity})
                if initial and address == 0x0801588C and regs[0] in formatted:
                    require(not checks or checks[-1].complete and checks[-1].returned, 'Gold theft queues overlap')
                    row, payload, guard = formatted.pop(regs[0])
                    capacity = 256
                    slots.append(row['table_offset'])
                    require(slots == expected[:len(slots)], 'Gold theft message order differs: ' + repr((case, slots)))
                    checks.append(ActionCheck(game, payload[:-1], regs[14], capacity, guard))
                if initial and address == 0x0802BE48:
                    before = initial[0]
                    require(regs[4:12] == before['registers'][4:12] and regs[13] == before['registers'][13]
                            and regs[0] == before['registers'][14] and
                            bytes(m[regs[13]:regs[13] + 32]).hex() == before['guard'], 'Gold theft caller ABI differs')
                    require(m.u32[hero + 0x60] == gold - stolen and
                            m.u32[actors_used[0] + 0x60] == stolen, 'Native gold transfer differs')
                    returns.append(event | {'gold_before': gold, 'gold_after': m.u32[hero + 0x60],
                                            'stolen': m.u32[actors_used[0] + 0x60]})
                for check in checks:
                    if not (check.complete and check.returned):
                        check.callback(event)
            with Debugger(game, callback, max_events=150000) as debug:
                for address in (0x08008F4C, 0x0802BD06, 0x0802BD44, 0x0802BDB0,
                                0x0802BD1A, 0x0802BD64, 0x0802BDFC, 0x08000FB8,
                                0x0802BD2A, 0x0802BD74, 0x0802BDF6, 0x0802BE18,
                                0x0801588C, 0x080158CE, 0x08001BC4, 0x08001C14, 0x08001C68,
                                0x0802BD32, 0x0802BD7C, 0x0802BE20, 0x0802BE48):
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
                    'Gold theft chain incomplete: ' + repr((case, slots, len(returns))))
            wraps = case in ('maximum-width', 'maximum-bytes', 'player-widest-Japanese') or case.startswith('combined-')
            require(checks[0].queued['one_line'] == (not wraps), 'Gold theft line choice differs')
            require(len(rolls) == (0 if failed else 4), 'Native gold roll count differs')
            require(m.u16[hero + 0x84] == hp and bytes(m[0x0200DF28:0x0200DF28 + 2400]) == inventory
                    and game.snapshot().battery == fixture.battery, 'Gold theft changed HP/items/save')
            results.append({'case': case, 'queue_slots': slots, 'queues': [c.queued for c in checks],
                            'draws': [c.draws for c in checks], 'formats': formats, 'overrides': overrides,
                            'return': returns[0], 'inputs': game.inputs,
                            'images': {p: digest((game.output / p).read_bytes()) for p in images}})
    report = {'passed': True, 'rom_sha256': digest(rom), 'cases': results,
              'scope': 'Controlled native monster gold-theft handler, amount rolls and resistance/transformation. '
                       'Native conserved gold transfer including empty/partial/max8-digit amounts and refusals; '
                       'actor/player fields,256-byte message and64-byte amount guards, ABI and HP/items/save. '
                       'Ordinary AI, resistance acquisition and later recovery of stolen gold remain separate.'}
    (OUT / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print('Gold theft:', len(results), 'cases passed', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cumulative', action='store_true')
    run(parser.parse_args().cumulative)
