import struct
import unittest

from tools.caller_repair_text import add_caller_repairs
from tools.extract_shared_text import START, END
from tools.item_loss_text import add_item_loss
from tools.rom import load_base
from tools.rom_build import RomBuild


class CallerRepairs(unittest.TestCase):
    def test_inherits_pot_messages_and_changes_only_owned_siblings(self):
        build = RomBuild(load_base())
        loss = add_item_loss(build, defer_literals=(0x38D08,))
        report = add_caller_repairs(build, loss)
        rom, _ = build.finish()
        self.assertEqual(rom[START:END], build.original[START:END])
        for binding in report['bindings']:
            if binding['table_relative'] is None:
                self.assertEqual(struct.unpack_from('<I', rom, binding['literal_offset'])[0], binding['compiled_source'])
                continue
            start = binding['compiled_literal']-binding['table_relative']-0x08000000
            old_start = loss['table_offset'] if binding['literal_offset'] == 0x38D08 else START
            owned = {r['table_offset'] for b in report['bindings'] if b['literal_offset'] == binding['literal_offset']
                     for r in report['entries'] if r['source']['offset'] == b['source_offset']}
            for slot in range(0, END-START, 4):
                if slot not in owned:
                    self.assertEqual(rom[start+slot:start+slot+4], rom[old_start+slot:old_start+slot+4])
        pot = next(b for b in report['bindings'] if b['literal_offset'] == 0x38D08)
        start = pot['compiled_literal']-0x08000000
        self.assertEqual(rom[start+0x34C:start+0x350], rom[loss['table_offset']+0x34C:loss['table_offset']+0x350])
