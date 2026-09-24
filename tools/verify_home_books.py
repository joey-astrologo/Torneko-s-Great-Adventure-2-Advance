"""Verify the English red/blue books, saves and first banker/mansion route."""

import json
from pathlib import Path

import mgba.log

from tools.book_text import CAPACITY, materialize
from tools.build_english import build_rom
from tools.dialogue_checks import TextChecks, player_layout_cases, rendered_codes
from tools.emulator import Debugger, Session, Snapshot
from tools.name_entry import HERO, STORED
from tools.rom import ROOT, default_rom, digest, load_base, require
from tools.trace_home_books import CHOICE, OVERWRITE, SAVED, play
from tools.town_playtest import position

OUTPUT = ROOT / 'build/english/books-validation'
FIXTURE = ROOT / 'build/english/home-validation/village'


class EnglishTrace:
    ADDRESSES = TextChecks.ADDRESSES + (0x08015CE8, 0x08015E28, 0x0801FB34, 0x0801FB38,
        0x0801FB3C, 0x080153EE, 0x080153F2, 0x08002124, 0x0800212A, 0x08002138)

    def __init__(self, game, route, build, save_fixture=True):
        self.game, self.route, self.save_fixture = game, route, save_fixture
        self.resources = {0x08000000 + row['rom_offset']: row for row in build['dialogue']['entries']}
        for row in build.get('town_actions',{}).get('entries',[]):
            if row['index']!=59:continue
            prior=next(r for r in self.resources.values() if r['id']==row['id'])
            require(row['encoded_hex']==prior['encoded_hex'],
                    'Private empty-inventory replacement differs from approved book text')
            self.resources[row['offset']+0x08000000]=prior|{'rom_offset':row['offset']}
        self.targets = {row['id']: ptr for ptr, row in self.resources.items()}
        self.checks = TextChecks(game, dict(self.resources))
        self.choices, self.formats, self.centers = [], [], []
        self.choice_active = False
        self.pending_format, self.pending_center = None, None

    @property
    def active(self):
        return self.checks.active

    @property
    def reads(self):
        return self.checks.reads

    @property
    def completed(self):
        return [row['id'] for row in self.reads]

    @property
    def glyph_checks(self):
        return self.checks.glyph_checks

    def callback(self, event):
        r, a, m = event['registers'], event['address'], self.game.core.memory
        if a == 0x0801FB34 and self.save_fixture:
            self.game.snapshot().save(self.game.output / 'overwrite-entry')
        elif a in (0x0801FB38, 0x080153EE):
            if a == 0x0801FB38:
                require(r[0] == r[13] and r[1] == self.targets[OVERWRITE], 'English overwrite arguments differ')
                row = self.resources[r[1]]
                name = bytes(m[r[2]:r[2] + 16]).split(b'\0')[0]
                payload = materialize(bytes.fromhex(row['encoded_hex']), name)
                extra = {'name_hex': name.hex(), 'name_pointer': r[2]}
            else:
                require(r[0] == r[13] + 4 and r[1] == 0x0806B4F0 and
                        r[2:4] == [self.targets[SAVED],self.targets['rom.00061d38']], 'English quit arguments differ')
                saved, farewell = [self.resources[p] for p in r[2:4]]
                payload = bytes.fromhex(saved['encoded_hex'])[:-1] + b'\r\x14' + bytes.fromhex(farewell['encoded_hex'])
                require(len(payload) <= CAPACITY, 'English quit message exceeds stack buffer')
                row = {'id': 'save-quit-message', 'layout': {'pages': [[SAVED, 'rom.00061d38']]}}
                extra = {'part_ids': [SAVED, 'rom.00061d38']}
            self.checks.resources[r[0]] = row | {'encoded_hex': payload.hex()}
            self.pending_format = {'id': row['id'], 'destination': r[0], 'output_hex': payload.hex(),
                'output_bytes': len(payload), 'capacity': CAPACITY, 'frame': event['frame'], **extra}
            self.format_before = (bytes(m[r[0] + len(payload):r[0] + CAPACITY + 32]), r[4:12], r[13])
        elif a in (0x0801FB3C, 0x080153F2):
            call = self.pending_format; dest = call['destination']; payload = bytes.fromhex(call['output_hex'])
            require(bytes(m[dest:dest + len(payload)]) == payload, 'Native English book formatting differs')
            require(self.format_before == (bytes(m[dest + len(payload):dest + CAPACITY + 32]),r[4:12],r[13]),
                    'English book formatter changed tail/guard/registers/SP')
            call.update(buffer_tail_and_guard_preserved=True, callee_saved_and_sp_preserved=True)
            self.formats.append(call)
            self.pending_format = None
        elif a == 0x08015CE8:
            self.choice_active = True
        elif a == 0x08015E28:
            self.choice_active = False
            self.choices.append(r[0])
        elif a == 0x08002124:
            require(self.active is not None and r[5] == self.active['window'], 'Unowned centred text')
            # These owned centred lines contain no operand-bearing commands.
            data = bytes(m[r[4] + 1:r[4] + 513])
            end = next(i for i, value in enumerate(data) if value in (0,10,13))
            codes = rendered_codes(data[:end] + b'\0', bytes(m[HERO:HERO + 16]))
            width = sum(self.checks.glyph_record(code)[0]['advance'] for code in codes)
            self.pending_center = {'id': self.active['id'], 'line_width': width,
                                   'window_width': m.u8[r[5] + 4] * 8,
                                   'expected_x': (m.u8[r[5] + 4] * 8 - width) // 2, 'frame': event['frame']}
        elif a == 0x0800212A:
            require(self.pending_center is not None and r[0] == self.pending_center['line_width'],
                    'Native centring measured a different pixel width')
        elif a == 0x08002138:
            require(m.u8[r[5] + 2] == self.pending_center['expected_x'], 'Native centring position differs')
            self.centers.append(self.pending_center | {'native_width_and_position_match': True})
            self.pending_center = None
        elif a == 0x080021B4:
            require(r[1] in self.checks.resources or (self.active is not None and r[1] == HERO),
                    f'Untranslated book-route source {r[1]:08x} in {self.route}')
        self.checks.callback(event)


def name_probes(rom, build, output):
    snapshot = Snapshot.load(output / 'overwrite-entry')
    results = []
    with Session(rom, output / 'name-probes') as game:
        for label, name in player_layout_cases():
            game.restore(snapshot)
            input_start = len(game.inputs) - 1
            m = game.core.memory
            guard = bytes(m[HERO - 16:HERO]), bytes(m[HERO + 16:HERO + 32])
            for i, value in enumerate(name.ljust(16,b'\0')):
                m.u8[HERO + i] = value
            game.core.cpu.gprs[2] = HERO  # Controlled alternate formatter argument; no save is written.
            observer = EnglishTrace(game, label, build, save_fixture=False)
            with Debugger(game, observer.callback, max_events=10000) as debugger:
                for a in observer.ADDRESSES:
                    debugger.breakpoint(a)
                game.frames(180)
            require(observer.completed == [OVERWRITE, CHOICE] and len(observer.formats) == 1,
                    'Controlled overwrite/name display did not finish')
            require(guard == (bytes(m[HERO - 16:HERO]),bytes(m[HERO + 16:HERO + 32])), 'Name probe changed guards')
            require(game.snapshot().battery == snapshot.battery, 'Controlled name probe changed save')
            game.capture(label)
            results.append({'case': label, 'name_hex': name.hex(), 'formatter_argument_pointer': HERO,
                            'fixture_state_sha256': digest(snapshot.state), 'reads': observer.reads,
                            'formatter_calls': observer.formats, 'native_glyph_checks': observer.glyph_checks,
                            'name_guards_and_battery_preserved': True, 'inputs': game.inputs[input_start:]})
    return results


def cold_loads(rom, snapshot, output, label, save_directory):
    with Session(rom, output / (label + '-name-reference')) as game:
        game.restore(snapshot)
        expected_hero = bytes(game.core.memory[HERO:HERO + 16])
        expected_indexed = bytes(game.core.memory[STORED:STORED + 16])
    results = []
    for action in ('save-continue', 'save-quit'):
        battery = (save_directory / (action + '.sav')).read_bytes()
        with Session(rom, output / (label + '-' + action), initial_save=battery) as game:
            game.frames(600)
            game.press('START', wait=180)
            game.capture('save-preview')
            game.press('A', wait=300)
            require(position(game) == (288,224), 'Cold book save did not resume at the blue book')
            m = game.core.memory
            require(bytes(m[HERO:HERO + 16]) == expected_hero and
                    bytes(m[STORED:STORED + 16]) == expected_indexed, 'Cold town save changed name records')
            game.capture('resumed')
            game.press('DOWN', hold=8, wait=30)
            require(position(game) == (288,256), 'Cold town movement did not resume')
            game.capture('movement')
            results.append({'rom':label, 'action':action, 'rom_sha256':digest(rom),
                            'save_sha256':digest(battery), 'hero_hex':expected_hero.hex(),
                            'indexed_names_hex':expected_indexed.hex(), 'names_preserved':True,
                            'position_after_movement':position(game), 'inputs':game.inputs,
                            'save_preview_scope':'Preview formatting remains partly Japanese; this checks native save/load and name persistence, not preview localization.'})
    return results


def run():
    mgba.log.silence()
    original = load_base(); rom, build = build_rom(); snapshot = Snapshot.load(FIXTURE)
    save = default_rom().with_suffix('.sav'); save_hash = digest(save.read_bytes())
    with Session(rom, OUTPUT) as game:
        routes = play(game, snapshot, lambda g, route: EnglishTrace(g, route, build))
    probes = name_probes(rom, build, OUTPUT)
    cold = cold_loads(rom, snapshot, OUTPUT / 'cold-load', 'english', OUTPUT)
    japanese = ROOT / 'build/english/books-validation/japanese'
    cold += cold_loads(original, Snapshot.load(ROOT / 'build/english/home-validation/japanese-home/village'),
                       OUTPUT / 'cold-load', 'japanese', japanese)
    require(digest(save.read_bytes()) == save_hash and digest(load_base()) == digest(original), 'Original files changed')
    report = {'passed': True, 'source_rom_sha256': digest(original), 'output_rom_sha256': digest(rom),
              'source_save_sha256': save_hash, 'original_files_unchanged': True,
              'fixture_state_sha256': digest(snapshot.state), 'routes': routes, 'controlled_name_layouts': probes,
              'cold_loads':cold,
              'scope': 'Natural red book, broken-storehouse blue-book actions, empty item lists, both save outcomes/cancel, banker Yes/No/old-man scene and mansion entrance. Three separate controlled village-name displays. Green-book contents, repaired storehouse, populated inventories and mansion completion remain outside this acceptance.'}
    (OUTPUT / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print('English books/banker:',len(routes),'routes,',sum(r['native_glyph_checks'] for r in routes),'natural glyph checks,',len(probes),'name probes')
    return report


if __name__ == '__main__':
    run()
