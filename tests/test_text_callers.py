"""Caller tracing must follow bindings and discard uncertain/changed paths."""
import struct
import unittest

from tools.audit_text_callers import BASE, compare_flags, condition, trace


class CallerTraceTests(unittest.TestCase):
    def sample(self):
        # ldr r0,[pc,#12]; ldr r1,[r0]; bl formatter; bx lr.
        rom = bytearray(96)
        struct.pack_into('<HHHHH', rom, 0, 0x4803, 0x6801, 0xF000, 0xFFD8, 0x4770)
        struct.pack_into('<I', rom, 16, BASE+32)
        struct.pack_into('<I', rom, 32, BASE+64)
        return rom

    def test_private_table_changes_actual_argument(self):
        original = self.sample()
        compiled = bytearray(original)
        struct.pack_into('<I', compiled, 16, BASE+40)
        struct.pack_into('<I', compiled, 40, BASE+80)
        rows, limits, _ = trace(original, compiled, {0}, {BASE+4: BASE+0xFB8})
        self.assertEqual([(r['original_argument'], r['compiled_argument']) for r in rows], [(BASE+64, BASE+80)])
        self.assertEqual(limits, [])

    def test_unknown_ram_load_does_not_keep_old_source(self):
        original = self.sample()
        # A second load through an unknown register replaces r1 before the call.
        struct.pack_into('<HHHH', original, 4, 0x6811, 0xF000, 0xFFD7, 0x4770)
        rows, _, _ = trace(original, original, {0}, {BASE+6: BASE+0xFB8})
        self.assertEqual(rows, [])

    def test_unknown_table_index_reports_loss_without_binding(self):
        original = self.sample()
        # r0 is a known table base, r2 is unknown: add r1,r0,r2;
        # ldr r1,[r1]; bl formatter. Reporting must not invent a pointer.
        struct.pack_into('<HHHHH', original, 2, 0x1881, 0x6809, 0xF000, 0xFFD7, 0x4770)
        compiled = bytearray(original)
        struct.pack_into('<I', compiled, 16, BASE+40)
        losses = []
        plain = trace(original, compiled, {0}, {BASE+6: BASE+0xFB8})
        observed = trace(original, compiled, {0}, {BASE+6: BASE+0xFB8},
            unknown_operand_observer=lambda *args: losses.append(args))
        self.assertEqual(observed, plain)
        self.assertEqual(observed[0], [])
        self.assertIn((BASE+2, 0x1881, (BASE+32, BASE+40), None, BASE), losses)

    def test_known_table_index_does_not_report_unknown_operand(self):
        original = self.sample()
        struct.pack_into('<HHHHHH', original, 2, 0x2200, 0x1881, 0x6809,
                         0xF000, 0xFFD6, 0x4770)
        losses = []
        rows, _, _ = trace(original, original, {0}, {BASE+8: BASE+0xFB8},
            unknown_operand_observer=lambda *args: losses.append(args))
        self.assertEqual(rows[0]['original_argument'], BASE+64)
        self.assertNotIn(BASE+4, [r[0] for r in losses])

    def test_patched_instruction_requires_new_analysis(self):
        original = self.sample()
        compiled = bytearray(original)
        struct.pack_into('<H', compiled, 2, 0x2100)
        rows, _, stops = trace(original, compiled, {0}, {BASE+4: BASE+0xFB8})
        self.assertEqual(rows, [])
        self.assertEqual(stops['patched_instruction'], 1)

    def test_call_clobbers_volatile_pointer(self):
        original = self.sample()
        struct.pack_into('<HHH', original, 8, 0xF000, 0xFFD6, 0x4770)
        rows, _, _ = trace(original, original, {0}, {BASE+8: BASE+0xFB8})
        self.assertEqual(rows, [])

    def test_ldmia_tracks_paired_tables_and_writeback(self):
        original = self.sample()
        # ldmia r0!,{r1,r2}: r1 receives the source; r0 advances by eight.
        struct.pack_into('<H', original, 2, 0xC806)
        compiled = bytearray(original)
        struct.pack_into('<I', compiled, 32, BASE+80)
        calls = []
        rows, _, _ = trace(original, compiled, {0}, {BASE+4: BASE+0xFB8},
            call_observer=lambda pc,target,args,seed,path:calls.append(args))
        self.assertEqual((rows[0]['original_argument'], rows[0]['compiled_argument']), (BASE+64,BASE+80))
        self.assertEqual(calls[0][0], (BASE+40,BASE+40))

    def test_ldmia_base_in_list_retains_loaded_value(self):
        original = self.sample()
        struct.pack_into('<H', original, 2, 0xC803)  # r0!, {r0,r1}
        struct.pack_into('<I', original, 36, BASE+80)
        calls = []
        rows, _, _ = trace(original, original, {0}, {BASE+4: BASE+0xFB8},
            call_observer=lambda pc,target,args,seed,path:calls.append(args))
        self.assertEqual(rows[0]['original_argument'], BASE+80)
        self.assertEqual(calls[0][0], (BASE+64,BASE+64))

    def test_ldmia_unknown_base_clears_stale_source(self):
        original = self.sample()
        struct.pack_into('<HHHH', original, 4, 0xCA02, 0xF000, 0xFFD7, 0x4770)
        rows, _, _ = trace(original, original, {0}, {BASE+6: BASE+0xFB8})
        self.assertEqual(rows, [])

    def test_known_comparison_excludes_impossible_table_branch(self):
        original = self.sample()
        struct.pack_into('<H', original, 0, 0x4807)
        struct.pack_into('<II', original, 32, BASE+36, BASE+64)
        # mov r2,#1; cmp r2,#1; bne to call. The reachable path returns.
        struct.pack_into('<HHHHHHH', original, 4, 0x2201, 0x2A01, 0xD100,
                         0x4770, 0xF000, 0xFFD4, 0x4770)
        rows, _, _ = trace(original, original, {0}, {BASE+12: BASE+0xFB8})
        self.assertEqual(rows, [])

    def test_unknown_flag_writer_does_not_reuse_comparison(self):
        original = self.sample()
        struct.pack_into('<H', original, 0, 0x4807)
        struct.pack_into('<II', original, 32, BASE+36, BASE+64)
        struct.pack_into('<HHHHHHHH', original, 4, 0x2201, 0x2A01, 0x1C5B,
                         0xD100, 0x4770, 0xF000, 0xFFD3, 0x4770)
        rows, _, _ = trace(original, original, {0}, {BASE+14: BASE+0xFB8})
        self.assertEqual(len(rows), 1)

    def test_signed_and_unsigned_comparisons_differ(self):
        flags = compare_flags(0x80000000, 1)
        self.assertTrue(condition(2, flags))  # unsigned >=
        self.assertTrue(condition(11, flags))  # signed <, including overflow


class TraceStopEvidenceTests(unittest.TestCase):
    def test_stop_observation_preserves_results_and_paired_patch_bytes(self):
        original = CallerTraceTests().sample()
        compiled = bytearray(original)
        struct.pack_into('<H', compiled, 2, 0x2100)
        expected = trace(original, compiled, {0}, {BASE+4: BASE+0xFB8})
        details = []
        actual = trace(original, compiled, {0}, {BASE+4: BASE+0xFB8},
                       stop_observer=details.append)
        self.assertEqual(actual, expected)
        self.assertEqual(len(details), 1)
        self.assertEqual((details[0]['reason'], details[0]['address']),
                         ('patched_instruction', BASE+2))
        self.assertEqual(details[0]['tail'], [BASE])
        self.assertNotEqual(details[0]['original_hex'], details[0]['compiled_hex'])
        self.assertEqual(details[0]['registers']['0'], (BASE+32, BASE+32))

    def test_loop_stop_records_repetition_and_exact_instruction(self):
        # add r0,1; b back: a known changing value defeats state deduplication.
        rom = struct.pack('<HH', 0x3001, 0xE7FD)
        details = []
        _, limits, stops = trace(rom, rom, {0}, {}, max_path_length=8,
            initial_registers={0:{0:(0,0)}}, stop_observer=details.append)
        self.assertFalse(limits)
        self.assertEqual(stops, {'path_length_limit':1})
        self.assertEqual(details[0]['address'], BASE)
        self.assertEqual(details[0]['registers']['0'], (4,4))
        self.assertEqual(details[0]['path_length'], 8)
        self.assertEqual(details[0]['repeated_addresses'],
                         [{'address':BASE,'visits':4},{'address':BASE+2,'visits':4}])
