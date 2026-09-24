"""Native monster curse priority, resistance, one-item effects and actor names."""
import argparse
import json
import struct
import mgba.log
from tools.compact_font import encode
from tools.curse_text import add_curse
from tools.emulator import Debugger, Session, ffi
from tools.rom import ROOT, digest, load_base, require
from tools.verify_inventory_action_prototype import ActionCheck
from tools.verify_service_ui import materialize

OUT = ROOT / 'build/curse-prototype'


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
        OUT = ROOT / 'build/english/curse-validation'
        rom = (ROOT / 'build/english/torneko-2-english.gba').read_bytes()
        build = json.loads((ROOT / 'build/english/build.json').read_text())
        require(digest(rom) == build['output_sha256'], 'Stale cumulative curse ROM')
    else:
        rom, build = candidate()
    prior = status.OUT
    try:
        status.OUT = OUT
        fixture = status.ready(rom, build)
    finally:
        status.OUT = prior
    direct = {r['offset'] + 0x08000000: r for r in build['curse']['entries']}
    notices = {r['source']['offset'] + 0x08000000: r for r in build['combat']['queue_notices']['entries']}
    fields = {'maximum-width': encode('W' * 31), 'maximum-bytes': encode('i' * 31),
              'coloured': b'\x03\x05' + encode('Monster')[:-1] + b'\x05\0'}
    configs = [('shield', [(31, True, False)], 0x264, 0),
               ('weapon', [(1, True, False)], 0x268, 0),
               ('ring', [(88, True, False)], 0x26C, 0),
               ('priority', [(1, True, False), (88, True, False), (31, True, False)], 0x264, 2),
               ('carried', [(1, False, False), (31, False, False)], 0x270, 0),
               ('empty', [], 0xC8, None), ('already-cursed', [(31, True, True)], 0xC8, None),
               ('curseproof-ring', [(31, True, False), (93, True, False)], 0x278, None),
               ('protected', [(31, True, False)], 0x278, None),
               ('ability', [(31, True, False)], 0x278, None)]
    configs += [(name, [(31, True, False)], 0x264, 0) for name in fields]
    results, base = [], load_base()
    for case, items, notice, cursed_index in configs:
        print('Curse:', case, flush=True)
        with Session(rom, OUT / case) as game:
            game.restore(fixture)
            m = game.core.memory
            hero = m.u32[0x02001624]
            initial, returns, checks, slots, overrides, formats, images, ring_reads = [], [], [], [], [], [], [], []
            pending, formatted = [], {}
            hp, gold = m.u16[hero + 0x84], m.u32[hero + 0x60]
            inventory = bytearray(2400)
            mapping = bytes(m[0x020013D0:0x020014D0])
            for i, (ident, equipped, cursed) in enumerate(items):
                properties = struct.unpack_from('<I', base, 0x141B9C + ident * 24 + 4)[0]
                struct.pack_into('<I', inventory, i * 120,
                                 0xC8000000 | properties | (0x800000 if equipped else 0) |
                                 (0x4000000 if cursed else 0))
                inventory[i * 120 + 4] = inventory[i * 120 + 5] = 1
                inventory[i * 120 + 8] = mapping.index(ident)
            after = bytearray(inventory)
            if cursed_index is not None:
                offset = cursed_index * 120
                struct.pack_into('<I', after, offset, struct.unpack_from('<I', after, offset)[0] | 0x4000000)
            expected = [0x274, notice]
            def write(address, data):
                overrides.append({'address': address, 'before': bytes(m[address:address + len(data)]).hex(),
                                  'after': data.hex()})
                for i, value in enumerate(data):
                    m.u8[address + i] = value
            def callback(event):
                address, regs = event['address'], event['registers']
                if address == 0x08008F4C and not initial:
                    initial.append(event | {'guard': bytes(m[regs[13]:regs[13] + 32]).hex()})
                    write(0x0200DF28, inventory)
                    actors = [m.u32[0x02001624 + 4 * i] for i in range(1, 56)]
                    actor = next(a for a in actors if 0x02000000 <= a < 0x02040000 and
                                 m.u32[a + 8] & 0x80000000 and m.u16[a + 0x84] > 0)
                    overrides.append({'event': event, 'pc_after': 0x0802B918, 'r0_after': actor})
                    game.core.cpu.gprs[0] = actor
                    require(game.core._core.writeRegister(game.core._core, b'pc',
                            ffi.new('uint32_t*', 0x0802B918)), 'Curse entry redirect failed')
                if initial and address == 0x0802B92A and case in fields:
                    write(0x02008D08, fields[case].ljust(64, b'\0'))
                    overrides.append({'event': event, 'r0_after': 0x02008D08})
                    game.core.cpu.gprs[0] = 0x02008D08
                if initial and address == 0x0802B940:
                    ring_reads.append(event)
                    require((regs[0] == 93) == (case == 'curseproof-ring'), 'Native curseproof ring result differs')
                if initial and address == 0x0802B946:
                    write(regs[0], struct.pack('<I', (m.u32[regs[0]] & ~0x4000) |
                                              (0x4000 if case == 'protected' else 0)))
                if initial and address == 0x0802B978:
                    overrides.append({'event': event, 'r0_after': int(case == 'ability')})
                    game.core.cpu.gprs[0] = int(case == 'ability')
                if initial and address == 0x08000FB8 and regs[1] in direct:
                    row = direct[regs[1]]
                    require(row['table_offset'] == 0x274 and regs[0] == regs[13] and
                            regs[14] == 0x0802B935, 'Curse formatter owner differs')
                    payload = materialize(bytes.fromhex(row['encoded_hex']), [regs[2]], m)
                    require(len(payload) <= row['maximum_bytes'] <= 256, 'Curse output overflow')
                    pending.append((regs, row, payload, bytes(m[regs[0] + 256:regs[0] + 272])))
                if pending and address == 0x0802B934:
                    before, row, payload, guard = pending.pop()
                    require(regs[4:12] == before[4:12] and regs[13] == before[13] and
                            bytes(m[before[0]:before[0] + len(payload)]) == payload and
                            bytes(m[before[0] + 256:before[0] + 272]) == guard, 'Curse formatter bytes/guard/ABI differ')
                    formatted[before[0]] = (row, payload, guard)
                    formats.append({'id': row['id'], 'hex': payload.hex(), 'bytes': len(payload), 'capacity': 256})
                if initial and address == 0x0801588C and (regs[0] in direct or regs[0] in notices or regs[0] in formatted):
                    require(not checks or checks[-1].complete and checks[-1].returned, 'Curse queues overlap')
                    if regs[0] in formatted:
                        row, payload, guard = formatted.pop(regs[0])
                        capacity = 256
                    else:
                        row = direct.get(regs[0], notices.get(regs[0]))
                        payload, capacity, guard = bytes.fromhex(row['encoded_hex']), None, b''
                    slots.append(row['table_offset'])
                    require(slots == expected[:len(slots)], 'Curse message order differs: ' + repr((case, slots)))
                    checks.append(ActionCheck(game, payload[:-1], regs[14], capacity, guard))
                if initial and address == 0x0802BA32:
                    before = initial[0]
                    require(regs[4:12] == before['registers'][4:12] and regs[13] == before['registers'][13]
                            and regs[0] == before['registers'][14] and
                            bytes(m[regs[13]:regs[13] + 32]).hex() == before['guard'], 'Curse caller ABI differs')
                    returns.append(event | {'inventory_hex': bytes(m[0x0200DF28:0x0200DF28 + 2400]).hex()})
                for check in checks:
                    if not (check.complete and check.returned):
                        check.callback(event)
            with Debugger(game, callback, max_events=150000) as debug:
                for address in (0x08008F4C, 0x0802B92A, 0x0802B940, 0x0802B946, 0x0802B978,
                                0x08000FB8, 0x0802B934, 0x0801588C, 0x080158CE, 0x08001BC4,
                                0x08001C14, 0x08001C68, 0x0802B93C, 0x0802B902, 0x0802B98A,
                                0x0802BA10, 0x0802BA2C, 0x0802BA32):
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
            require(len(initial) == len(returns) == len(ring_reads) == 1 and slots == expected and
                    all(c.complete and c.returned for c in checks) and not pending and not formatted,
                    'Curse chain incomplete: ' + repr((case, slots, len(returns))))
            require(bytes.fromhex(returns[0]['inventory_hex']) == after, 'Curse changed wrong item(s): ' + case)
            require(all(c.queued['one_line'] == (case != 'maximum-width' or i != 0)
                        for i, c in enumerate(checks)), 'Curse conditional line choice differs')
            require(m.u16[hero + 0x84] == hp and m.u32[hero + 0x60] == gold and
                    game.snapshot().battery == fixture.battery, 'Curse changed HP/gold/save')
            results.append({'case': case, 'queue_slots': slots, 'queues': [c.queued for c in checks],
                            'draws': [c.draws for c in checks], 'formats': formats, 'overrides': overrides,
                            'native_ring_reads': ring_reads, 'return': returns[0],
                            'inputs': game.inputs, 'images': {p: digest((game.output / p).read_bytes()) for p in images}})
    report = {'passed': True, 'rom_sha256': digest(rom), 'cases': results,
              'scope': 'Controlled monster curse handler, equipment/inventory and protection/ability branches. '
                       'Native Curseproof ring lookup, shield/weapon/ring priority and exactly one eligible '
                       'carried-item curse are checked; empty/already-cursed/resistance preserve inventory. '
                       'Complete one-line or bounded conditional notices, native pixels, 64-byte actor field, '
                       '256-byte output, ABI and HP/gold/save preservation. Ordinary monster AI, resistance '
                       'acquisition and other curse consumers remain separate.'}
    (OUT / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print('Curse:', len(results), 'cases passed', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cumulative', action='store_true')
    run(parser.parse_args().cumulative)
