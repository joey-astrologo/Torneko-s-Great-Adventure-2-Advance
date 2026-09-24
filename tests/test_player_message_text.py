"""Ownership and argument-safety boundaries for the player-only formatter."""
import json
import struct
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from tools import player_message_text as messages
from tools.rom import load_base
from tools.rom_build import RomBuild


class PlayerMessageText(unittest.TestCase):
    def test_only_entry_is_patched_and_map_is_exact(self):
        original = load_base()
        build = RomBuild(original)
        report = messages.add_player_messages(build)
        rom, ledger = build.finish()
        self.assertEqual([(p['start'], p['end_exclusive']) for p in ledger['patches']], [(0x15848, 0x15850)])
        self.assertEqual(rom[:0x15848], original[:0x15848])
        self.assertEqual(rom[0x15850:len(original)], original[0x15850:])
        table = report['mapping_offset']
        actual = [struct.unpack_from('<II', rom, table + 8 * i) for i in range(33)]
        self.assertEqual(actual, [(r['source']['offset'] + 0x08000000, r['offset'] + 0x08000000) for r in report['entries']])

    def test_cannot_drop_a_player_argument_or_overflow_a_line(self):
        original = json.loads(messages.CATALOG.read_text())
        for english, error in [('Recovered.', 'source arguments'), ('{player} ' + 'W' * 50, 'width exceeds')]:
            catalog = json.loads(json.dumps(original))
            row = next(r for r in catalog['entries'] if '{player}' in r['english'])
            row['english'] = english
            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / 'catalog.json'
                path.write_text(json.dumps(catalog))
                with patch.object(messages, 'CATALOG', path), self.assertRaisesRegex(ValueError, error):
                    messages.add_player_messages(RomBuild(load_base()))
