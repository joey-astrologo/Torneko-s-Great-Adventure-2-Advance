"""Controlled native proof of reader control 7F, without insertion changes."""
import json
import mgba.log
from tools import dialogue_checks
from tools.audit_menu_layouts import Observer
from tools.build_english import build_rom
from tools.compact_font import encode
from tools.emulator import Session, Snapshot, Debugger
from tools.name_entry import HERO
from tools.opening_text import BANK_RAM, banks
from tools.rom import ROOT, digest, require

OUT = ROOT / 'build/player-initial-prototype'


def run():
    mgba.log.silence()
    rom, _ = build_rom()
    village = Snapshot.load(ROOT / 'build/english/home-validation/village')
    require(village.rom_sha256 == digest(rom), 'Village fixture is stale')
    entry = OUT / 'native/reader-entry'
    reached = []
    with Session(rom, OUT / 'native') as game:
        game.restore(village)
        def capture(event):
            if not reached:
                game.snapshot().save(entry)
                reached.append(event)
        with Debugger(game, capture, max_events=1000) as debug:
            debug.breakpoint(0x080022C4)
            game.press('LEFT', hold=16, wait=120)
            game.press('A', wait=120)
        require(reached, 'Ordinary village approach did not reach a reader')
        (OUT / 'native/provenance.json').write_text(json.dumps({
            'source_fixture_sha256': digest(village.state), 'events': reached,
            'inputs': game.inputs, 'scope': 'Ordinary village approach to Ed; no state overrides.'}, indent=2) + '\n')
    fixture = Snapshot.load(entry)
    # This untranslated bank-one source is already owned by the event bank.
    # Replace its beginning only in disposable RAM, at a paused reader call.
    start = 0x0A5B
    original = banks()[1]['data'][start:0x0B19]
    target = BANK_RAM + start
    payload = b'\x14\x7f' + encode('-')[:-1] + b'\x7e' + encode('!')
    require(len(payload) <= len(original), 'Probe exceeds existing source span')
    results = []
    cases = dialogue_checks.player_layout_cases() + [('one-letter', encode('T'))]
    for label, name in cases:
        with Session(rom, OUT / label) as game:
            game.restore(fixture)
            memory = game.core.memory
            require(bytes(memory[target:target + len(original)]) == original,
                    'Probe source is not the expected original bank-one text')
            guard = bytes(memory[target - 16:target]), bytes(memory[target + len(original):target + len(original) + 16])
            for index, value in enumerate(payload):
                memory.u8[target + index] = value
            for index, value in enumerate(name.ljust(16, b'\0')):
                memory.u8[HERO + index] = value
            before = int(game.core.cpu.gprs[1])
            game.core.cpu.gprs[1] = target
            checks = dialogue_checks.TextChecks(game, {target: {
                'id': 'player-initial-probe', 'encoded_hex': payload.hex(),
                'layout': {'pages': [['{initial}-{player}!']]}}})
            observer = Observer(game)

            def callback(event):
                checks.callback(event)
                observer.callback(event)

            with Debugger(game, callback, max_events=20000) as debug:
                for address in set(checks.ADDRESSES + observer.ADDRESSES):
                    debug.breakpoint(address)
                game.frames(180)
                require(checks.completed('player-initial-probe') and checks.active is None,
                        'Initial probe did not complete')
                game.capture('rendered')
            read = next(r for r in observer.reads if r['source'] == target)
            expected = dialogue_checks.rendered_codes(name[:2] + encode('-')[:-1] + name[:-1] + encode('!'))
            # Observer keeps nested player rendering in its own read;
            # TextChecks above validates the complete flattened sequence.
            require(read['glyph_positions'][0]['code'] == expected[0],
                    'Initial glyph differs')
            width = sum(checks.glyph_record(code)[0]['advance'] for code in expected)
            require(read['glyph_positions'][0]['x'] == (read['window_width'] - width) // 2,
                    'Native centering did not account for the initial')
            require(guard == (bytes(memory[target - 16:target]), bytes(memory[target + len(original):target + len(original) + 16])),
                    'Probe wrote beyond the owned source span')
            require(game.snapshot().battery == fixture.battery, 'Probe wrote the save')
            results.append({'case': label, 'name_hex': name.hex(), 'width': width,
                            'read': checks.reads[0], 'glyph_checks': checks.glyph_checks,
                            'controlled_r1': {'before': before, 'after': target},
                            'centered': True, 'save_unchanged': True, 'inputs': game.inputs})
    report = {'passed': True, 'rom_sha256': digest(rom), 'fixture_sha256': digest(fixture.state),
              'source_ram_span': [target, target + len(original)], 'payload_hex': payload.hex(),
              'cases': results,
              'scope': 'Controlled reader argument and existing event-text RAM replacement. Control 7F renders the first two-byte player glyph and participates in native centering. Production rendered-code expectations checked against independently expanded name bytes. No active translation/ROM insertion changes; no ordinary missing-King scene coverage.'}
    (OUT / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print('Player-initial control:', len(results), 'native cases passed')
    return report


if __name__ == '__main__':
    run()
