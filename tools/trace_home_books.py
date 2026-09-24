"""Replay the three home books and first banker request using ordinary inputs."""

import argparse
import json
from pathlib import Path

import mgba.log

from tools.emulator import Debugger, Session, Snapshot
from tools.opening_text import BANK_RAM, banks
from tools.rom import ROOT, default_rom, digest, load_base, require
from tools.text_codec import readable, tokenize
from tools.town_playtest import position
from tools.town_text import RAM as COMMON_RAM, resource as common_resource
from tools.name_entry_playtest import position as dungeon_position

OUTPUT = ROOT / 'build/home-books/native'
FIXTURE = ROOT / 'build/home-return/research/village'
MENU = 'town-common.3dec'
OVERWRITE = 'rom.00148304'
CHOICE = 'rom.0006309c'
SAVED = 'rom.00061ffc'


class SourceTrace:
    ADDRESSES = (0x080021B4, 0x08002284, 0x08015CE8, 0x08015E28,
                 0x0801FB38, 0x0801FB3C, 0x080153EE, 0x080153F2, 0x08002124)

    def __init__(self, game, route):
        self.game, self.route = game, route
        self.original, self.bank, self.common = load_base(), banks()[1], common_resource()
        self.entries, self.completed, self.reads = [], [], []
        self.choices, self.formats, self.centers = [], [], []
        self.active, self.depth, self.choice_active = None, 0, False

    def source(self, pointer):
        if 0x08000000 <= pointer < 0x08800000:
            return self.original, pointer - 0x08000000, {'kind': 'rom'}, 'rom'
        for base, bank in [(BANK_RAM, self.bank), (COMMON_RAM, self.common)]:
            if base <= pointer < base + len(bank['data']):
                return bank['data'], pointer - base, {'kind': 'compressed-bank', 'bank': bank['id'],
                    'compressed_rom_offset': bank['rom_offset']}, bank['id']
        raise ValueError(f'Unowned text pointer {pointer:08x}')

    def record(self, pointer, event, consumer='reader'):
        data, start, source, resource = self.source(pointer)
        tokens, end = tokenize(data, start)
        raw = data[start:end]
        require(bytes(self.game.core.memory[pointer:pointer + len(raw)]) == raw, 'Native source differs')
        ident = f'rom.{start:08x}' if resource == 'rom' else f'{resource}.{start:04x}'
        row = {'id': ident, 'source': source | {'offset': start, 'end_exclusive': end},
               'raw_hex': raw.hex(), 'source_sha256': digest(raw), 'tokens': tokens,
               'japanese': readable(tokens), 'evidence': [{'route': self.route, 'frame': event['frame'],
               'reader': event['address'], 'consumer': consumer, 'source': pointer}]}
        self.entries.append(row)
        return row

    def callback(self, event):
        r, a, m = event['registers'], event['address'], self.game.core.memory
        if a == 0x0801FB38:
            require(r[1] == 0x08148304 and r[0] == r[13], 'Overwrite formatter differs')
            row = self.record(r[1], event, 'native formatter; resulting stack buffer also read')
            name = bytes(m[r[2]:r[2] + 18]).split(b'\0')[0]
            expected = bytes.fromhex(row['raw_hex']).replace(b'%s', name)
            require(len(expected) <= 128, 'Overwrite stack buffer exceeds allocation')
            self.formats.append({'id': OVERWRITE, 'destination': r[0], 'name_hex': name.hex(), 'output_hex': expected.hex(),
                                 'frame': event['frame'], 'preserved': (r[4:12], r[13]),
                                 'after': bytes(m[r[0] + len(expected):r[0] + 128]).hex()})
        elif a == 0x080153EE:
            require(r[0] == r[13] + 4 and r[1] == 0x0806B4F0, 'Quit formatter differs')
            rows = [self.record(p, event, 'native quit-message formatter argument') for p in r[2:4]]
            require([x['id'] for x in rows] == [SAVED, 'rom.00061d38'], 'Quit argument sources differ')
            require(self.original[0x6B4F0:0x6B4F7] == b'%s\r\x14%s\0', 'Quit format grammar differs')
            expected = bytes.fromhex(rows[0]['raw_hex'])[:-1] + b'\r\x14' + bytes.fromhex(rows[1]['raw_hex'])
            require(len(expected) <= 128, 'Quit stack buffer exceeds allocation')
            self.formats.append({'id': 'save-quit-message', 'destination': r[0], 'output_hex': expected.hex(),
                                 'frame': event['frame'], 'preserved': (r[4:12], r[13]),
                                 'after': bytes(m[r[0] + len(expected):r[0] + 128]).hex()})
        elif a in (0x0801FB3C, 0x080153F2):
            call = self.formats[-1]; dest = call['destination']; expected = bytes.fromhex(call['output_hex'])
            require(bytes(m[dest:dest + len(expected)]) == expected, 'Overwrite formatter output differs')
            require(bytes(m[dest + len(expected):dest + 128]).hex() == call.pop('after'), 'Overwrite buffer tail changed')
            require(call.pop('preserved') == (r[4:12], r[13]), 'Overwrite formatter changed registers/SP')
            call['buffer_tail_and_registers_preserved'] = True
        elif a == 0x08015CE8:
            self.choice_active = True
        elif a == 0x08015E28:
            self.choice_active = False
            self.choices.append(r[0])
        elif a == 0x080021B4:
            if self.active is not None:
                self.depth += 1
                return
            if self.formats and r[1] == self.formats[-1]['destination']:
                row = {'id': self.formats[-1]['id']}
                require(bytes(m[r[1]:r[1] + len(bytes.fromhex(self.formats[-1]['output_hex']))]).hex() ==
                        self.formats[-1]['output_hex'], 'Generated overwrite text differs')
            else:
                row = self.record(r[1], event)
            self.active = {'id': row['id'], 'source': r[1], 'window': r[0],
                           'window_hex': bytes(m[r[0]:r[0] + 24]).hex(), 'start_frame': event['frame']}
        elif a == 0x08002284 and self.active is not None:
            if self.depth:
                self.depth -= 1
            else:
                self.active['end_frame'] = event['frame']
                self.reads.append(self.active)
                self.completed.append(self.active['id'])
                self.active = None
        elif a == 0x08002124:
            self.centers.append({'source': self.active['id'] if self.active else None,
                                 'window': r[5], 'frame': event['frame']})


def approach_books(game):
    for key, hold, wait in [('UP',32,60), ('UP',16,120), ('RIGHT',40,30), ('UP',28,30),
                          ('RIGHT',24,30), ('UP',32,30)]:
        game.press(key, hold=hold, wait=wait)
    require(position(game) == (320,224), 'Home-book approach differs')


def finish(game, observer, expected, label):
    for page in range(100):
        game.capture(f'{label}-{page:03}')
        require(observer.completed == expected[:len(observer.completed)],
                f'Unexpected route sources in {label}: {observer.completed}; expected {expected}')
        if observer.completed == expected and observer.active is None:
            return
        game.press('A', wait=240)
    raise ValueError(f'Route did not finish: {label}; reads {observer.completed}')


def play(game, village, observer_factory, include_green=False):
    """Identical route actions for source research and English verification."""
    results = []
    scenarios = ['red-book', 'view-empty', 'sell-empty', 'save-cancel', 'save-continue', 'save-quit']
    if include_green:
        scenarios += ['green-book']
    scenarios += ['banker-no', 'banker-yes']
    for scenario in scenarios:
        game.restore(village)
        input_start = len(game.inputs) - 1
        observer = observer_factory(game, scenario)
        before_battery = digest(game.snapshot().battery)
        mansion = None
        with Debugger(game, observer.callback, max_events=100000) as debugger:
            for address in observer.ADDRESSES:
                debugger.breakpoint(address)
            if scenario.startswith('banker'):
                game.press('DOWN', hold=40, wait=60)
                game.press('DOWN', wait=60)
                require(observer.completed == ['rom.0006c524','rom.0006c154','rom.0006c144'], 'Square travel menu differs')
                game.capture(scenario + '-travel-menu')
                game.press('DOWN', wait=30)
                game.press('A', wait=540)
                require(position(game) == (192,96), 'Square arrival differs')
                game.snapshot().save(game.output / (scenario + '-square'))
                for key, hold in [('UP',16),('RIGHT',96),('DOWN',8),('LEFT',16),('DOWN',80),('RIGHT',104),('UP',3)]:
                    game.press(key, hold=hold, wait=30)
                require(position(game) == (560,384), 'Banker approach differs')
                game.snapshot().save(game.output / (scenario + '-entry'))
                expected = observer.completed + ['event-bank-1.449e', CHOICE]
                game.press('A', wait=240)
                finish(game, observer, expected, scenario + '-question')
                if scenario == 'banker-no':
                    game.press('RIGHT', wait=30)
                    expected += ['event-bank-1.45fc']
                else:
                    expected += ['event-bank-1.4660','event-bank-1.28fc','event-bank-1.48bd']
                game.press('A', wait=240)
                finish(game, observer, expected, scenario + '-reply')
                require(observer.choices == [int(scenario == 'banker-yes')], 'Banker choice result differs')
                game.press('A', wait=240)
                if scenario == 'banker-yes':
                    game.press('RIGHT', wait=30)
                    game.press('A', wait=240)
                    expected += ['event-bank-1.469c']
                    finish(game, observer, expected, scenario + '-reminder')
                    game.press('A', wait=30)
                    game.press('UP', hold=32, wait=60)
                    game.snapshot().save(game.output / 'mansion-departure')
                    game.press('UP', hold=16, wait=600)
                    m = game.core.memory
                    require(m.u32[0x02003B6C] == 0 and m.u16[0x02005674] == 1,
                            'Mansion did not reach dungeon zero, floor one')
                    game.capture('mansion-floor-one')
                    game.snapshot().save(game.output / 'mansion-floor-one')
                    before = dungeon_position(game)
                    game.press('RIGHT', wait=90)
                    after = dungeon_position(game)
                    require(after == (before[0] + 1, before[1]), 'Mansion movement did not resume')
                    game.capture('mansion-first-movement')
                    mansion = {'dungeon_id':0, 'floor':1, 'before_grid':before, 'after_grid':after,
                               'ordinary_movement_verified':True}
                else:
                    before = position(game)
                    game.press('DOWN', hold=8, wait=30)
                    require(position(game) != before, 'Town controls did not resume')
            else:
                approach_books(game)
                if scenario == 'red-book':
                    game.press('LEFT', hold=32, wait=30)
                    game.press('UP', wait=30)
                    game.press('A', wait=240)
                    finish(game, observer, ['event-bank-1.073a'], scenario)
                    game.press('A', wait=30)
                    game.press('DOWN', hold=8, wait=30)
                    require(position(game) == (256,256), 'Book did not return town controls')
                elif scenario == 'green-book':
                    game.press('UP', wait=30)
                    game.press('A', wait=240)
                    game.capture('green-parent')
                    game.press('A', wait=240)
                    game.capture('green-empty-scroll-list')
                    game.press('B', wait=30)
                    game.press('B', wait=30)
                    game.press('A', wait=30)
                    game.press('DOWN', wait=30)
                    game.press('A', wait=240)
                    game.capture('green-records-menu')
                else:
                    game.press('LEFT', hold=16, wait=30)
                    game.press('UP', wait=30)
                    game.press('A', wait=240)
                    game.capture(scenario + '-menu')
                    require(observer.completed == [MENU], 'Blue book menu differs')
                    selection = {'view-empty':0, 'sell-empty':1, 'save-cancel':2, 'save-continue':2, 'save-quit':3}[scenario]
                    for _ in range(selection):
                        game.press('DOWN', wait=30)
                    game.press('A', wait=240)
                    if selection < 2:
                        ident = 'town-common.2a76' if selection == 0 else 'town-common.4090'
                        require(observer.completed == [MENU, ident], 'Empty inventory reply differs')
                        game.capture(scenario + '-notice')
                    else:
                        require(observer.completed == [MENU, OVERWRITE, CHOICE], 'Overwrite prompt differs')
                        game.capture(scenario + '-overwrite')
                        if scenario == 'save-cancel':
                            game.press('RIGHT', wait=30)
                        game.press('A', wait=240)
                        ident = ('town-common.40f4' if scenario == 'save-cancel' else
                                 'save-quit-message' if scenario == 'save-quit' else SAVED)
                        require(observer.completed == [MENU, OVERWRITE, CHOICE, ident], 'Save outcome differs')
                        require(observer.choices == [int(scenario != 'save-cancel')], 'Save choice result differs')
                        game.capture(scenario + '-result')
                    game.press('A', wait=600 if scenario == 'save-quit' else 240)
                    if scenario != 'save-quit':
                        require(observer.completed[-1] == MENU, 'Blue book menu did not reopen')
                        game.press('B', wait=30)
                        game.press('DOWN', hold=8, wait=30)
                        require(position(game) == (288,256), 'Blue book controls did not resume')
                    if scenario in ('save-continue','save-quit'):
                        require(digest(game.snapshot().battery) != before_battery, 'Native save did not change battery')
                        (game.output / (scenario + '.sav')).write_bytes(game.snapshot().battery)
                    else:
                        require(digest(game.snapshot().battery) == before_battery, 'Non-save action changed battery')
            game.capture(scenario + '-end')
        results.append({'route': scenario, 'reads': observer.reads, 'choices': observer.choices,
                        'formatter_calls': observer.formats, 'centers': observer.centers,
                        'mansion_entrance': mansion,
                        'inputs': game.inputs[input_start:], 'end_position': position(game),
                        'before_battery_sha256': before_battery, 'after_battery_sha256': digest(game.snapshot().battery),
                        'native_glyph_checks': getattr(observer, 'glyph_checks', 0)})
    return results


def run(fixture=FIXTURE, output=OUTPUT):
    mgba.log.silence()
    original = load_base(); snapshot = Snapshot.load(fixture)
    save = default_rom().with_suffix('.sav'); save_hash = digest(save.read_bytes())
    observers = []
    def factory(game, route):
        trace = SourceTrace(game, 'home-books/' + route); observers.append(trace); return trace
    with Session(original, output) as game:
        results = play(game, snapshot, factory, include_green=True)
    entries = {}
    for observer in observers:
        for row in observer.entries:
            if row['id'] in entries:
                entries[row['id']]['evidence'].extend(row['evidence'])
            else:
                entries[row['id']] = row
    require(digest(save.read_bytes()) == save_hash and digest(load_base()) == digest(original), 'Original files changed')
    report = {'passed': True, 'source_rom_sha256': digest(original), 'source_save_sha256': save_hash,
              'original_files_unchanged': True, 'fixture_state_sha256': digest(snapshot.state),
              'routes': results, 'entries': list(entries.values()),
              'scope': 'Natural book and empty-inventory/save flows, green-book discovery, both banker choices and first mansion entrance. Storehouse remains broken; populated lists, later quest states and dungeon completion are not covered.'}
    (output / 'trace.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print('Japanese home books:', len(results), 'routes,', len(entries), 'sources')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fixture', type=Path, default=FIXTURE)
    parser.add_argument('--output', type=Path, default=OUTPUT)
    args = parser.parse_args()
    run(args.fixture.resolve(), args.output.resolve())
