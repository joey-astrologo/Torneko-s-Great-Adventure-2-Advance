import struct,unittest
from tools.rom import load_base
from tools.rom_build import RomBuild
from tools.dungeon_story_text import add_dungeon_story

class DungeonStoryOwnershipTest(unittest.TestCase):
 def test_owned_consumers_and_page_colours(self):
  base=load_base();build=RomBuild(base);resource=add_dungeon_story(build);rom,ledger=build.finish();table=resource['table_offset']
  self.assertTrue(ledger['unowned_original_bytes_preserved'])
  self.assertEqual({p['start'] for p in ledger['patches']},{0x1BE10,0x1C198,0x1C278,0x1C530})
  self.assertEqual(rom[0x1471D4:0x147234],base[0x1471D4:0x147234])
  for offset in (0,40,80):self.assertEqual(rom[table+offset:table+offset+4],base[0x1471D4+offset:0x1471D8+offset])
  for row in resource['entries']:
   self.assertEqual(struct.unpack_from('<I',rom,table+4*(row['index']+1))[0],row['offset']+0x08000000)
   if row['index'] in (1,6,7,16,17):
    raw=bytes.fromhex(row['encoded_hex']);self.assertEqual(raw.count(b'\x03\x06'),len(row['layout']['pages']))
    self.assertEqual(raw.count(b'\x03\x06'),bytes.fromhex(row['source']['raw_hex']).count(b'\x03\x06'))
