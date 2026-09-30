import struct,unittest
from tools.rom import load_base
from tools.rom_build import RomBuild
from tools.travel_confirm_text import add_travel_confirm,SITES
class TravelConfirmOwnershipTest(unittest.TestCase):
 def test_shared_prompts_owned_readers_and_saved_name_controls(self):
  original=load_base();b=RomBuild(original);r=add_travel_confirm(b);rom,ledger=b.finish();self.assertEqual({p['start'] for p in ledger['patches']},{site for sites in SITES.values() for site in sites})
  for e in r['entries']:
   a,z=e['source']['offset'],e['source']['end_exclusive'];self.assertEqual(rom[a:z],original[a:z]);raw=bytes.fromhex(e['encoded_hex']);self.assertEqual(raw.count(b'\x1f'),original[a:z].count(b'\x1f'));self.assertEqual(raw.count(b'\x14'),original[a:z].count(b'\x14'));self.assertLessEqual(max(e['layout']['line_widths'][0]),216);self.assertEqual(len(e['layout']['pages']),1)
   for site in e['literals']:self.assertEqual(struct.unpack_from('<I',rom,site)[0],e['offset']+0x08000000)
