import struct
import unittest

from tools.audit_text_callers import BASE, trace


class SourceReaderAnalysis(unittest.TestCase):
    def test_relocated_table_reads_preserve_original_compiled_pair(self):
        # ldr r0, literal; ldr r1,[r0]; bl formatter; bx lr.
        rom = bytearray(24)
        struct.pack_into('<HHHHHH', rom, 0, 0x4803, 0x6801, 0xF000, 0xF800, 0x4770, 0)
        struct.pack_into('<I', rom, 16, 0x020141AC)
        calls = {BASE+4: 0x08000FB8}
        images = ((0x020141AC, (struct.pack('<I', 0x08060344), struct.pack('<I', 0x08900000))),)
        rows, _, _ = trace(rom, rom, {0}, calls, memory_images=images)
        self.assertEqual([(r['original_argument'], r['compiled_argument']) for r in rows],
                         [(0x08060344, 0x08900000)])
        rows, _, _ = trace(rom, rom, {0}, calls)
        self.assertFalse(rows)

    def test_stack_argument_is_tagged_and_not_read_as_rom(self):
        # push {lr}; sub sp,16; add r0,sp,4; bl queue; add sp,16; pop {pc}.
        rom = struct.pack('<8H', 0xB500, 0xB084, 0xA801, 0xF000, 0xF800, 0xB004, 0xBD00, 0)
        rows, _, _ = trace(rom, rom, {0}, {BASE+6: 0x0801588C}, stack_model=True)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['argument_kind'], 'stack-relative')
        self.assertEqual(rows[0]['original_argument'], 0x0FFFFFF0)

    def test_paired_frame_sizes_and_unknown_format_producer(self):
        original = struct.pack('<8H', 0xB500, 0xB084, 0xA800, 0xF000, 0xF800, 0xB004, 0xBD00, 0)
        compiled = bytearray(original)
        struct.pack_into('<H', compiled, 2, 0xB088)
        observed = []
        rows, _, _ = trace(original, compiled, {0}, {}, stack_model=True,
                           paired_stack_adjustments=True, call_observer=lambda *args: observed.append(args))
        self.assertFalse(rows)
        self.assertEqual(len(observed), 1)
        self.assertEqual(observed[0][2][0], (0x0FFFFFEC,0x0FFFFFDC))
        self.assertIsNone(observed[0][2][1])
        self.assertEqual(observed[0][1], BASE+10)

    def test_english_index_includes_both_catalog_schemas(self):
        from tools.audit_source_readers import inserted_resources
        rows = [{'source':{'raw_hex':'00'},'offset':1,'encoded_hex':'f04100','english':'A'},
                {'source_hex':'00','offset':4,'encoded_hex':'f04200','english':'B'}]
        self.assertEqual(list(inserted_resources({'a':rows})), rows)
