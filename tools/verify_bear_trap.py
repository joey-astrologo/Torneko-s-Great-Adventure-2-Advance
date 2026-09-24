"""Native bear-trap activation, evasion and both grab-release types."""
import argparse
import json
import struct
import mgba.log

from tools.bear_trap_text import add_bear_trap
from tools.compact_font import encode
from tools.emulator import Debugger, Session, ffi
from tools.rom import ROOT, digest, require
from tools.verify_inventory_action_prototype import ActionCheck
from tools.verify_service_ui import materialize

OUT = ROOT / 'build/bear-trap-prototype'


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
        OUT = ROOT / 'build/english/bear-trap-validation'
        rom = (ROOT / 'build/english/torneko-2-english.gba').read_bytes()
        build = json.loads((ROOT / 'build/english/build.json').read_text())
        require(digest(rom) == build['output_sha256'], 'Stale cumulative bear_trap ROM')
    else:
        rom, build = candidate()
    prior = status.OUT
    try:
        status.OUT = OUT
        fixture = status.ready(rom, build)
    finally:
        status.OUT = prior
    direct = {r['offset'] + 0x08000000: r for r in build['bear_trap']['entries']}
    fields = {'maximum-width': encode('W' * 31), 'maximum-bytes': encode('i' * 31),
              'coloured': b'\x03\x05' + encode('Monster')[:-1] + b'\x05\0'}
    results = []
    for case in ('activated', 'refused', 'grab-six', 'grab-seven', *fields):
        print('Bear trap:', case, flush=True)
        grabbing = case not in ('activated', 'refused')
        with Session(rom, OUT / case) as game:
            game.restore(fixture)
            m = game.core.memory
            hero = m.u32[0x02001624]
            initial, returns, checks, slots, overrides, releases, formats, images = [], [], [], [], [], [], [], []
            pending, formatted = [], {}
            targets, latch_writes = [], []
            hp, gold = m.u16[hero + 0x84], m.u32[hero + 0x60]
            inventory = bytes(m[0x0200DF28:0x0200DF28 + 2400])
            expected = [0x2DC, 0x2E8] if case == 'refused' else [0x2DC] + ([0x978] if grabbing else [])
            def write(address, data):
                overrides.append({'address': address, 'before': bytes(m[address:address + len(data)]).hex(),
                                  'after': data.hex()})
                for i, value in enumerate(data):
                    m.u8[address + i] = value
            def callback(event):
                address, regs = event['address'], event['registers']
                if initial and event['kind'] == 'watchpoint' and address == 0x02003B8F:
                    latch_writes.append(event)
                if address == 0x08008F4C and not initial:
                    initial.append(event | {'guard': bytes(m[regs[13]:regs[13] + 32]).hex()})
                    write(hero + 0xA3, b'\0')
                    for i in range(1, 56):
                        actor = m.u32[0x02001624 + 4 * i]
                        require(0x02000000 <= actor < 0x02040000, 'Actor pointer outside EWRAM')
                        flags = m.u32[actor + 8]
                        if flags & 0x80000000 and m.u16[actor + 0x84] > 0:
                            if flags & 0x40:
                                write(actor + 8, struct.pack('<I', flags & ~0x40))
                            if grabbing and not targets:
                                targets.append(actor)
                                write(actor + 8, struct.pack('<I', flags | 0x40))
                                write(actor + 0x91, bytes([7 if case == 'grab-seven' else 6]))
                                write(hero + 0xA3, bytes([98 if case == 'grab-seven' else 99]))
                    require(bool(targets) == grabbing, 'Fixture lacks a live grabbing target')
                    write(0x02003B8F, b'\x04')
                    overrides.append({'event': event, 'pc_after': 0x080275B8,
                                      'r0_after': hero, 'r1_after': int(case == 'refused')})
                    game.core.cpu.gprs[0] = hero
                    game.core.cpu.gprs[1] = int(case == 'refused')
                    require(game.core._core.writeRegister(game.core._core, b'pc',
                            ffi.new('uint32_t*', 0x080275B8)), 'Bear trap entry redirect failed')
                if initial and address == 0x08012050:
                    require(targets and regs[0] == targets[0], 'Unexpected grab-release target')
                    releases.append(event)
                if initial and address == 0x0802763E and case in fields:
                    # A plain actor name can be a ROM pointer. Use the already
                    # established 64-byte actor-name scratch for stress fields.
                    write(0x02008D08, fields[case].ljust(64, b'\0'))
                    overrides.append({'event': event, 'r0_after': 0x02008D08})
                    game.core.cpu.gprs[0] = 0x02008D08
                if initial and address == 0x08000FB8 and regs[1] in direct:
                    row = direct[regs[1]]
                    require(row['table_offset'] == 0x978 and regs[0] == regs[13] and
                            regs[14] == 0x08027649, 'Bear formatter owner changed')
                    payload = materialize(bytes.fromhex(row['encoded_hex']), [regs[2]], m)
                    require(len(payload) <= row['maximum_bytes'] <= 256, 'Bear formatter overflow')
                    pending.append((regs, row, payload, bytes(m[regs[0] + 256:regs[0] + 272])))
                if pending and address == 0x08027648:
                    before, row, payload, guard = pending.pop()
                    require(regs[4:12] == before[4:12] and regs[13] == before[13] and
                            bytes(m[before[0]:before[0] + len(payload)]) == payload and
                            bytes(m[before[0] + 256:before[0] + 272]) == guard,
                            'Bear formatter output/guard/ABI changed')
                    formatted[before[0]] = (row, payload, guard)
                    formats.append({'id': row['id'], 'hex': payload.hex(), 'bytes': len(payload), 'capacity': 256})
                if initial and address == 0x0801588C and (regs[0] in direct or regs[0] in formatted):
                    require(not checks or checks[-1].complete and checks[-1].returned, 'Bear messages overlap')
                    if regs[0] in direct:
                        row, capacity, guard = direct[regs[0]], None, b''
                        payload = bytes.fromhex(row['encoded_hex'])
                    else:
                        row, payload, guard = formatted.pop(regs[0])
                        capacity = 256
                    slots.append(row['table_offset'])
                    require(slots == expected[:len(slots)], 'Bear message order differs')
                    checks.append(ActionCheck(game, payload[:-1], regs[14], capacity, guard))
                if initial and address == 0x08027670:
                    before = initial[0]
                    require(regs[4:12] == before['registers'][4:12] and regs[13] == before['registers'][13]
                            and regs[0] == before['registers'][14] and
                            bytes(m[regs[13]:regs[13] + 32]).hex() == before['guard'], 'Bear caller ABI changed')
                    returns.append({'event': event, 'timer': m.u8[hero + 0xA3],
                                    'latch': m.u8[0x02003B8F],
                                    'grab_flags': [m.u32[a + 8] for a in targets]})
                for check in checks:
                    if not (check.complete and check.returned):
                        check.callback(event)
            with Debugger(game, callback, max_events=150000) as debug:
                debug.watchpoint(0x02003B8F, 'write')
                for address in (0x08008F4C, 0x08012050, 0x0802763E, 0x08000FB8, 0x08027648,
                                0x0801588C, 0x080158CE, 0x08001BC4, 0x08001C14, 0x08001C68,
                                0x080275D4, 0x080275EC, 0x08027650, 0x08027670):
                    debug.breakpoint(address)
                game.press('A', wait=0)
                captured = 0
                for _ in range(1800):
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
                    'Bear trap chain incomplete: ' + case)
            require(len(releases) == int(grabbing) and not any(f & 0x40 for f in returns[0]['grab_flags']),
                    'Native grab release failed')
            require(returns[0]['timer'] == (0 if case == 'refused' else 6) and
                    returns[0]['latch'] == 0 and latch_writes,
                    'Native trap timer/latch changed: ' + repr((case, returns[0])))
            require(all(c.queued['one_line'] == (case != 'maximum-width' or i == 0)
                        for i, c in enumerate(checks)), 'Bear conditional wrapping differs')
            require(m.u16[hero + 0x84] == hp and m.u32[hero + 0x60] == gold and
                    bytes(m[0x0200DF28:0x0200DF28 + 2400]) == inventory and
                    game.snapshot().battery == fixture.battery, 'Bear trap changed HP/gold/items/save')
            results.append({'case': case, 'queue_slots': slots, 'queues': [c.queued for c in checks],
                            'draws': [c.draws for c in checks], 'formats': formats, 'overrides': overrides,
                            'releases': releases, 'latch_writes': latch_writes,
                            'return': returns[0], 'inputs': game.inputs,
                            'images': {p: digest((game.output / p).read_bytes()) for p in images}})
    report = {'passed': True, 'rom_sha256': digest(rom), 'cases': results,
              'scope': 'Controlled bear-trap entry/evasion and existing live actors configured as two native '
                       'grab types. Native release clears holding flags, then sets the trap timer to6 and '
                       'clears the latch. Static and formatted notices retain full meaning, conditional '
                       'one-line rendering, 64-byte field/256-byte output bounds, colours, ABI and save. '
                       'Ordinary trap/grab acquisition and later turn-by-turn recovery remain separate.'}
    (OUT / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print('Bear trap:', len(results), 'cases passed', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cumulative', action='store_true')
    run(parser.parse_args().cumulative)
