import struct,unittest
from tools.rom import load_base
from tools.rom_build import RomBuild
from tools.fire_scene_text import add_fire_scene,BASE,COUNT,STRIDE,EMPTY
class FireSceneOwnershipTest(unittest.TestCase):
 def test_indexed_sources_and_empty_records_preserved(self):
  original=load_base();b=RomBuild(original);r=add_fire_scene(b);rom,ledger=b.finish();self.assertEqual({p['start'] for p in ledger['patches']},{0x52DF4,0x52E34});self.assertEqual(rom[BASE:BASE+COUNT*256],original[BASE:BASE+COUNT*256]);self.assertEqual(struct.unpack_from('<I',rom,0x52E34)[0],r['table_offset']+0x08000000)
  instruction=struct.unpack_from('<H',rom,0x52DF4)[0];self.assertEqual(instruction>>11,0);self.assertEqual((instruction>>3)&7,5);self.assertEqual(instruction&7,0);self.assertEqual(1<<((instruction>>6)&31),STRIDE)
  for e in r['entries']:
   self.assertEqual(e['offset'],r['table_offset']+STRIDE*e['index']);raw=bytes.fromhex(e['encoded_hex']);self.assertEqual(rom[e['offset']:e['offset']+len(raw)],raw);self.assertLessEqual(len(raw),STRIDE);self.assertLessEqual(max(max(p) for p in e['layout']['line_widths']),216)
  for i in EMPTY:self.assertEqual(rom[r['table_offset']+i*STRIDE:r['table_offset']+(i+1)*STRIDE],b'\0'*STRIDE)
