"""Unidentified display insertion must not change assignment metadata."""
import struct,unittest
from tools.rom import load_base
from tools.rom_build import RomBuild
from tools.item_alias_text import add_aliases
from tools.extract_item_aliases import START,END

class ItemAliasText(unittest.TestCase):
    def test_private_names_preserve_assignment_table_and_end_marker(self):
        original=load_base();build=RomBuild(original);report=add_aliases(build);rom,_=build.finish()
        self.assertEqual(rom[START:END],original[START:END])
        self.assertEqual(rom[0x9FD8:0x9FDC],original[0x9FD8:0x9FDC])
        self.assertEqual({p['start'] for p in build.patches},{0xF628,0xF64C,0xF684})
        offset=report['table_offset'];copied=rom[offset:offset+END-START]
        for row in report['entries']:
            start=row['id']*24
            self.assertEqual(copied[start+4:start+24],original[START+start+4:START+start+24])
            self.assertEqual(struct.unpack_from('<I',copied,start)[0],row['offset']+0x08000000)
        self.assertEqual(copied[154*24:],original[START+154*24:END])
        self.assertEqual(len(report['entries']),154)
