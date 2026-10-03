import struct
import unittest

from tools.custom_item_text import CATEGORY_READERS, add_custom_items
from tools.extract_item_aliases import END
from tools.rom import load_base
from tools.rom_build import RomBuild


class CustomItems(unittest.TestCase):
    def test_private_table_preserves_shared_original_and_all_categories(self):
        build = RomBuild(load_base())
        report = add_custom_items(build)
        rom, ledger = build.finish()
        self.assertEqual(rom[END:END+56], build.original[END:END+56])
        self.assertEqual(len(ledger['patches']), 6)
        for row in report['entries']:
            if 'category' in row:
                pointer = struct.unpack_from('<I', rom, report['table_offset']+4*row['category'])[0]
                self.assertEqual(pointer, row['offset']+0x08000000)
        for site in CATEGORY_READERS:
            self.assertEqual(struct.unpack_from('<I', rom, site)[0], report['table_offset']+0x08000000)

    def test_rejects_conflicting_owner(self):
        build = RomBuild(load_base())
        site = CATEGORY_READERS[0]
        build.patch('other-owner', site, build.original[site:site+4], b'\0'*4, 'fixture')
        with self.assertRaises(ValueError):
            add_custom_items(build)
