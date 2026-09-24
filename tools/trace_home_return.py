"""Trace the native first evening/morning and both nearby carpenter responses."""

import argparse
import json
from pathlib import Path

import mgba.log

from tools.emulator import Debugger, Session, Snapshot
from tools.event_text import table_entries
from tools.opening_text import BANK_RAM, banks
from tools.review_fonts import extract
from tools.rom import ROOT, default_rom, digest, load_base, require
from tools.text_codec import readable, tokenize
from tools.town_playtest import position, face_home_roamer

OUTPUT = ROOT / 'build/home-return/research'
FIXTURE = ROOT / 'build/destination-menu/research/home-menu'
ROUTES = ROOT / 'config/routes/home-return.json'
HEART = 0x874E


class SourceTrace:
    ADDRESSES = (0x080021B4, 0x08002284, 0x0804D722, 0x0804D726,
                 0x0804F938, 0x08015CE8, 0x08015E28, 0x08002094,
                 0x080020A6, 0x080020AC, 0x080020B2, 0x08001C14,
                 0x08051614, 0x08051618, 0x08051664, 0x080516AE)

    def __init__(self, game, original, route):
        self.game, self.original, self.route = game, original, route
        self.bank = banks()[1]
        self.tables = {(r['group'], r['index']): r for r in table_entries(self.bank)}
        self.entries, self.completed, self.slots = [], [], []
        self.loads, self.colors, self.hearts, self.choices = [], [], [], []
        self.generated = []
        self.formats, self.commands = [], []
        self.active, self.depth, self.choice_active = None, 0, False
        self.bank_before, self.color_before = None, None

    def callback(self, event):
        r, a, m = event['registers'], event['address'], self.game.core.memory
        if a == 0x08051614:
            require(r[0] == 0x0202F44C and r[1] == 0x0806C424, 'Unexpected sale formatter arguments')
            tokens, end = tokenize(self.original, 0x6C424)
            raw = self.original[0x6C424:end]
            require(bytes(m[r[1]:r[1] + len(raw)]) == raw, 'Native sale template differs')
            self.entries.append({'id': 'rom.0006c424', 'source': {'kind': 'rom', 'offset': 0x6C424, 'end_exclusive': end},
                                 'raw_hex': raw.hex(), 'source_sha256': digest(raw), 'tokens': tokens,
                                 'japanese': readable(tokens), 'evidence': [{'route': self.route, 'frame': event['frame'],
                                 'reader': a, 'consumer': 'native formatter; resulting RAM stream also observed at 080021B4',
                                 'source': r[1], 'destination': r[0], 'amount': r[2]}]})
            self.formats.append({'frame': event['frame'], 'amount': r[2], 'template_hex': raw.hex(),
                                 'preserved': (r[4:12], r[13])})
        elif a == 0x08051618:
            call = self.formats[-1]
            expected = bytes.fromhex(call['template_hex']).replace(b'%-ld', str(call['amount']).encode('ascii'))
            require(bytes(m[0x0202F44C:0x0202F44C + len(expected)]) == expected, 'Native formatted sale differs')
            require(call.pop('preserved') == (r[4:12], r[13]), 'Sale formatter changed preserved registers/SP')
            call.update(output_hex=expected.hex(), preserved_registers_and_sp=True)
        elif a == 0x08051664:
            self.commands.append({'command': bytes(m[r[0]:r[0] + 3]).decode('ascii'),
                                  'before_flags': m.u8[0x0201020E], 'frame': event['frame']})
        elif a == 0x080516AE:
            self.commands[-1]['after_flags'] = m.u8[0x0201020E]
        elif a == 0x0804D722:
            require(r[0] == 0x08000000 + self.bank['rom_offset'], 'Unexpected home bank load')
            end = BANK_RAM + len(self.bank['data'])
            self.bank_before = bytes(m[BANK_RAM - 64:BANK_RAM]), bytes(m[end:end + 64]), r[4:12], r[13]
        elif a == 0x0804D726:
            end = BANK_RAM + len(self.bank['data'])
            require(bytes(m[BANK_RAM:end]) == self.bank['data'], 'Native bank-one bytes differ')
            require(self.bank_before == (bytes(m[BANK_RAM - 64:BANK_RAM]), bytes(m[end:end + 64]), r[4:12], r[13]),
                    'Home decompression changed guards or preserved registers/SP')
            self.loads.append({'frame': event['frame'], 'decoded_bytes': len(self.bank['data']),
                               'decoded_sha256': digest(self.bank['data']), 'guards_and_registers_preserved': True})
        elif a == 0x0804F938:
            script = m.u32[0x02010138]
            group, index = m.u8[script + 1], m.u8[script + 2]
            row = self.tables[group, index]
            require(r[5] == BANK_RAM + row['slot'] and
                    r[6] + m.u32[r[3]] + m.u32[r[5]] == BANK_RAM + row['start'], 'Native home table target differs')
            self.slots.append({k: row[k] for k in ('id', 'group', 'index', 'slot')} |
                              {'frame': event['frame'], 'script_hex': bytes(m[script:script + 5]).hex()})
        elif a == 0x08015CE8:
            self.choice_active = True
        elif a == 0x08015E28:
            self.choice_active = False
            self.choices.append(r[0])
        elif a == 0x080021B4:
            if self.active is not None:
                self.depth += 1
                return
            pointer = r[1]
            if BANK_RAM <= pointer < BANK_RAM + len(self.bank['data']):
                data, start = self.bank['data'], pointer - BANK_RAM
                ident = f"{self.bank['id']}.{start:04x}"
                source = {'kind': 'compressed-bank', 'bank': self.bank['id'],
                          'compressed_rom_offset': self.bank['rom_offset']}
            elif pointer == 0x0202F44C:
                data, start = bytes(m[pointer:pointer + 2048]), 0
                ident, source = 'generated.0202f44c', {'kind': 'runtime-buffer'}
            else:
                require(0x08000000 <= pointer < 0x08000000 + len(self.original),
                        f'Unexpected home text source {pointer:08x}: {self.route}, after {self.completed}; '
                        + bytes(m[pointer:pointer + 32]).hex())
                data, start = self.original, pointer - 0x08000000
                ident, source = f'rom.{start:08x}', {'kind': 'rom'}
            tokens, end = tokenize(data, start)
            raw = data[start:end]
            require(bytes(m[pointer:pointer + len(raw)]) == raw, 'Native home source differs')
            self.active = {'id': ident, 'source': source | {'offset': start, 'end_exclusive': end},
                           'raw_hex': raw.hex(), 'source_sha256': digest(raw), 'tokens': tokens,
                           'japanese': readable(tokens), 'evidence': [{'route': self.route, 'frame': event['frame'],
                           'reader': a, 'source': pointer, 'window': r[0], 'window_hex': bytes(m[r[0]:r[0] + 24]).hex()}]}
            self.active['evidence'][0]['link_register'] = r[14]
            (self.generated if source['kind'] == 'runtime-buffer' else self.entries).append(self.active)
        elif a == 0x08002284 and self.active is not None:
            if self.depth:
                self.depth -= 1
            else:
                self.completed.append(self.active['id'])
                self.active = None
        elif a in (0x08002094, 0x080020AC):
            self.color_before = m.u8[0x020000C2], m.u8[0x020000C3]
        elif a in (0x080020A6, 0x080020B2):
            before, saved = self.color_before
            operand = m.u8[r[4]] if a == 0x080020A6 else None
            expected = (operand & 7) + 8 if operand is not None else saved
            require(m.u8[0x020000C2] == expected, 'Native foreground control differs')
            require(m.u8[0x020000C3] == (before if operand is not None else saved), 'Saved foreground differs')
            self.colors.append({'id': self.active['id'] if self.active else None, 'frame': event['frame'],
                                'code': 3 if operand is not None else 5, 'operand': operand,
                                'before': before, 'after': expected, 'saved': m.u8[0x020000C3]})
        elif a == 0x08001C14 and r[4] == HEART:
            glyph = extract(self.original, HEART)
            require(r[0] == 0x08000000 + glyph['rom_offset'], 'Native heart lookup differs')
            bg = 4 if m.u8[r[5] + 9] & 1 else 7
            pixels = bytes(m.u8[0x020000C2] if bit else (7 if y < 2 else bg)
                           for y, line in enumerate(glyph['pixels']) for bit in line) + bytes([bg]) * glyph['width']
            require(bytes(m[0x02036430:0x02036430 + len(pixels)]) == pixels, 'Native heart pixels differ')
            self.hearts.append({'id': self.active['id'], 'frame': event['frame'], 'glyph': glyph,
                                'native_pixels_match': True})


def finish(game, observer, expected, label, choice=None):
    chose_no = False
    for page in range(100):
        game.capture(label + f'-{page:03}')
        if observer.completed == expected and observer.active is None:
            return
        if observer.choice_active and choice == 'no' and not chose_no:
            game.press('RIGHT', wait=30)
            chose_no = True
            game.capture(label + '-choice-no')
        game.press('A', wait=240)
    raise ValueError('Home route did not complete: ' + label)


def run(fixture=FIXTURE, output=OUTPUT):
    mgba.log.silence()
    original, snapshot = load_base(), Snapshot.load(fixture)
    source_save = default_rom().with_suffix('.sav')
    save_hash = digest(source_save.read_bytes())
    routes, results, entries = json.loads(ROUTES.read_text()), [], {}
    with Session(original, output) as game:
        for route in [{'id': 'evening-morning', 'reads': routes['home_reads']}] + routes['routes']:
            home = route['id'] == 'evening-morning'
            game.restore(snapshot if home else Snapshot.load(output / 'village'))
            input_start = len(game.inputs) - 1
            observer = SourceTrace(game, original, routes['id'] + '/' + route['id'])
            with Debugger(game, observer.callback, max_events=15000) as trace:
                for address in observer.ADDRESSES:
                    trace.breakpoint(address)
                for step in route.get('steps', []):
                    game.press(step['key'], hold=step['hold'], wait=30)
                facing = face_home_roamer(game) if route['id'] == 'mansion-rumour' else None
                approach = position(game)
                game.capture(route['id'] + '-approach')
                game.press('A', wait=600 if home else 240)
                finish(game, observer, route['reads'], route['id'], route.get('choice'))
                require(observer.choices == ([int(route['choice'] == 'yes')] if 'choice' in route else []),
                        'Home choice outcome differs')
                game.press('A', wait=360 if home else 30)  # Close the final story window.
                require(observer.completed == route['reads'] and observer.active is None, 'Closing reopened dialogue')
                game.capture(route['id'] + '-closed')
                if home:
                    require(list(position(game)) == routes['village_position'], 'Village arrival position differs')
                    require(len(observer.loads) == len(observer.hearts) == 1 and len(observer.colors) == 8,
                            'Missing native home bank/color/heart evidence')
                    game.snapshot().save(output / 'village')
                    before = position(game)
                    game.press('DOWN', hold=8, wait=30)
                    require(position(game) != before, 'Village movement did not resume')
            for row in observer.entries:
                if row['id'] in entries:
                    entries[row['id']]['evidence'].extend(row['evidence'])
                else:
                    entries[row['id']] = row
            results.append({'route': route['id'], 'reads': observer.completed, 'choices': observer.choices,
                            'roaming_npc_facing': facing,
                            'approach_position': approach, 'slots': observer.slots, 'bank_loads': observer.loads,
                            'color_controls': observer.colors, 'heart_glyphs': observer.hearts,
                            'generated_streams': observer.generated,
                            'formatter_calls': observer.formats, 'event_commands': observer.commands,
                            'inputs': game.inputs[input_start:]})
    require(digest(source_save.read_bytes()) == save_hash and digest(load_base()) == digest(original), 'Original files changed')
    report = {'passed': True, 'source_rom_sha256': digest(original), 'source_save_sha256': save_hash,
              'original_files_unchanged': True, 'fixture_state_sha256': digest(snapshot.state),
              'routes_sha256': digest(ROUTES.read_bytes()), 'routes': results, 'entries': list(entries.values()),
              'scope': 'Natural first evening/morning and village movement, then four normal-input conversations from the resulting checkpoint, including both Ed choices. Original ROM; no RAM/register overrides. Other village states, books and mansion quest remain separate.'}
    (output / 'trace.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print('Japanese home return:', len(results), 'routes,', len(entries), 'unique sources')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fixture', type=Path, default=FIXTURE)
    parser.add_argument('--output', type=Path, default=OUTPUT)
    args = parser.parse_args()
    run(args.fixture.resolve(), args.output.resolve())
