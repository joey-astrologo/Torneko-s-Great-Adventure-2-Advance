import struct,unittest
from tools.rom import load_base
from tools.rom_build import RomBuild
from tools.dungeon_travel_text import add_dungeon_travel
class DungeonTravelOwnershipTest(unittest.TestCase):
 def test_private_picker_preserves_other_travel_consumers(self):
  base=load_base();b=RomBuild(base);r=add_dungeon_travel(b);rom,ledger=b.finish();self.assertTrue(ledger['unowned_original_bytes_preserved']);self.assertEqual({p['start'] for p in ledger['patches']},{0x52420,0x523B8});self.assertEqual(rom[0x14D71C:0x14D738],base[0x14D71C:0x14D738]);table=r['table_offset'];self.assertEqual(struct.unpack_from('<7I',rom,table),tuple(e['offset']+0x08000000 for e in r['entries'][:7]));self.assertEqual(struct.unpack_from('<I',rom,0x523B8)[0],r['entries'][7]['offset']+0x08000000)
