"""Native unknown-name branches and full combat callers on disposable cartridges."""

import argparse
import json
import struct
from pathlib import Path

import mgba.log

from tools.actor_fallback_text import READERS, SLOT
from tools.audit_dungeon_screens import AuditedSession
from tools.compact_font import encode
from tools.dialogue_checks import rendered_codes
from tools.emulator import Debugger, Session, ffi
from tools.name_entry import HERO
from tools.rom import ROOT, default_rom, digest, require
from tools.screen_text_audit import ScreenTextAudit
from tools.verify_service_ui import cstring
from tools import verify_player_status_prototype as status

BASE = 0x08000000
GETTER = BASE+0x9ACC


def prepare(game, kind, level=1, species=1):
    m = game.core.memory
    hero = m.u32[0x02001624]
    actor = next(m.u32[0x02001624+4*i] for i in range(1, 56)
                 if 0x02000000 <= m.u32[0x02001624+4*i] < 0x0203FF00
                 and m.u32[m.u32[0x02001624+4*i]+8] & 0x80000000
                 and m.u16[m.u32[0x02001624+4*i]+0x84] > 0)
    writes = []

    def write(at, raw, why):
        writes.append(dict(address=at, before=bytes(m[at:at+len(raw)]).hex(),
                           after=raw.hex(), reason=why))
        for i, v in enumerate(raw):
            m.u8[at+i] = v

    write(HERO, encode('Torneko').ljust(16, b'\0'), 'English player name in disposable RAM')
    write(actor+8, struct.pack('<I', 0x80000000), 'Ordinary active monster flags')
    write(actor+0x91, bytes([species]), 'Controlled native species')
    write(actor+0x88, struct.pack('<h', level), 'Controlled native level')
    write(actor+0x94, bytes(0x2C), 'Clear monster name/status aliases')
    write(hero+0x94, bytes(0x2C), 'Clear player name/status aliases')
    write(hero+8, struct.pack('<I', m.u32[hero+8] & ~0x10100000),
          'Clear see-invisible and resistance flags')
    write(0x020081D4, struct.pack('<I', m.u32[0x020081D4] & ~0x520000),
          'Clear global visibility/resistance aliases')
    flag = m.u32[0x020129D8]+28*species+0x13
    write(flag, bytes([kind == 'unknown-species']), 'Native species name-concealment branch')
    if 'invisible' in kind:
        write(actor+0xBE, b'\x32', 'Native monster invisibility timer')
    if 'see-invisible' in kind:
        write(hero+8, struct.pack('<I', m.u32[hero+8] | 0x100000), 'Native see-invisible flag')
    if 'hallucination' in kind and kind != 'hallucination-trap':
        write(hero+0x96, b'\x32', 'Native player hallucination timer')
    if kind == 'blind':
        write(hero+0x98, b'\x32', 'Native player blindness timer')
    return hero, actor, writes, write


def getter(game, actor):
    snapshot = game.snapshot()
    m, cpu = game.core.memory, game.core.cpu
    regs = [int(cpu.gprs[i]) & 0xFFFFFFFF for i in range(16)]
    guard = bytes(m[0x02008D48:0x02008D68])
    actor_before = bytes(m[actor:actor+0xC4])
    branches, returned = [], []
    cpu.gprs[0], cpu.gprs[14] = actor, 0x08000355
    for register, value in ((b'cpsr', int(cpu.cpsr.packed) | 0x20), (b'pc', GETTER)):
        require(game.core._core.writeRegister(game.core._core, register, ffi.new('uint32_t*', value)),
                'Could not enter native actor getter')

    def callback(e):
        if e['address'] == 0x08000354:
            r = e['registers']
            require(r[4:12] == regs[4:12] and r[13] == regs[13], 'Getter ABI differs')
            require(bytes(m[0x02008D48:0x02008D68]) == guard
                    and bytes(m[actor:actor+0xC4]) == actor_before, 'Getter changed actor or scratch guard')
            returned.append(dict(pointer=r[0], raw_hex=(cstring(m, r[0])+b'\0').hex()))
        else:
            branches.append(e['address'])
    try:
        with Debugger(game, callback, max_events=100) as debug:
            for a in (0x08009B3E, 0x08009B6E, 0x08000354):
                debug.breakpoint(a)
            debug.run_until(lambda _: bool(returned))
        return returned[0] | dict(branches=branches, abi_actor_and_guard_preserved=True)
    finally:
        game.restore(snapshot)


def invoke(game, entry, arguments, exit_address, exit_register, writes, audit, stack_args=()):
    """Enter a complete handler at the normal action dispatcher and keep its return."""
    entered, returned, names, pending, stack = [], [], [], [], []
    m, cpu = game.core.memory, game.core.cpu

    def callback(e):
        a, r = e['address'], e['registers']
        audit.callback(e)
        if a == 0x08008F4C and not entered:
            entered.append(e)
            for i, v in enumerate(arguments):
                cpu.gprs[i] = v
            for i, v in enumerate(stack_args):
                at = r[13]+4*i
                stack.append((at, bytes(m[at:at+4])))
                m.u32[at] = v
            writes.append(dict(event=e, controlled_entry=entry, arguments=arguments,
                               stack_arguments=list(stack_args), stack_restored_at_return=True))
            require(game.core._core.writeRegister(game.core._core, b'pc', ffi.new('uint32_t*', entry)),
                    'Could not enter native combat/trap handler')
        if a == GETTER and entered and not returned:
            pending.append(r[0])
        if a == 0x08009BFC and pending:
            actor = pending.pop()
            names.append(dict(actor=actor, pointer=r[0], raw_hex=(cstring(m, r[0])+b'\0').hex()))
        if a == exit_address and entered and not returned and r[exit_register] == entered[0]['registers'][14]:
            before = entered[0]['registers']
            require(r[4:12] == before[4:12] and r[13] == before[13], 'Native handler ABI differs')
            for at, raw in stack:
                for i, v in enumerate(raw):
                    m.u8[at+i] = v
            returned.append(e)

    with Debugger(game, callback, max_events=200000) as debug:
        for a in set(audit.ADDRESSES) | {0x08008F4C, GETTER, 0x08009BFC, exit_address}:
            debug.breakpoint(a)
        game.press('A', hold=1, wait=0)
        for _ in range(900):
            if returned and audit.glyphs and game.core.frame_counter > audit.glyphs[-1]['frame']+4:
                break
            game.frames(1)
    require(len(entered) == len(returned) == 1,
            f'Native handler {entry:08x}: entries={len(entered)}, returns={len(returned)}')
    return dict(entry=entry, names=names, abi_preserved=True)


def run(source, output=None, expect_japanese=False):
    mgba.log.silence()
    output = output or source/'actor-fallback-validation'
    rom = (source/'torneko-2-english.gba').read_bytes()
    build = json.loads((source/'build.json').read_text())
    require(digest(rom) == build['output_sha256'], 'Actor fallback ROM/ledger differs')
    protected = {str(p): digest(p.read_bytes()) for p in (default_rom(), default_rom().with_suffix('.sav'))}
    prior = status.OUT
    try:
        status.OUT = output
        fixture = status.ready(rom, build)
    finally:
        status.OUT = prior
    unknown = bytes.fromhex('89bd8ed282a900') if expect_japanese else encode('Someone')
    if not expect_japanese:
        for _, literal, _ in READERS:
            table = struct.unpack_from('<I', rom, literal)[0]-BASE
            pointer = struct.unpack_from('<I', rom, table+SLOT)[0]
            require(pointer == build['actor_fallback']['name_offset']+BASE
                    and rom[pointer-BASE:pointer-BASE+len(unknown)] == unknown, 'Fallback binding differs')
    cases = []
    specs = [(kind, 1, 1) for kind in ('visible', 'hallucination', 'blind', 'invisible',
        'invisible-hallucination', 'see-invisible', 'see-invisible-hallucination', 'unknown-species')]
    specs += [('visible', 32767, 99), ('hallucination', 32767, 99)]
    for kind, level, species in specs:
        with Session(rom, output/f'getter-{kind}-{level}') as game:
            game.restore(fixture)
            hero, actor, writes, write = prepare(game, kind, level, species)
            row = build['monsters']['entries'][species]
            normal = (encode(row['english']+' Lv')[:-1]+str(level).encode()+b'\0'
                      if level > 1 else encode(row['english']))
            expected = normal if kind in ('visible', 'see-invisible') else unknown
            result = getter(game, actor)
            require(result['raw_hex'] == expected.hex(), 'Native getter returned the wrong name: '+kind)
            branch = [] if expected == normal else [0x08009B3E if kind.startswith('invisible') else 0x08009B6E]
            require(result['branches'] == branch, 'Unexpected unknown-name branch: '+kind)
            write(hero+0x96, b'\0', 'Controlled condition removal')
            write(hero+0x98, b'\0', 'Controlled condition removal')
            write(actor+0xBE, b'\0', 'Controlled invisibility removal')
            write(game.core.memory.u32[0x020129D8]+28*species+0x13, b'\0', 'Restore known species')
            restored = getter(game, actor)
            require(restored['raw_hex'] == normal.hex() and not restored['branches'], 'Normal name did not return')
            require(game.snapshot().battery == fixture.battery, 'Getter wrote battery save')
            cases.append(dict(case=f'{kind}-{level}', overrides=writes, getter=result,
                              after_condition_removal=restored, inputs=game.inputs))
    combat = []
    for kind in ('visible', 'hallucination', 'invisible', 'blind'):
        for direction in ('outgoing', 'incoming'):
            print('Actor fallback:', kind, direction, flush=True)
            with AuditedSession(rom, output/f'{kind}-{direction}') as game:
                game.restore(fixture)
                hero, actor, writes, write = prepare(game, kind)
                m = game.core.memory
                # Real records and native attack logic; controls supply scene access only.
                for who in (hero, actor):
                    write(who+0x84, struct.pack('<HH', 999, 999), 'Survive this controlled non-death combat case')
                x, y = m.u16[hero+0x66], m.u16[hero+0x68]
                write(actor+0x66, struct.pack('<HH', x+1, y), 'Adjacent actor for controlled melee scene')
                write(actor+0x10, struct.pack('<II', (x+1)*32, y*32), 'Matching native render coordinates')
                audit = ScreenTextAudit(game)
                game.audit, game.images = audit, []
                expected = bytes.fromhex(build['monsters']['entries'][1]['encoded_hex']) if kind == 'visible' else unknown
                start_queue = len(audit.final_queues)
                arguments = [hero, actor, 1, 0] if direction == 'outgoing' else [actor, hero, 1, 0]
                result = invoke(game, 0x0800BCBC, arguments, 0x0800CC94, 1, writes, audit, (0, 1))
                require(any(n['actor'] == actor and n['raw_hex'] == expected.hex() for n in result['names']),
                        'Combat did not consume the native expected actor name')
                queues = audit.final_queues[start_queue:]
                require(any(expected[:-1] in bytes.fromhex(q['raw_hex']) for q in queues),
                        'Expected actor name did not reach the actual combat log')
                name_codes = rendered_codes(expected)
                require(any(any(q['drawn_codes'][i:i+len(name_codes)] == name_codes
                                for i in range(len(q['drawn_codes'])-len(name_codes)+1))
                            for q in queues), 'Expected actor name was queued but not drawn')
                require(not audit.unreadable and not audit.layout_violations, 'Combat stream/layout finding')
                require(not audit.unclassified if not expect_japanese or kind == 'visible' else bool(audit.unclassified),
                        'Unexpected language result in native glyphs')
                require(game.snapshot().battery == fixture.battery, 'Combat wrote battery save')
                game.capture('combat')
                combat.append(dict(case=kind+'-'+direction, overrides=writes, attack=result,
                    audit=audit.report(), inputs=game.inputs, battery_preserved=True,
                    outcome=dict(hero_hp=m.u16[hero+0x84], actor_hp=m.u16[actor+0x84],
                                 hero_sha256=digest(bytes(m[hero:hero+0xC4])),
                                 actor_sha256=digest(bytes(m[actor:actor+0xC4])),
                                 inventory_sha256=digest(bytes(m[0x0200DF28:0x0200E888]))),
                    images=game.images,
                    image_sha256=digest((game.output/'combat.png').read_bytes())))
    with Session(rom, output/'hallucination-trap') as game:
        game.restore(fixture)
        hero, actor, writes, write = prepare(game, 'visible')
        audit = ScreenTextAudit(game)
        result = invoke(game, 0x08027A8C, [hero, 0], 0x08027B02, 0, writes, audit)
        timer = game.core.memory.u8[hero+0x96]
        name = getter(game, actor)
        require(timer == 50 and name['raw_hex'] == unknown.hex(),
                'Real hallucination trap did not select the expected name')
        require(not audit.unreadable and not audit.unclassified and not audit.layout_violations,
                'Hallucination trap message finding')
        require(game.snapshot().battery == fixture.battery, 'Trap wrote battery save')
        game.capture('trap')
        trap = dict(overrides=writes, handler=result, timer=timer, getter=name,
                    audit=audit.report(), inputs=game.inputs,
                    image_sha256=digest((game.output/'trap.png').read_bytes()))
    require(all(digest(Path(p).read_bytes()) == h for p, h in protected.items()), 'Supplied ROM/save changed')
    report = dict(passed=True, rom_sha256=digest(rom), negative_control=expect_japanese,
        fixture_state_sha256=digest(fixture.state), fixture_battery_sha256=digest(fixture.battery),
        protected_files=protected, getters=cases, combat=combat, trap=trap,
        scope='Controlled native getter/state cases, recovery, and full outgoing/incoming combat owners. '
              'A separate real hallucination-trap handler case checks timer50 and the resulting name. Scene access, names, positions, '
              'non-death HP and status fields are controlled and recorded; no function result or text '
              'argument is substituted. Exact names, original return paths, complete glyph/language/layout '
              'audit and source/save preservation. Ordinary trap placement and natural invisible-monster '
              'acquisition are not claimed; other name aliases remain separate.')
    (output/'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
    print('Actor fallback:', len(cases), 'getter cases and', len(combat), 'combat cases passed')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=ROOT/'build/english')
    parser.add_argument('--output', type=Path)
    parser.add_argument('--expect-japanese', action='store_true')
    args = parser.parse_args()
    run(args.source, args.output, args.expect_japanese)
