"""Blacksmith table isolation and the original formatter capacity."""
import json
import struct
import unittest
from tools.blacksmith_text import CATALOG, INDICES, add_blacksmith, compile_row
from tools.rom import load_base
from tools.rom_build import RomBuild
from tools.town_text import entries, RAM


class BlacksmithText(unittest.TestCase):
    def test_unowned_town_slots_keep_original_runtime_pointers(self):
        original = load_base(); build = RomBuild(original)
        report = add_blacksmith(build); rom, ledger = build.finish()
        self.assertEqual([(p['start'], p['end_exclusive']) for p in ledger['patches']], [(0x1D110, 0x1D118)])
        table = struct.unpack_from('<300I', rom, report['table_offset'])
        selected = {r['index']: r['offset'] + 0x08000000 for r in report['entries']}
        self.assertEqual(set(selected), INDICES)
        self.assertEqual(table, tuple(selected.get(r['index'], RAM + r['start']) for r in entries()))

    def test_reversed_items_and_oversized_formatted_prose_are_rejected(self):
        rows = json.loads(CATALOG.read_text())['entries']; sources = entries()
        row = next(r for r in rows if r['index'] == 61)
        reversed_text = row['english'].replace('{item1}', '{temporary}').replace('{item2}', '{item1}').replace('{temporary}', '{item2}')
        with self.assertRaisesRegex(ValueError, 'argument roles'):
            compile_row(row | {'english': reversed_text}, sources[61])
        row = next(r for r in rows if r['index'] == 70)
        with self.assertRaisesRegex(ValueError, '512-byte'):
            compile_row(row | {'english': row['english'] + '\n\n' + 'Additional prose. ' * 30}, sources[70])
