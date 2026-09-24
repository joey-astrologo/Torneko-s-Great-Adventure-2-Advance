"""Boundary checks for newly owned service and story formatting consumers."""
import json
import unittest
from tools.rom import load_base
from tools.rom_build import RomBuild
from tools.bakery_text import CATALOG as BAKERY, compile_row
from tools.town_text import entries
from tools.player_status_text import add_player_status
from tools.floor_progress_text import CATALOG as FLOOR, compile_progress, CAPACITY
from tools.extract_shared_text import START, END

class OwnedTextConsumers(unittest.TestCase):
    def test_bakery_dynamic_width_and_argument_multiplicity(self):
        row=next(r for r in json.loads(BAKERY.read_text())['entries'] if r['index']==103)
        source=next(r for r in entries() if r['index']==103)
        payload,layout=compile_row(row,source)
        self.assertEqual(payload.count(b'%s'),1)
        self.assertEqual(payload.count(b'%d'),1)
        self.assertLessEqual(max(layout['line_widths'][0]),216)
        self.assertLessEqual(layout['maximum_formatted_bytes'],256)
        with self.assertRaisesRegex(ValueError,'substitutions'):
            compile_row(row|{'english':'{item} and {item}: {price}G'},source)
        with self.assertRaisesRegex(ValueError,'exceeds page'):
            compile_row(row|{'english':'W'*30+' {item} {price}'},source)

    def test_player_status_copy_cannot_translate_other_shared_consumers(self):
        build=RomBuild(load_base());report=add_player_status(build);rom,_=build.finish()
        self.assertEqual(rom[START:END],load_base()[START:END])
        self.assertEqual({p['start'] for p in build.patches},{0xB760,0xB7D8,0xB7A8})
        self.assertEqual({r['table_offset'] for r in report['entries']},{0xE4,0xE8,0x4A0})
        self.assertEqual(max(r['maximum_width'] for r in report['entries']),205)
        self.assertTrue(all(b'\r' not in bytes.fromhex(r['encoded_hex']) for r in report['entries']))

    def test_floor_formatter_bound_applies_to_static_text_too(self):
        rows=json.loads(FLOOR.read_text())['entries']
        static=next(r for r in rows if r['id']=='event-bank-5.2747')
        payload,layout=compile_progress(static)
        self.assertEqual(layout['capacity'],CAPACITY)
        self.assertGreater(len(payload),256)
        self.assertLessEqual(len(payload),CAPACITY)
        with self.assertRaisesRegex(ValueError,'stack capacity'):
            compile_progress(static|{'english':static['english']+'\n\nAnother long paragraph to exceed the owned buffer safely.'})
        dynamic=next(r for r in rows if '{floor}' in r['english'])
        with self.assertRaisesRegex(ValueError,'substitution'):
            compile_progress(dynamic|{'english':dynamic['english'].replace('{floor}','27')})
