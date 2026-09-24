"""Synthesis menu/format limits and isolated item-selector ownership."""
import json
import struct
import unittest
from tools.rom import load_base
from tools.rom_build import RomBuild
from tools.gaibara_text import CATALOG, INDICES, add_gaibara, compile_row
from tools.selection_prompt_text import add_selection_prompt
from tools.town_text import entries, RAM
from tools.extract_shared_text import START, END


class GaibaraText(unittest.TestCase):
    def test_private_sources_and_selector_do_not_change_shared_tables(self):
        original = load_base(); build = RomBuild(original)
        service = add_gaibara(build); heading = add_selection_prompt(build)
        rom, ledger = build.finish()
        self.assertEqual({(p['start'], p['end_exclusive']) for p in ledger['patches']}, {(0x1D544,0x1D54C),(0x1DDE4,0x1DDE8)})
        self.assertEqual(rom[START:END], original[START:END])
        selected = {r['index']: r['offset'] + 0x08000000 for r in service['entries']}
        self.assertEqual(set(selected), INDICES)
        self.assertEqual(struct.unpack_from('<300I', rom, service['table_offset']),
                         tuple(selected.get(r['index'], RAM + r['start']) for r in entries()))
        self.assertEqual(struct.unpack_from('<6I', rom, heading['table_offset']), (0,0,0,0,0,heading['entries'][0]['offset'] + 0x08000000))

    def test_menu_reserve_and_format_arguments(self):
        rows = {r['index']: r for r in json.loads(CATALOG.read_text())['entries']}; sources = entries()
        payload, layout = compile_row(rows[112], sources[112])
        self.assertEqual(layout['text_budget'], 60)
        self.assertTrue(all(line.startswith(b'  ') for line in payload[:-1].split(b'\r')))
        with self.assertRaisesRegex(ValueError, 'choices'):
            compile_row(rows[112] | {'english': ['Synthesise', 'Leave', 'Explain']}, sources[112])
        with self.assertRaisesRegex(ValueError, 'roles/order'):
            compile_row(rows[114] | {'english': 'Gaibara: Make this the base?'}, sources[114])
        with self.assertRaisesRegex(ValueError, 'byte capacity'):
            compile_row(rows[113] | {'english': rows[113]['english'] + '\n\n' + 'More text. ' * 30}, sources[113])
        payload, layout = compile_row(rows[52], sources[52])
        self.assertIn(b'\x03\x05%d\x05', payload)
        self.assertLessEqual(layout['maximum_formatted_bytes'], 256)
