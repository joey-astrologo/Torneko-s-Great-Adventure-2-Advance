"""Keep shared property text owned by its original readers."""
import struct,unittest
from tools.rom import load_base
from tools.rom_build import RomBuild
from tools.ability_info_text import add_ability_info
from tools.extract_shared_text import START,END

class AbilityInfoOwnershipTest(unittest.TestCase):
 def test_private_tables_preserve_other_consumers_and_special_slot(self):
  base=load_base();build=RomBuild(base);resource=add_ability_info(build);rom,ledger=build.finish()
  self.assertTrue(ledger['unowned_original_bytes_preserved'])
  self.assertEqual({p['start'] for p in ledger['patches']},{0x17CA4,0x17CC8})
  self.assertEqual(rom[0x1447A8:0x1448E8],base[0x1447A8:0x1448E8])
  self.assertEqual(rom[START:END],base[START:END])
  pointer=struct.unpack_from('<I',rom,0x17CA4)[0]-0x08000000
  self.assertEqual(struct.unpack_from('<40I',rom,pointer),tuple(r['offset']+0x08000000 for r in resource['entries'][:40]))
  alternate=struct.unpack_from('<I',rom,0x17CC8)[0]-0x08000000
  expected=bytearray(base[START:END]);struct.pack_into('<I',expected,0x9FC,resource['entries'][40]['offset']+0x08000000)
  self.assertEqual(rom[alternate:alternate+END-START],expected)
