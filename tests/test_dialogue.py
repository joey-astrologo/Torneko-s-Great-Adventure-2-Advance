"""Reject unsafe dialogue edits and verify relocation leaves unrelated data intact."""

from copy import deepcopy
import json
import unittest
from unittest.mock import patch

from tools.build_english import build_rom
from tools.build_dialogue import CATALOG
from tools.dialogue_layout import compile_dialogue
from tools.event_text import table_entries
from tools.dialogue_checks import rendered_codes
from tools.home_sale import ENGLISH, ORIGINAL, compile_sale, materialize
from tools.lz77 import decompress, pack_literals
from tools.opening_text import BANK_RAM, banks
from tools.text_codec import tokenize
from tools.book_text import OVERWRITE, compile_overwrite, materialize as overwrite_message
from tools.town_text import RAM as TOWN_RAM, resource as town_resource, entries as town_entries, relocate


class DialogueTest(unittest.TestCase):
    def test_initial_control_retains_order_and_widest_name_reserve(self):
        source = tokenize(b'\x14\x7f\x7e\0')[0]
        payload, layout = compile_dialogue('{center}{initial}-{player}!', source)
        self.assertEqual(layout['commands'], ['{center}', '{initial}', '{player}'])
        self.assertEqual(layout['line_widths'], [[124]])  # 14 + 98 + two six-pixel marks.
        name = 'げ'.encode('cp932') * 7 + b'\0'
        codes = rendered_codes(payload, name)
        self.assertEqual(codes, [0x82B0, 0xF02D] + [0x82B0] * 7 + [0xF021])
        for text in ('{center}{player}!', '{center}{player}-{initial}!',
                     '{center}{initial}-{initial}-{player}!'):
            with self.assertRaises(ValueError):
                compile_dialogue(text, source)
        for name in (None, b'\0', b'T\0'):
            with self.assertRaises(ValueError):
                rendered_codes(payload, name)

    def test_unlock_command_preserves_control_sequence(self):
        source = tokenize(b'\x14@A@\x7e\r\x14\0')[0]
        payload, layout = compile_dialogue('{center}@A@{player}\n{center}can now visit Mt. Fiery!', source)
        self.assertEqual(payload[:5], b'\x14@A@\x7e')
        self.assertEqual(layout['commands'], ['{center}', '@A@', '{player}', '{center}'])
        for text in ('{center}{player}\n{center}Go!',
                     '{center}@B@{player}\n{center}Go!',
                     '{center}{player}@A@\n{center}Go!'):
            with self.assertRaises(ValueError):
                compile_dialogue(text, source)

    def test_two_centered_lines_preserve_name_and_one_page(self):
        source = tokenize(b'\x14\x7e\r\x14' + '金庫'.encode('cp932') + b'\0')[0]
        payload, layout = compile_dialogue('{center}{player}\n{center}recovered the banker\'s safe!', source)
        self.assertEqual(layout['pages'], [['{center}{player}', "{center}recovered the banker's safe!"]])
        self.assertEqual(layout['line_widths'][0][0], 98)
        self.assertEqual(payload[:4], b'\x14\x7e\x0d\x14')
        for bad in ('{center}{player}\ntext {center}safe',
                    '{center}{player}\nplain\n{center}safe'):
            with self.assertRaises(ValueError):
                compile_dialogue(bad, source)

    def test_centering_controls_keep_count_and_whole_line_fit(self):
        source = tokenize(b'\x14' + '本'.encode('cp932') + b'\r\x14' + '王'.encode('cp932') + b'\0')[0]
        payload, layout = compile_dialogue('{center}Book\n\n{center}By the King', source)
        self.assertEqual(payload.count(b'\x14'), 2)
        self.assertEqual(len(layout['pages']), 2)
        for text in ('Book\n\n{center}By the King', 'A {center}Book\n\n{center}King',
                     '{center}' + 'Wide ' * 30 + '\n\n{center}King'):
            with self.subTest(text=text), self.assertRaises(ValueError):
                compile_dialogue(text, source)

    def test_town_pointer_relocation_preserves_unowned_bytes(self):
        rom, report = build_rom()
        resource = report['dialogue']['town_resource']
        decoded, _ = decompress(rom, resource['rom_offset'])
        original = town_resource()['data']
        restored = bytearray(decoded)
        relocated = relocate(decoded)
        targets = {row['id']:0x08000000 + row['rom_offset'] for row in report['dialogue']['entries']}
        service_targets = {row['slot']:0x08000000 + row['offset'] for row in resource['service_entries']}
        service_targets.update({row['slot']:0x08000000+row['offset'] for row in resource['bakery_entries']})
        service_targets.update({slot:0x08000000+row['offset'] for row in resource['storage_entries'] for slot in row['slots']})
        self.assertEqual(len(original), len(decoded))
        for row in town_entries():
            actual = int.from_bytes(relocated[row['slot']:row['slot'] + 4], 'little')
            self.assertEqual(actual, service_targets.get(row['slot'], targets.get(row['id'], TOWN_RAM + row['start'])))
            if row['id'] in targets or row['slot'] in service_targets:
                restored[row['slot']:row['slot'] + 4] = original[row['slot']:row['slot'] + 4]
        self.assertEqual(restored, original)

    def test_overwrite_format_keeps_name_and_stack_bound(self):
        payload, layout = compile_overwrite(OVERWRITE)
        for name in (b'\xf0T\0', 'げ'.encode('cp932') * 7 + b'\0'):
            message = overwrite_message(payload, name)
            self.assertLessEqual(len(message), 128)
            self.assertIn(name.rstrip(b'\0'), message)
        self.assertLessEqual(layout['maximum_formatted_bytes'], 128)
        for name in (b'', b'\xf0A' * 8, b'\xf0A\0\xf0B'):
            with self.assertRaises(ValueError):
                overwrite_message(payload, name)
        with self.assertRaises(ValueError):
            compile_overwrite(OVERWRITE.replace('{village}', 'Torneko'))

    def test_literal_stream_boundaries(self):
        for size in (1, 7, 8, 9, 12_132):
            source = bytes(i % 256 for i in range(size))
            packed = pack_literals(source)
            self.assertEqual(decompress(packed), (source, len(packed)))
        with self.assertRaises(ValueError):
            pack_literals(b'')

    def test_command_and_glyph_changes_rejected(self):
        source = tokenize('ねえ'.encode('cp932') + b'@B@\r@C@\0')[0]
        compile_dialogue('Hello.@B@\n\nGoodbye.@C@', source)
        for english in ('Hello.', 'Hello.@C@@B@', 'Hello.@B@@B@@C@', 'Hello.@D@@B@@C@',
                        'Hello.@B@\n\nGoodbye.@C@\t\x01', 'Caf\u00e9@B@@C@'):
            with self.subTest(english=english), self.assertRaises(ValueError):
                compile_dialogue(english, source)
        with self.assertRaisesRegex(ValueError, 'insertion-ready'):
            compile_dialogue('Name', tokenize(b'\x1f\0')[0])

    def test_player_substitutions_keep_count_and_reserve_japanese_width(self):
        source = tokenize(b'\x7e\r\x7e\0')[0]
        payload, layout = compile_dialogue('Hello, {player}!\n\nGoodbye, {player}!', source)
        self.assertEqual(payload.count(b'\x7e'), 2)
        self.assertTrue(all(98 <= line <= 216 for page in layout['line_widths'] for line in page))
        for english in ('Hello!', 'Hello, {player}!', '{player}{player}{player}', '{village}{player}'):
            with self.assertRaises(ValueError):
                compile_dialogue(english, source)

    def test_long_word_and_empty_paragraph_rejected(self):
        for english in ('W' * 100, 'First\n\n\n\nLast', ''):
            with self.assertRaises(ValueError):
                compile_dialogue(english, [])

    def test_all_original_entry_addresses_preserved_except_selected(self):
        rom, report = build_rom()
        targets = {e['id']: 0x08000000 + e['rom_offset'] for e in report['dialogue']['entries']}
        originals = {b['id']: b for b in banks()}
        self.assertEqual({b['id'] for b in report['dialogue']['banks']}, {f'event-bank-{i}' for i in range(7)})
        for bank in report['dialogue']['banks']:
            decoded, _ = decompress(rom, bank['bank_rom_offset'])
            original = originals[bank['id']]['data']
            self.assertEqual(len(decoded), len(original))
            restored = bytearray(decoded)
            for row in table_entries(originals[bank['id']]):
                slot = row['slot']
                resolved = BANK_RAM + row['strings_offset'] + row['group_offset'] + int.from_bytes(decoded[slot:slot + 4], 'little')
                self.assertEqual(resolved, targets.get(row['id'], BANK_RAM + row['start']))
                if row['id'] in targets:
                    restored[slot:slot + 4] = original[slot:slot + 4]
            self.assertEqual(restored, original)

    def test_native_colors_and_heart_cannot_be_dropped_or_introduced(self):
        source = tokenize(b'\x03\x06' + '本'.encode('cp932') + b'\x05\x87\x4e\0')[0]
        payload, layout = compile_dialogue('{color:6}Book{/color}{heart}', source)
        expected = [(0xF000 + ord(c), 14) for c in 'Book'] + [(0x874E, 15)]
        self.assertEqual(rendered_codes(payload, foreground=15, saved=8), expected)
        self.assertEqual(layout['line_widths'], [[37]])  # T2 Book (24) + original heart (13).
        for text in ('Book{heart}', '{color:6}Book{/color}', '{heart}{color:6}Book{/color}',
                     '{color:5}Book{/color}{heart}', '{color:6}Book{/color}{heart}{heart}'):
            with self.subTest(text=text), self.assertRaises(ValueError):
                compile_dialogue(text, source)
        for raw in (b'\x03\x04A\x05\0', b'\x05\0', b'\x03\x06A\0', b'\x03\x06\x03\x06A\x05\x05\0'):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                compile_dialogue('A', tokenize(raw)[0])

    def test_status_skill_palette_restores_the_original_foreground(self):
        payload=bytes.fromhex('0303f04105f04200')
        self.assertEqual(rendered_codes(payload,foreground=15,saved=8),[(0xF041,11),(0xF042,15)])

    def test_dynamic_sale_keeps_amount_and_original_buffer_bound(self):
        template, layout = compile_sale(ENGLISH)
        for amount in (0, 1, 9, 10, 100, 999999, 0x7FFFFFFF):
            encoded = materialize(template, amount)
            self.assertLessEqual(len(encoded), len(materialize(ORIGINAL, amount)))
            codes = rendered_codes(encoded, bytes.fromhex('f05400'), foreground=15, saved=8)
            self.assertEqual([code for code, color in codes if color == 13],
                             [ord(c) + 0x821F for c in str(amount)])
        for amount in (-1, 0x80000000):
            with self.assertRaises(ValueError):
                materialize(template, amount)
        with self.assertRaises(ValueError):
            compile_sale(ENGLISH.replace('{amount}', '100'))
        self.assertTrue(layout['output_never_longer_for_same_argument'])

    def test_stale_source_and_unreviewed_english_rejected(self):
        original = json.loads(CATALOG.read_text())
        for field, value in (('raw_hex', '00'), ('language_status', 'draft')):
            catalog = deepcopy(original)
            row = next(e for e in catalog['entries'] if e.get('batch') == 'opening-dialogue')
            row[field] = value
            from tools.build_dialogue import add_dialogue
            from tools.rom_build import RomBuild
            from tools.rom import load_base
            build = RomBuild(load_base())
            with patch('tools.build_dialogue.json.loads', return_value=catalog), self.assertRaises(ValueError):
                add_dialogue(build)
