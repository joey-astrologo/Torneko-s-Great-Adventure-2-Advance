import json,struct,unittest
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

 def test_early_tutorials_use_complete_reviewed_prose_and_bounded_menu(self):
  from tools.rom import ROOT
  from tools.opening_text import banks
  from tools.event_text import table_entries
  from tools.dialogue_layout import compile_dialogue
  from tools.text_codec import tokenize
  original=load_base();build=RomBuild(original)
  catalog={e['id']:e for e in json.loads((ROOT/'translations/event-prose-review.json').read_text())['entries']}
  sources=[e for bn in (5,6) for e in table_entries(banks()[bn])
           if (bn==5 and e['group']==2 and e['index'] in (2,5,6,7,8,9,10)) or
              (bn==6 and (e['group'],e['index'])==(9,1))]
  entries=[]
  for source in sources:
   reviewed=catalog[source['id']]
   self.assertEqual(reviewed['status'],'reviewed')
   raw,_=compile_dialogue(reviewed['english'],tokenize(bytes.fromhex(reviewed['source_hex']))[0])
   at=build.allocate(source['id'],raw,'test-prose')
   entries.append(dict(id=source['id'],rom_offset=at,encoded_hex=raw.hex(),language_status='reviewed'))
  result=add_tutorial_help(build,dict(entries=entries));rom,ledger=build.finish()
  # The original shared descriptors/cursor geometry remain byte-identical.
  self.assertEqual(rom[0x14D52C:0x14E700],original[0x14D52C:0x14E700])
  triples=bytearray(rom[0x14CEFC:0x14CF4D])
  for index,expected in ((12,b'\x0e\x04\x00'),(14,b'\x05\x04\x00')):
   self.assertEqual(triples[3*index:3*index+3],expected)
   triples[3*index:3*index+3]=original[0x14CEFC+3*index:0x14CEFF+3*index]
  self.assertEqual(triples,original[0x14CEFC:0x14CF4D])
  self.assertEqual(result['groups'][14]['descriptor'][7],2)
  self.assertEqual(len(result['groups'][14]['labels']),2)
  by_id={e['id']:e for e in entries}
  for repair in result['repairs']:
   binding=next(b for b in result['bindings'] if b['group']==repair['configuration'] and b['kind']=='intro')
   for index,ident in enumerate(repair['prose_ids'],1):
    pointer=struct.unpack_from('<I',rom,binding['offset']+4*index)[0]-0x08000000
    self.assertEqual(pointer,by_id[ident]['rom_offset'])
    raw=bytes.fromhex(by_id[ident]['encoded_hex'])
    self.assertEqual(rom[pointer:pointer+len(raw)],raw)
  self.assertTrue(ledger['unowned_original_bytes_preserved'])
