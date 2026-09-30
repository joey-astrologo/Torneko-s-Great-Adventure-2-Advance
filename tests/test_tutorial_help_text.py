import struct,unittest
from tools.rom import load_base
from tools.rom_build import RomBuild
from tools.tutorial_help_text import add_tutorial_help
class TutorialHelpOwnershipTest(unittest.TestCase):
 def test_private_tables_preserve_original_selectors(self):
  base=load_base();b=RomBuild(base);r=add_tutorial_help(b);rom,ledger=b.finish();self.assertTrue(ledger['unowned_original_bytes_preserved']);self.assertEqual(rom[0x14CEFC:0x14D028],base[0x14CEFC:0x14D028]);self.assertEqual({p['start'] for p in ledger['patches']},{0x4F9F0,0x4FA1C,0x5103C,0x51088,0x4F9F4,0x4FA20,0x51040,0x5108C})
  self.assertEqual(len(r['entries']),104)
  self.assertEqual({g['index'] for g in r['groups']},set(range(27)))
  for binding in r['bindings']:
   for slot in range(binding['bytes']//4):
    original=base[binding['source_offset']+4*slot:binding['source_offset']+4*slot+4];actual=rom[binding['offset']+4*slot:binding['offset']+4*slot+4]
    if slot not in binding['changed_slots']:self.assertEqual(actual,original)
    else:self.assertGreaterEqual(int.from_bytes(actual,'little'),0x08000000+len(base))
 def test_equipment_cursor_reserve_is_independent_of_text_column_control(self):
  b=RomBuild(load_base());r=add_tutorial_help(b);cells=[e for e in r['entries'] if e.get('layout',{}).get('original_cursor_table')==0x14E4D0];self.assertTrue(cells)
  for e in cells:self.assertEqual(e['layout']['cursor_x'],[5,120]);self.assertEqual(e['layout']['cell_starts'],[11,128]);self.assertEqual(e['layout']['cell_budgets'],[109,96])
