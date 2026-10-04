import struct
import unittest

from tools.audit_text_callers import BASE, trace
from tools.thumb_switches import switches


class ThumbSwitchTests(unittest.TestCase):
    def sample(self):
        rom = bytearray(128)
        # cmp r1,1; bhi default; lsl r0,r1,2; ldr r1,table;
        # add r0,r0,r1; ldr r0,[r0]; mov pc,r0.
        struct.pack_into('<7H', rom, 0, 0x2901, 0xD819, 0x0088,
                         0x4902, 0x1840, 0x6800, 0x4687)
        struct.pack_into('<III', rom, 16, BASE+20, BASE+32, BASE+44)
        for at, value in ((32, 1), (44, 2), (56, 3)):
            struct.pack_into('<5H', rom, at, 0x2100+value, 0xF000, 0xF800, 0x4770, 0)
        return rom

    def test_all_in_range_branches_and_default(self):
        rom = self.sample()
        domains = switches(rom, rom)
        calls = {BASE+a:BASE+0xFB8 for a in (34, 46, 58)}
        rows, limits, _ = trace(rom, rom, {0}, calls, switch_domains=domains)
        self.assertEqual(sorted((r['call'],r['original_argument']) for r in rows),
                         [(BASE+34,1),(BASE+46,2),(BASE+58,3)])
        self.assertFalse(limits)

    def test_known_index_excludes_other_branches(self):
        rom = self.sample()
        rows, _, _ = trace(rom, rom, {0}, {BASE+34:BASE+0xFB8, BASE+46:BASE+0xFB8},
                           initial_registers={0:{1:(1,1)}}, switch_domains=switches(rom,rom))
        self.assertEqual([r['call'] for r in rows], [BASE+46])

    def test_default_path_replaces_flags_from_before_the_guard(self):
        rom = self.sample()
        # An out-of-range index cannot compare equal to the upper bound.
        struct.pack_into('<5H',rom,56,0xD008,0x2103,0xF000,0xF800,0x4770)
        struct.pack_into('<4H',rom,76,0x2104,0xF000,0xF800,0x4770)
        rows,_,_=trace(rom,rom,{0},{BASE+60:BASE+0xFB8,BASE+78:BASE+0xFB8},
                      initial_registers={0:{999:(4,4)}},switch_domains=switches(rom,rom))
        self.assertEqual([(r['call'],r['original_argument']) for r in rows],[(BASE+60,3)])

    def test_changed_table_or_guard_is_not_followed(self):
        rom = self.sample()
        for at in (0, 16, 20):
            changed = bytearray(rom)
            changed[at] ^= 1
            self.assertFalse(switches(rom, changed))

    def test_mismatched_register_and_invalid_target_are_rejected(self):
        rom = self.sample()
        for at, value in ((4, 0x0080), (20, BASE+33), (20, BASE+200)):
            changed = bytearray(rom)
            struct.pack_into('<H' if at == 4 else '<I', changed, at, value)
            self.assertFalse(switches(changed, changed))

    def test_default_trace_keeps_unknown_computed_branch_unresolved(self):
        rom = self.sample()
        rows, _, stops = trace(rom, rom, {0}, {BASE+34:BASE+0xFB8, BASE+46:BASE+0xFB8})
        self.assertFalse(rows)
        self.assertEqual(stops['computed_pc'],1)
