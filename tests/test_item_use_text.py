"""Guard the halfword-aligned use-message trampoline and private source table."""
import struct,unittest
from tools.rom import load_base
from tools.rom_build import RomBuild
from tools.item_use_text import add_item_use
from tools.extract_item_use import START,END

class ItemUseText(unittest.TestCase):
    def test_literal_alignment_and_private_category_mapping(self):
        base=load_base();build=RomBuild(base);report=add_item_use(build);rom,_=build.finish()
        self.assertEqual(rom[START:END],base[START:END])
        self.assertEqual({(p['start'],p['end_exclusive']) for p in build.patches},
                         {(0x2585A,0x25864),(0x258D0,0x258D4)})
        instruction=struct.unpack_from('<H',rom,0x2585A)[0]
        self.assertEqual(instruction&0xFF00,0x4B00)
        literal=((0x2585A+4)&~3)+(instruction&255)*4
        self.assertEqual(literal%4,0)
        self.assertEqual(struct.unpack_from('<I',rom,literal)[0],0x08000001+report['helper_offset'])
        for row in report['entries']:
            for category in row['categories']:
                self.assertEqual(struct.unpack_from('<I',rom,report['table_offset']+category*4)[0],
                                 row['offset']+0x08000000)
