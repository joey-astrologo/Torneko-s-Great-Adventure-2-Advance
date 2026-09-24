"""Verify English input, cursor/glyph rendering, real saves and cold game loading."""

import argparse
import json
from pathlib import Path

import mgba.log

from tools.build_english import build_rom
from tools.compact_font import encode, load_font, measure
from tools.emulator import BIOS, Debugger, Session, battery_snapshot, version
from tools.name_entry import CHARACTERS, EDIT, HERO, IDS, STORED, indexed
from tools.name_entry_playtest import position, save_at_stairs, walk_to_stairs
from tools.name_entry_route import NameEntryRoute, POSITION, SELECTION
from tools.review_fonts import extract
from tools.numeric_font import ALIASES, glyph as numeric_glyph
from tools.rom import ROOT, default_rom, digest, load_base, require
from tools.verify_compact_font import call_thumb

OUTPUT = ROOT / 'build/english/name-entry-validation'


class EditorChecks:
    def __init__(self, game, rom, build):
        self.game, self.rom, self.build = game, rom, build
        self.base, self.font = load_base(), load_font()
        self.pending = None
        self.cursor_checks, self.prefix_checks, self.copy_checks = 0, 0, 0
        self.glyphs = set()
        self.guards = None

    def neighboring_bytes(self):
        memory = self.game.core.memory
        return (bytes(memory[STORED - 2:STORED]), bytes(memory[STORED + 16:HERO]),
                bytes(memory[HERO:HERO + 17]))

    def callback(self, event):
        regs, address = event['registers'], event['address']
        memory = self.game.core.memory
        if address == 0x08019F68:
            self.pending = regs
        elif address == 0x08019F72:
            before = self.pending
            require(before is not None, 'Missing cursor entry')
            self.pending = None
            window = bytes(memory[before[2]:before[2] + 24])
            expected = window[0]
            table = self.build['name_entry']['glyph_table'] - 0x08000000
            for ident in bytes(memory[EDIT:EDIT + memory.u32[POSITION]]):
                code = int.from_bytes(self.rom[table + ident * 2:table + ident * 2 + 2], 'big')
                width = (self.font['glyphs'][chr(code & 255)]['advance'] if 0xF020 <= code <= 0xF07E
                         else numeric_glyph(self.font,code)['advance'] if code in ALIASES
                         else extract(self.base, code)['width'])
                expected += (window[6] or width) + window[8]
            if before[14] == 0x080155FD:
                fmt = memory.u32[before[13] + 28 + 0x54]
                prefix = encode('Name: ')[:-1]
                if bytes(memory[fmt:fmt + len(prefix)]) == prefix:
                    expected += measure('Name: ')
                    self.prefix_checks += 1
            require(regs[0] == expected, 'Native name cursor differs from glyph advances')
            require(all(regs[i] == before[i] for i in (2, 4, 5, 6, 7, 8, 9, 10, 11, 13, 14)),
                    'Cursor helper changed preserved registers or SP')
            self.cursor_checks += 1
        elif address == 0x08001C14:
            code = regs[4]
            if not 0xF020 <= code <= 0xF07E:
                return
            glyph = self.font['glyphs'][chr(code & 255)]
            require(regs[0] == 0x08800000 + (code - 0xF020) * 32, 'Wrong English glyph record')
            window = bytes(memory[regs[5]:regs[5] + 24])
            foreground, background = memory.u8[0x020000C2], 4 if window[9] & 1 else 7
            expected = bytes(foreground if bit == '#' else (7 if y < 2 else background)
                             for y, row in enumerate(glyph['rows']) for bit in row)
            expected += bytes([background]) * glyph['advance']
            require(bytes(memory[0x02036430:0x02036430 + len(expected)]) == expected,
                    'Native prepared glyph pixels differ')
            self.glyphs.add(chr(code & 255))
        elif address == 0x0801567C:
            require(regs[:3] == [STORED, EDIT, 16], 'Unexpected name confirmation copy')
            self.guards = self.neighboring_bytes()
        else:
            require(address == 0x08015680 and self.guards is not None, 'Unpaired name copy')
            require(self.guards == self.neighboring_bytes(), 'Confirmation touched adjacent fields')
            require(bytes(memory[STORED:STORED + 16]) == bytes(memory[EDIT:EDIT + 16]),
                    'Confirmation record differs')
            self.guards = None
            self.copy_checks += 1

    def attach(self):
        debugger = Debugger(self.game, self.callback, max_events=500000)
        for address in (0x08019F68, 0x08019F72, 0x08001C14, 0x0801567C, 0x08015680):
            debugger.breakpoint(address)
        return debugger


def open_editor(game):
    game.frames(600)
    game.press('START', wait=180)
    game.press('A', wait=180)


def input_checks(rom, build, output):
    with Session(rom, output) as game:
        checks = EditorChecks(game, rom, build)
        with checks.attach():
            open_editor(game)
            route = NameEntryRoute(game, build['name_entry']['keyboard_pages'])
            game.capture('default')
            initial = game.snapshot()
            route.clear()
            game.capture('empty')
            empty = game.snapshot()
            for char in CHARACTERS:
                game.restore(empty)
                route.choose_id(IDS[char])
                require(bytes(game.core.memory[EDIT:EDIT + 16]) == indexed(char), 'Wrong selected character')
            game.restore(empty)
            for sample in ('WWWWWWW', 'iljtrfi', 'Torneko'):
                route.clear()
                route.enter(sample)
                require(game.core.memory.u32[SELECTION] == 3, 'Full name did not select Done')
                game.capture('sample-' + sample)
            route.press('B')
            require(bytes(game.core.memory[EDIT:EDIT + 16]) == indexed('Tornek'), 'Delete failed')
            route.choose_id(IDS['o'])
            game.capture('Torneko-reentered')
            route.choose_id(IDS['X'])
            require(bytes(game.core.memory[EDIT:EDIT + 16]) == indexed('TornekX'),
                    'Attempted eighth character did not replace the final slot safely')
            route.choose_id(IDS['o'])
            route.confirm()
            require(bytes(game.core.memory[STORED:STORED + 16]) == indexed('Torneko'), 'Confirm failed')
            # Reach the original conditional player-name screen with actual kana
            # and symbol selections, including its voiced-kana action.
            game.restore(initial)
            route.clear()
            for ident in load_base()[0x147DE4:0x147DEA]:
                if ident == 0x38:
                    route.choose_id(0x24)
                    route.choose_id(0xFF, page=3)
                else:
                    route.choose_id(ident)
            game.capture('original-secret')
            route.confirm()
            require(game.core.memory.u8[EDIT] == 1, 'Conditional player editor not entered')
            route.enter('Torneko')
            game.capture('player-name-Torneko')
            route.confirm()
            require(bytes(game.core.memory[HERO:HERO + 15]) == encode('Torneko'), 'Player name differs')
            game.restore(initial)
            route.clear()
            for ident in load_base()[0x147DE4:0x147DEA]:
                if ident == 0x38:
                    route.choose_id(0x24)
                    route.choose_id(0xFF, page=3)
                else:
                    route.choose_id(ident)
            route.choose_id(IDS['X'])
            seven = bytes(game.core.memory[EDIT:EDIT + 16])
            route.confirm()
            require(bytes(game.core.memory[STORED:STORED + 16]) == seven,
                    'Seven-character prefix incorrectly triggered the six-character secret')
        require(set(CHARACTERS) <= checks.glyphs and checks.prefix_checks > 0 and checks.copy_checks == 4,
                'Incomplete native editor coverage')
        # Actual native player-name width controls (~ and DEL), with snapshot
        # restoration. These original byte pairs are only controlled API inputs.
        width_probes = []
        for raw, expected in ((b'\x7E\0', measure('Torneko')), (b'\x7F\0', measure('T'))):
            offset = load_base().find(raw)
            require(offset >= 0, 'Missing controlled width input')
            probe = call_thumb(game, 0x08001C84, 0x08000000 + offset)
            require(probe['r0'] == expected, 'Player-name substitution width differs')
            width_probes.append(probe)
        return {'passed': True, 'selectable_english_characters': len(CHARACTERS),
                'native_glyphs_checked': ''.join(sorted(checks.glyphs)),
                'cursor_and_abi_checks': checks.cursor_checks, 'player_prefix_checks': checks.prefix_checks,
                'confirmation_guard_checks': checks.copy_checks, 'player_name_width_probes': width_probes,
                'normal_input_route': game.inputs}


def save_fields(memory, base):
    return {'indexed_header': bytes(memory[base + 0x214:base + 0x224]).hex(),
            'player_header': bytes(memory[base + 0x232:base + 0x242]).hex(),
            'indexed_body': bytes(memory[base + 0x2FE5:base + 0x2FF5]).hex(),
            'player_body': bytes(memory[base + 0x2FF5:base + 0x3005]).hex()}


def expected_fields(name_ids, player):
    return {'indexed_header': name_ids.hex(), 'player_header': player[:16].ljust(16, b'\0').hex(),
            'indexed_body': name_ids.hex(), 'player_body': player[:16].ljust(16, b'\0').hex()}


def decode_save_body(battery, slot):
    block = bytearray(battery[slot * 0x4000:(slot + 1) * 0x4000])
    key = bytes.fromhex('7e237e4d7e55')
    for i in range(0x280, 0x31B8):
        block[i] = (block[i] + key[(i - 0x280) % 6]) & 255
    return block


def verify_battery(battery, expected):
    original = load_base()
    signature = original[0x13EDCC:0x13EDCC + 32]
    slots = [s for s in range(4) if battery[s * 0x4000 + 0x3FE0:s * 0x4000 + 0x4000] == signature]
    require(slots, 'No complete native flash slot')
    for slot in slots:
        decoded = decode_save_body(battery, slot)
        actual = {'indexed_header': decoded[0x214:0x224].hex(), 'player_header': decoded[0x232:0x242].hex(),
                  'indexed_body': decoded[0x2FE5:0x2FF5].hex(), 'player_body': decoded[0x2FF5:0x3005].hex()}
        require(actual == expected, 'Persisted native name fields differ')
    return slots


def gameplay_save(rom, build, output, japanese=False):
    observations = []
    help_active = help_done = False
    help_pointer = (0x0806B0E8 if japanese else 0x08000000 + next(
        e['rom_offset'] for e in build['dialogue']['entries'] if e['id'] == 'rom.0006b0e8'))
    name_ids = bytes.fromhex('759e656b010101010000000000000000') if japanese else indexed('Torneko')
    player = 'トルネコ'.encode('cp932') + b'\0' if japanese else encode('Torneko')
    expected = expected_fields(name_ids, player)
    with Session(rom, output) as game:
        def callback(event):
            nonlocal help_active, help_done
            regs, address = event['registers'], event['address']
            if address == 0x080021B4:
                help_active = regs[1] == help_pointer
                return
            if address == 0x08002284:
                if help_active:
                    help_done, help_active = True, False
                return
            observation = {'frame': event['frame'], 'address': address, 'registers': regs}
            if address == 0x08015354:  # After state serialization, before save-body encoding.
                observation['fields'] = save_fields(game.core.memory, regs[0])
                require(observation['fields'] == expected, 'Serialized name fields differ')
            observations.append(observation)
        with Debugger(game, callback) as debugger:
            for address in (0x08015354, 0x08004480, 0x0800453E):
                debugger.breakpoint(address)
            if not japanese:
                debugger.breakpoint(0x080021B4)
                debugger.breakpoint(0x08002284)
            if japanese:
                for step in json.loads((ROOT / 'config/routes/opening.json').read_text())['steps']:
                    if 'frames' in step:
                        game.frames(step['frames'])
                    elif 'press' in step:
                        game.press(step['press'], wait=step.get('wait', 120), hold=step.get('hold', 3))
                    elif step['capture'] == 'first-dungeon':
                        break
            else:
                open_editor(game)
                route = NameEntryRoute(game, build['name_entry']['keyboard_pages'])
                route.clear()
                route.enter('Torneko')
                game.capture('entered-Torneko')
                route.confirm()
                game.frames(600)
                for _ in range(160):
                    game.press('A', wait=240)
                    if help_done:
                        break
                require(help_done, 'English opening did not finish first-floor help')
                game.press('A', wait=120)
            game.capture('first-dungeon')
            path = walk_to_stairs(game)
            save_at_stairs(game)
            battery = battery_snapshot(game.core)
        require(any(o['address'] == 0x08015354 for o in observations), 'Game save routine was not reached')
        slots = verify_battery(battery, expected)
        schedule = game.inputs
    require(game.disk_save == battery, 'Native disk save differs from cartridge battery')
    (output / 'native-save.sav').write_bytes(battery)
    return battery, expected, {'passed': True, 'normal_inputs': schedule, 'walk': path,
                              'native_save_calls': observations, 'complete_flash_slots': slots,
                              'battery_sha256': digest(battery), 'native_disk_save_exact': True}


def cold_load(rom, battery, expected, output):
    restored = []
    help_active = help_done = False
    help_pointer = int.from_bytes(rom[0x14723C:0x147240], 'little')
    with Session(rom, output, initial_save=battery) as game:
        def callback(event):
            nonlocal help_active, help_done
            if event['address'] == 0x080021B4:
                help_active = event['registers'][1] == help_pointer
                return
            if event['address'] == 0x08002284:
                if help_active:
                    help_done, help_active = True, False
                return
            # Native title-menu call after the main record has been decoded.
            fields = save_fields(game.core.memory, event['registers'][0])
            require(fields == expected, 'Cold-loaded decoded record differs')
            restored.append({'frame': event['frame'], 'fields': fields})
        with Debugger(game, callback) as debugger:
            debugger.breakpoint(0x08014FF2)
            debugger.breakpoint(0x080021B4)
            debugger.breakpoint(0x08002284)
            game.frames(600)
            game.press('START', wait=180)
            game.capture('loaded-menu')
            require(bytes(game.core.memory[STORED:STORED + 16]).hex() == expected['indexed_header'],
                    'Loaded preview indexed name differs')
            for i in range(16):
                game.press('A', wait=600)
                game.capture('resume-' + str(i))
                if help_done:
                    break
            require(help_done, 'Cold resume did not finish second-floor help')
            require(restored, 'Native main-record restore was not reached')
            require(bytes(game.core.memory[STORED:STORED + 16]).hex() == expected['indexed_body'] and
                    bytes(game.core.memory[HERO:HERO + 16]).hex() == expected['player_body'],
                    'Resumed RAM name fields differ')
            game.press('A', wait=120)  # Close the final tutorial page.
            before = position(game)
            for key in ('LEFT', 'RIGHT', 'UP', 'DOWN'):
                game.press(key, wait=120)
                if position(game) != before:
                    break
            require(position(game) != before, 'No normal movement after cold resume')
            game.capture('resumed-movement')
            slots = verify_battery(battery_snapshot(game.core), expected)
        return {'passed': True, 'native_restores': restored, 'normal_inputs': game.inputs,
                'movement_before': before, 'movement_after': position(game),
                'complete_flash_slots_after_resume': slots}


def run(output=OUTPUT):
    mgba.log.silence()
    original = load_base()
    save_hash = digest(default_rom().with_suffix('.sav').read_bytes())
    rom, build = build_rom()
    output.mkdir(parents=True, exist_ok=True)
    editor = input_checks(rom, build, output / 'editor')
    print('English keyboard, native glyphs, cursor, guards and player editor passed', flush=True)
    battery, expected, saved = gameplay_save(rom, build, output / 'english-save')
    loaded = cold_load(rom, battery, expected, output / 'english-cold')
    print('English native save and cold gameplay resume passed', flush=True)
    japanese, jp_expected, jp_saved = gameplay_save(original, None, output / 'japanese-save', japanese=True)
    compatibility = cold_load(rom, japanese, jp_expected, output / 'japanese-save-in-english')
    require(digest(load_base()) == digest(original) and
            digest(default_rom().with_suffix('.sav').read_bytes()) == save_hash, 'Original files changed')
    result = {'passed': True, 'source_rom_sha256': digest(original), 'output_rom_sha256': digest(rom),
              'source_save_sha256': save_hash, 'original_files_unchanged': True, 'emulator': version(), 'bios': BIOS,
              'editor': editor, 'english_save': saved, 'english_cold_load': loaded,
              'japanese_native_save': jp_saved, 'japanese_save_in_english': compatibility,
              'scope': 'Shared English and conditional player editors; normal first-floor save/suspend, '
                       'cold second-floor resume and movement; one native Japanese save imported. '
                       'All later name contexts, item-specific naming mechanics and full gameplay remain broader playtest work.'}
    (output / 'report.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'passed': True, 'characters': len(CHARACTERS), 'cold_gameplay_resume': True,
                      'japanese_save_compatible_on_tested_route': True, 'original_files_unchanged': True}))
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=OUTPUT)
    run(parser.parse_args().output.resolve())
