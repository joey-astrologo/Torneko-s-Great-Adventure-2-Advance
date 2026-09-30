import struct,unittest
from tools.rom import load_base
from tools.rom_build import RomBuild
from tools.travel_gate_text import add_travel_gate
class TravelGateOwnershipTest(unittest.TestCase):
 def test_private_pointers_preserve_shared_scratch_neighbors(self):
  base=load_base();build=RomBuild(base);resource=add_travel_gate(build);rom,ledger=build.finish()
  self.assertTrue(ledger['unowned_original_bytes_preserved'])
  self.assertEqual({p['start'] for p in ledger['patches']},{0x4BD04,0x4BD30,0x5222C})
  self.assertEqual(rom[0x14C8E4:0x14C8F4],base[0x14C8E4:0x14C8F4])
  private=struct.unpack_from('<I',rom,0x4BD04)[0]-0x08000000
  self.assertEqual(struct.unpack_from('<4I',rom,private),tuple(r['offset']+0x08000000 for r in resource['entries']))
  self.assertEqual(struct.unpack_from('<I',rom,0x4BD30)[0],private+4+0x08000000)
  self.assertEqual(struct.unpack_from('<I',rom,0x5222C)[0],private+12+0x08000000)
  self.assertLessEqual(max(r['maximum_bytes'] for r in resource['entries']),128)
