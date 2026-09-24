"""Equipment text must not alter other shared readers or native output frames."""
import struct,unittest
from tools.rom import load_base
from tools.rom_build import RomBuild
from tools.inventory_action_text import add_actions,OWNERS
from tools.extract_shared_text import START,END

class InventoryActionText(unittest.TestCase):
    def test_private_reads_preserve_unowned_table_and_consumer_code(self):
        original=load_base();build=RomBuild(original);report=add_actions(build);rom,_=build.finish()
        self.assertEqual(rom[START:END],original[START:END])
        self.assertEqual({p['start'] for p in build.patches},set(OWNERS))
        copied=bytearray(rom[report['table_offset']:report['table_offset']+END-START])
        for row in report['entries']:
            slot=row['table_offset']
            self.assertEqual(struct.unpack_from('<I',copied,slot)[0],row['offset']+0x08000000)
            copied[slot:slot+4]=original[START+slot:START+slot+4]
            self.assertLessEqual(row['maximum_bytes'],192)
            self.assertLessEqual(max(row['maximum_line_widths']),216)
        self.assertEqual(copied,original[START:END])
        # Ground-removal fragment090 remains owned by its original source.
        self.assertEqual(rom[0x24930:0x24934],original[0x24930:0x24934])
        restored=bytearray(rom[0x246FC:0x24F88])
        for site in OWNERS:restored[site-0x246FC:site-0x246FC+4]=original[site:site+4]
        self.assertEqual(restored,original[0x246FC:0x24F88])

    def test_pickup_changes_only_the_owned_walk_literal_and_no_other_actions(self):
        from tools.pickup_text import add_pickup,OWNERS as pickup_owners
        original=load_base();build=RomBuild(original);report=add_pickup(build);rom,_=build.finish()
        self.assertEqual({p['start'] for p in build.patches},set(pickup_owners))
        copied=bytearray(rom[report['table_offset']:report['table_offset']+END-START])
        for row in report['entries']:
            slot=row['table_offset'];copied[slot:slot+4]=original[START+slot:START+slot+4]
            self.assertLessEqual(row['maximum_bytes'],192)
        self.assertEqual(copied,original[START:END])
        self.assertEqual(rom[START:END],original[START:END])
        wrapper=bytearray(rom[0x249DC:0x24AD8])
        wrapper[0x24AC0-0x249DC:0x24AC4-0x249DC]=original[0x24AC0:0x24AC4]
        self.assertEqual(wrapper,original[0x249DC:0x24AD8])
        self.assertEqual(rom[0x24E70:0x257F8],original[0x24E70:0x257F8])
