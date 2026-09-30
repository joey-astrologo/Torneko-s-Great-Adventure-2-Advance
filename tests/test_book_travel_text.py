"""Private menu-pointer ownership and saved-name/control preservation."""
import struct,unittest
from tools.rom import load_base
from tools.rom_build import RomBuild
from tools.book_travel_text import add_book_travel

class BookTravelOwnershipTest(unittest.TestCase):
    def test_only_owned_readers_change_and_saved_name_control_survives(self):
        original=load_base();build=RomBuild(original);resource=add_book_travel(build);rom,ledger=build.finish()
        self.assertTrue(ledger['unowned_original_bytes_preserved'])
        self.assertEqual({p['start'] for p in ledger['patches']},{0x50AC4,0x50B1C,0x50B7C,0x5256C,0x52574,0x5271C,0x5263C,0x52714})
        for lo,hi in [(0x14D340,0x14D354),(0x14D70C,0x14D718),(0x14BCE4,0x14BCE8)]:
            self.assertEqual(rom[lo:hi],original[lo:hi])
        by_id={r['id']:r for r in resource['entries']}
        private=struct.unpack_from('<I',rom,0x50B1C)[0]-0x08000000
        self.assertEqual(struct.unpack_from('<5I',rom,private),tuple(by_id['book.'+key]['offset']+0x08000000 for key in ('records','scores','records','scores','trade')))
        self.assertEqual(struct.unpack_from('<I',rom,0x50AC4)[0],private+8+0x08000000)
        overwrite=bytes.fromhex(by_id['travel.overwrite']['encoded_hex'])
        self.assertEqual(overwrite.count(b'\x1f'),1)
        self.assertEqual(overwrite.count(b'\x14'),2)
        self.assertEqual(by_id['travel.overwrite']['line_widths'],[189,142])
