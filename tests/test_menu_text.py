"""Protect English menu bytes, isolated consumers and tile-sized budgets."""
import struct
import unittest
from tools.rom import load_base
from tools.rom_build import RomBuild
from tools.menu_text import add_menus,ACTIONS
from tools.compact_font import load_font,COMPACT_ASSET,measure

class MenuTextTest(unittest.TestCase):
    def test_complete_menu_buffers_and_other_consumers(self):
        base=load_base();build=RomBuild(base);report=add_menus(build);rom,ledger=build.finish()
        self.assertEqual(report['action_max_bytes_bound'],113)
        self.assertEqual(report['root_max_bytes_bound'],58)
        for site in (0x19680,0x1e560,0x1e62c):
            self.assertEqual(rom[site:site+4],base[site:site+4])
        self.assertEqual(rom[0x141904:0x1419b4],base[0x141904:0x1419b4])
        for site in (0x19d72,0x19474,0x19478):
            self.assertEqual(rom[site:site+2],base[site:site+2])
        table=report['action_table_offset']
        for i in range(44):
            if i not in ACTIONS:self.assertEqual(rom[table+i*4:table+i*4+4],base[0x141904+i*4:0x141904+i*4+4])
    def test_overwide_font_fails_before_insertion(self):
        font=load_font(COMPACT_ASSET)
        for glyph in font['glyphs'].values():glyph['advance']=12
        with self.assertRaisesRegex(ValueError,'exceeds'):
            add_menus(RomBuild(load_base()),font)
    def test_t2_default_and_known_tight_labels(self):
        self.assertEqual(load_font(),load_font(COMPACT_ASSET))
        self.assertEqual(measure('Remove'),36)
        self.assertTrue(all(measure(label)<=36 for label in ACTIONS.values()))
