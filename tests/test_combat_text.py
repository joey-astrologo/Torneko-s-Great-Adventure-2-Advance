"""Guard source identities and safe fallback bounds before native combat checks."""
import json,unittest,re
from tools.rom import ROOT,load_base
from tools.extract_monsters import extract
from tools.combat_text import compile_format
from tools.compact_font import measure,encode
class CombatTextTest(unittest.TestCase):
 def test_actor_table_exceptions_are_not_conflated(self):
  rows=extract()['entries']
  self.assertEqual(len(rows),141)
  self.assertEqual((rows[0]['raw_table']['japanese'],rows[0]['dungeon']['japanese']),('何者か','トルネコ'))
  self.assertEqual((rows[131]['raw_table']['japanese'],rows[131]['dungeon']['japanese']),('にせ神父','幻覚'))
 def test_formats_preserve_arguments_and_safe_individual_lines(self):
  rows=json.loads((ROOT/'translations/combat-review.json').read_text())['entries'];formats={}
  for row in rows:
   raw=compile_format(row['english']);self.assertEqual(re.findall(b'%[sd]',raw),re.findall(b'%[sd]',bytes.fromhex(row['source']['raw_hex'])))
   formats[row['id']]=row['english']
  for ident,text in formats.items():
   if ident in ('combat.1b4','combat.1b8'):text+=formats['combat.1c4']
   self.assertLessEqual(len(text.split('\n')),2)
   widths=[measure(line.replace('{actor}','Crack-billed platypunk Lv32767').replace('{value}','2147483647')) for line in text.split('\n')]
   self.assertLessEqual(max(widths),216)
   self.assertTrue(all(line.endswith(' ') for line in text.split('\n')[:-1]))
 def test_level_suffix_fits_existing_scratch(self):
  for row in json.loads((ROOT/'translations/monsters-review.json').read_text())['entries']:
   self.assertLessEqual(len(encode(row['dungeon_english']+' Lv'))+11,64)
 def test_literal_percent_does_not_become_a_printf_directive(self):
  self.assertEqual(compile_format('50%'),encode('50')[:-1]+b'\xf0%%\0')
  with self.assertRaisesRegex(ValueError,'Unknown combat format field'):
   compile_format('{unknown} takes damage.')
