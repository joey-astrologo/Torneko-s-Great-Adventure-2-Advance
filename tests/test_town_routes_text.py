import struct,unittest
from tools.rom import load_base
from tools.rom_build import RomBuild
from tools.compact_font import encode
from tools.town_routes_text import add_town_routes,BASE,END,SITES,INHERITED
class TownRoutesOwnershipTest(unittest.TestCase):
 def base(self):
  b=RomBuild(load_base())
  for i,ident in INHERITED.items():
   at=b.allocate(ident,encode('Owned label'),'dialogue');b.patch(ident+'-pointer',BASE+4*i,b.original[BASE+4*i:BASE+4*i+4],struct.pack('<I',at+0x08000000),'dialogue')
  return b
 def test_private_copy_preserves_sources_and_inherited_ownership(self):
  b=self.base();before=bytes(b.data[BASE:END]);r=add_town_routes(b);rom,ledger=b.finish();self.assertEqual(rom[BASE:END],before);self.assertEqual({p['start'] for p in ledger['patches'] if p['owner']=='town-routes'},set(SITES))
  for e in r['entries']:
   a,z=e['source']['offset'],e['source']['end_exclusive'];self.assertEqual(rom[a:z],b.original[a:z])
   for i in e['table_indices']:self.assertEqual(struct.unpack_from('<I',rom,r['table_offset']+4*i)[0],e['offset']+0x08000000)
  for i in INHERITED:self.assertEqual(rom[r['table_offset']+4*i:r['table_offset']+4*i+4],before[4*i:4*i+4])
 def test_rejects_changed_inherited_pointer(self):
  b=self.base();b.data[BASE+4]^=1
  with self.assertRaisesRegex(ValueError,'ownership'):add_town_routes(b)
