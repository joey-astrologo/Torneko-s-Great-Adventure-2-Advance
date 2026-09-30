import struct,unittest
from tools.rom import load_base
from tools.rom_build import RomBuild
from tools.pickup_help_text import add_pickup_help,SOURCES
class PickupHelpOwnershipTest(unittest.TestCase):
 def test_dispatch_and_original_sources_preserved(self):
  original=load_base();b=RomBuild(original);r=add_pickup_help(b);rom,ledger=b.finish();self.assertTrue(ledger['unowned_original_bytes_preserved']);self.assertEqual({p['start'] for p in ledger['patches']},set(SOURCES));self.assertEqual(len(r['entries']),8)
  for e in r['entries']:
   a,z=e['source']['offset'],e['source']['end_exclusive'];self.assertEqual(rom[a:z],original[a:z]);self.assertEqual(struct.unpack_from('<I',rom,e['literal_offset'])[0],e['offset']+0x08000000);raw=bytes.fromhex(e['encoded_hex']);self.assertEqual(raw.count(b'\x09'),original[a:z].count(b'\x09'));self.assertEqual(raw.startswith(b'\r'),original[a:z].startswith(b'\r'));self.assertLessEqual(e['layout']['maximum_combined_queue_bytes'],1024)
