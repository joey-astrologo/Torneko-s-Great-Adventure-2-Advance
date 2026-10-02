import copy
import json
import struct
import unittest

from tools.item_text import add_items
from tools.remaining_caller_text import add_remaining_callers, compile_row, CATALOG
from tools.result_text import add_results
from tools.rom import load_base
from tools.rom_build import RomBuild


class RemainingCallers(unittest.TestCase):
    def test_preserves_existing_result_and_story_siblings(self):
        build=RomBuild(load_base())
        add_items(build)
        results=add_results(build,defer_ui_literals=(0x1CD3C,0x571B4))
        # An existing owner may have localized a neighboring tutorial slot.
        tutorial=build.allocate('test-owned-tutorial',b'English\0','fixture')
        build.patch('test-tutorial-pointer',0x147238,build.original[0x147238:0x14723C],
                    struct.pack('<I',tutorial+0x08000000),'fixture')
        report=add_remaining_callers(build,results)
        rom,_=build.finish()
        for table in report['tables']:
            for slot in range(0,table['size'],4):
                if slot not in table['changed_slots']:
                    self.assertEqual(rom[table['offset']+slot:table['offset']+slot+4],
                                     rom[table['source_start']+slot:table['source_start']+slot+4])
        for literal in report['item_definition_literals']:
            self.assertEqual(struct.unpack_from('<I',rom,literal)[0],report['item_definition_table']+0x08000000)

    def test_rejects_missing_timing_and_substitution_controls(self):
        rows=json.loads(CATALOG.read_text())['entries']
        for src,token in [(0x6B24C,'@W@'),(0x14BD5D,'{village}'),(0x6B1B4,'{player}')]:
            row=copy.deepcopy(next(r for r in rows if r['source']['offset']==src))
            row['english']=row['english'].replace(token,'',1)
            with self.assertRaises(ValueError):compile_row(row)

    def test_rejects_overflowing_trade_item_field(self):
        row=copy.deepcopy(next(r for r in json.loads(CATALOG.read_text())['entries'] if r['source']['offset']==0x6ED58))
        row['english']='Trading completed successfully for "{item}".'
        with self.assertRaises(ValueError):compile_row(row)
