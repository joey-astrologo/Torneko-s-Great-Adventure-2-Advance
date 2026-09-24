"""A private effect table must preserve all unrelated shared consumers."""
import struct
import unittest
from tools.rom import load_base
from tools.rom_build import RomBuild
from tools.player_effect_text import add_effects, OWNERS
from tools.extract_shared_text import START, END

class PlayerEffectText(unittest.TestCase):
    def test_only_owned_literals_and_table_slots_change(self):
        original=load_base();build=RomBuild(original);report=add_effects(build);rom,_=build.finish()
        self.assertEqual(rom[START:END],original[START:END])
        self.assertEqual({p['start'] for p in build.patches},set(OWNERS))
        copied=bytearray(rom[report['table_offset']:report['table_offset']+END-START])
        for row in report['entries']:
            slot=row['table_offset']
            self.assertEqual(struct.unpack_from('<I',copied,slot)[0],row['offset']+0x08000000)
            copied[slot:slot+4]=original[START+slot:START+slot+4]
            self.assertLessEqual(row['maximum_width'],216)
            self.assertLessEqual(row['maximum_bytes'],256)
        self.assertEqual(copied,original[START:END])
        self.assertEqual(rom[0xB760:0xB764],original[0xB760:0xB764])
