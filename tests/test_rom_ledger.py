import copy
import unittest

from tools.rom import digest
from tools.rom_build import verify_ledger


class RomLedgerTests(unittest.TestCase):
    def setUp(self):
        self.original = b'abcdef'
        self.rom = b'abXdef\xff\xfftest\xff\xff\xff\xff'
        self.report = {
            'source_sha256': digest(self.original), 'source_bytes': 6,
            'output_sha256': digest(self.rom), 'output_bytes': 16,
            'patches': [{'id': 'patch', 'owner': 'test', 'start': 2,
                         'end_exclusive': 3, 'before_hex': '63', 'after_hex': '58'}],
            'allocations': [{'id': 'text', 'owner': 'test', 'start': 8,
                             'end_exclusive': 12, 'padding_before': 2,
                             'alignment': 4, 'sha256': digest(b'test')}],
        }

    def test_valid_ledger(self):
        self.assertTrue(verify_ledger(self.original, self.rom, self.report))

    def test_corruption_is_rejected_even_with_updated_output_hash(self):
        # Original bytes, checked patch, alignment padding, allocation, ROM tail.
        for offset in (0, 2, 6, 9, 15):
            with self.subTest(offset=offset):
                damaged = bytearray(self.rom)
                damaged[offset] ^= 1
                report = copy.deepcopy(self.report)
                report['output_sha256'] = digest(damaged)
                with self.assertRaises(ValueError):
                    verify_ledger(self.original, bytes(damaged), report)

    def test_overlapping_patch_is_rejected(self):
        report = copy.deepcopy(self.report)
        extra = dict(report['patches'][0], id='overlap')
        report['patches'].append(extra)
        with self.assertRaises(ValueError):
            verify_ledger(self.original, self.rom, report)

    def test_invalid_allocation_alignment_is_rejected(self):
        report = copy.deepcopy(self.report)
        report['allocations'][0]['alignment'] = 3
        with self.assertRaises(ValueError):
            verify_ledger(self.original, self.rom, report)
