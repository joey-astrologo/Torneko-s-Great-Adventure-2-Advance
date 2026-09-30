import json,struct,unittest
from tools.rom import load_base
from tools.rom_build import RomBuild
from tools.ending_text import add_ending,compile_ending,CATALOG,TABLE,END
from tools.text_codec import tokenize

class EndingOwnershipTest(unittest.TestCase):
 def test_descriptor_timing_flags_sentinel_and_private_consumers(self):
  base=load_base();b=RomBuild(base);r=add_ending(b);rom,ledger=b.finish();table=r['table_offset'];self.assertTrue(ledger['unowned_original_bytes_preserved']);self.assertEqual(rom[TABLE:END],base[TABLE:END]);self.assertEqual({p['start'] for p in ledger['patches']},{0x55920,0x559B8,0x55A3C,0x55AD8,0x55B7C})
  for i in range(58):
   self.assertEqual(rom[table+12*i+4:table+12*i+12],base[TABLE+12*i+4:TABLE+12*i+12])
  self.assertEqual(rom[table+43*12:table+44*12],base[TABLE+43*12:TABLE+44*12])
  for row in r['entries']:self.assertEqual(struct.unpack_from('<I',rom,table+12*row['index'])[0],row['offset']+0x08000000)
 def test_reject_changed_delays_modes_and_name_order(self):
  rows={e['index']:e for e in json.loads(CATALOG.read_text())['entries']}
  for i,bad in [(57,'Tipper: Yeah!{wait:w:12}{mode:1}'),(57,'Tipper: Yeah!{wait:w:11}{mode:0}'),(10,'King: {player}!{wait:W:3}')]:
   with self.assertRaises(ValueError):compile_ending(bad,tokenize(bytes.fromhex(rows[i]['source']['raw_hex']))[0])
