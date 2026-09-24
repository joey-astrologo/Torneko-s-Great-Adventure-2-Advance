"""Native stumbling-trap notices, drop/loss outcomes and item-field bounds."""
import argparse
import json
import struct
import mgba.log
from tools.compact_font import encode
from tools.emulator import Debugger, Session, ffi
from tools.rom import ROOT, digest, require, load_base
from tools.stumble_trap_text import add_stumble_trap
from tools.verify_inventory_action_prototype import ActionCheck
from tools.verify_service_ui import materialize

OUT = ROOT / 'build/stumble-trap-prototype'


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
        OUT = ROOT / 'build/english/stumble-trap-validation'
        rom = (ROOT / 'build/english/torneko-2-english.gba').read_bytes()
        build = json.loads((ROOT / 'build/english/build.json').read_text())
        require(digest(rom) == build['output_sha256'], 'Stale cumulative stumble_trap ROM')
    else:
        rom, build = candidate()
    prior = status.OUT
    try:
        status.OUT = OUT
        fixture = status.ready(rom, build)
    finally:
        status.OUT = prior
    direct = {r['offset'] + 0x08000000: r for r in build['stumble_trap']['entries']}
    fields = {'maximum-width': encode('W' * 31), 'maximum-bytes': encode('i' * 31),
              'coloured': b'\x03\x05' + encode('Item')[:-1] + b'\x05\0'}
    results, base = [], load_base()
    for case in ('empty', 'refused', 'protected', 'staff', 'drop', 'placement-full', *fields):
        print('Stumble trap:', case, flush=True)
        failed_placement = case == 'placement-full' or case in fields
        avoided = case in ('refused', 'protected', 'staff')
        with Session(rom, OUT / case) as game:
            game.restore(fixture)
            m = game.core.memory
            hero = m.u32[0x02001624]
            initial, returns, checks, slots, overrides, placements, floors, formats, images = [], [], [], [], [], [], [], [], []
            pending, formatted = [], {}
            hp, gold = m.u16[hero + 0x84], m.u32[hero + 0x60]
            inventory = bytearray(2400)
            ident = 59 if case == 'staff' else 177
            if case != 'empty':
                flags = struct.unpack_from('<I', base, 0x141B9C + ident * 24 + 4)[0]
                struct.pack_into('<I', inventory, 0, 0xC8000000 | flags)
                inventory[4] = inventory[5] = 1
                inventory[8] = bytes(m[0x020013D0:0x020014D0]).index(ident)
            expected = [0x32C] + ([0x330] if case == 'staff' else [0x328] if avoided else
                                  [0x1D0] if failed_placement else [])
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
                    type_address = 0x02003BAC + ident * 20
                    write(type_address, struct.pack('<I', m.u32[type_address] | 0x40000000))
                    overrides.append({'event': event, 'pc_after': 0x08027EC4,
                                      'r0_after': hero, 'r1_after': int(case == 'refused')})
                    game.core.cpu.gprs[0] = hero
                    game.core.cpu.gprs[1] = int(case == 'refused')
                    require(game.core._core.writeRegister(game.core._core, b'pc',
                            ffi.new('uint32_t*', 0x08027EC4)), 'Stumble entry redirect failed')
                if initial and address == 0x08027F1A:
                    flags = (m.u32[regs[0] + 4] & ~8) | (8 if case == 'protected' else 0)
                    write(regs[0] + 4, struct.pack('<I', flags))
                if initial and address == 0x08013F66 and failed_placement:
                    # Select the native exhausted-pool branch before allocation;
                    # overriding success after placement would create a duplicate.
                    overrides.append({'event': event, 'r6_after': 128})
                    game.core.cpu.gprs[6] = 128
                if initial and address == 0x08028274:
                    placements.append(event)
                if initial and address == 0x08028280:
                    pointer = m.u32[regs[0] + 16]
                    floors.append({'address': pointer, 'record_hex': bytes(m[pointer:pointer + 120]).hex()})
                if initial and address == 0x080282D0 and case in fields:
                    write(regs[9], fields[case].ljust(64, b'\0'))
                if initial and address == 0x08000FB8 and regs[1] in direct:
                    row = direct[regs[1]]
                    require(row['table_offset'] == 0x1D0 and regs[14] == 0x080282E3 and
                            regs[0] == regs[8] == regs[13] + 0xCD8 and
                            regs[2] == regs[9] == regs[13] + 0xDD8, 'Stumble formatter layout differs')
                    payload = materialize(bytes.fromhex(row['encoded_hex']), [regs[2]], m)
                    require(len(payload) <= row['maximum_bytes'] <= 256, 'Stumble output overflow')
                    pending.append((regs, row, payload, bytes(m[regs[0] + 256:regs[0] + 272])))
                if pending and address == 0x080282E2:
                    before, row, payload, guard = pending.pop()
                    require(regs[4:12] == before[4:12] and regs[13] == before[13] and
                            bytes(m[before[0]:before[0] + len(payload)]) == payload and
                            bytes(m[before[0] + 256:before[0] + 272]) == guard,
                            'Stumble formatter output/guard/ABI changed')
                    formatted[before[0]] = (row, payload, guard)
                    formats.append({'id': row['id'], 'hex': payload.hex(), 'bytes': len(payload), 'capacity': 256})
                if initial and address == 0x0801588C and (regs[0] in direct or regs[0] in formatted):
                    require(not checks or checks[-1].complete and checks[-1].returned, 'Stumble queues overlap')
                    if regs[0] in direct:
                        row, capacity, guard = direct[regs[0]], None, b''
                        payload = bytes.fromhex(row['encoded_hex'])
                    else:
                        row, payload, guard = formatted.pop(regs[0])
                        capacity = 256
                    slots.append(row['table_offset'])
                    require(slots == expected[:len(slots)], 'Stumble message order differs')
                    checks.append(ActionCheck(game, payload[:-1], regs[14], capacity, guard))
                if initial and address == 0x080283B0:
                    before = initial[0]
                    require(regs[4:12] == before['registers'][4:12] and regs[13] == before['registers'][13]
                            and regs[0] == before['registers'][14] and
                            bytes(m[regs[13]:regs[13] + 32]).hex() == before['guard'], 'Stumble caller ABI changed')
                    returns.append(event | {'inventory_hex': bytes(m[0x0200DF28:0x0200DF28 + 2400]).hex()})
                for check in checks:
                    if not (check.complete and check.returned):
                        check.callback(event)
            with Debugger(game, callback, max_events=150000) as debug:
                for address in (0x08008F4C, 0x08027F1A, 0x08013F66, 0x08028274, 0x08028280,
                                0x080282D0, 0x08000FB8, 0x080282E2, 0x0801588C, 0x080158CE,
                                0x08001BC4, 0x08001C14, 0x08001C68, 0x08027F18, 0x08027FA6,
                                0x080282EA, 0x080283B0):
                    debug.breakpoint(address)
                game.press('A', wait=0)
                captured = 0
                for _ in range(2400):
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
                    'Stumble chain incomplete: ' + repr((case, slots, len(returns))))
            final_items = bytes.fromhex(returns[0]['inventory_hex'])
            count = sum(bool(struct.unpack_from('<I', final_items, i * 120)[0] & 0x80000000) for i in range(20))
            require(count == int(avoided) and len(placements) == int(case == 'drop' or failed_placement)
                    and len(floors) == int(case == 'drop'), 'Stumble item/drop count differs: ' + case)
            if avoided:
                require(final_items == inventory, 'Avoided stumble changed inventory')
            if case == 'drop':
                record = bytes.fromhex(floors[0]['record_hex'])
                require(record[4:120] == inventory[4:120] and placements[0]['registers'][0] == 1,
                        'Successful stumble changed dropped item identity/amount')
            if failed_placement:
                require(placements[0]['registers'][0] == 0, 'Exhausted placement succeeded')
            require(all(c.queued['one_line'] == (i == 0 or case not in ('maximum-width', 'maximum-bytes'))
                        for i, c in enumerate(checks)), 'Stumble conditional line choice differs')
            require(m.u16[hero + 0x84] == hp and m.u32[hero + 0x60] == gold and
                    game.snapshot().battery == fixture.battery, 'Stumble changed HP/gold/save')
            results.append({'case': case, 'queue_slots': slots, 'queues': [c.queued for c in checks],
                            'draws': [c.draws for c in checks], 'formats': formats, 'overrides': overrides,
                            'placements': placements, 'floors': floors, 'return': returns[0],
                            'inputs': game.inputs, 'images': {p: digest((game.output / p).read_bytes()) for p in images}})
    report = {'passed': True, 'rom_sha256': digest(rom), 'cases': results,
              'scope': 'Controlled native stumbling-trap entry, activation/protection, inventory and exhausted '
                       'floor-pool selection before allocation. Empty, evaded, staff-protected, actual floor drop '
                       'and native item-loss outcomes; complete notices, item-field width/byte/colour bounds, '
                       'formatter/caller ABI and HP/gold/save preservation. Ordinary terrain/discovery, '
                       'full inventory arrangements and pot-breaking/contents remain separate.'}
    (OUT / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print('Stumble trap:', len(results), 'cases passed', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cumulative', action='store_true')
    run(parser.parse_args().cumulative)
