"""Malformed source handling and preservation of translator-owned catalog data."""

from copy import deepcopy
import unittest

from tools.extract_text import merge_catalog
from tools.lz77 import decompress
from tools.text_codec import readable, source_bytes, tokenize


class TextSourcesTest(unittest.TestCase):
    def test_overlapping_lz_reference(self):
        # Literal A followed by a distance-one reference: copied bytes become
        # available immediately, rather than slicing only the old output.
        packed = bytes.fromhex("1007000040413000")
        decoded, end = decompress(packed)
        self.assertEqual(decoded, b"AAAAAAA")
        self.assertEqual(end, len(packed))

    def test_malformed_lz_streams_fail_with_bounds(self):
        for data in (b"", bytes.fromhex("110100000041"), bytes.fromhex("10000000"),
                     bytes.fromhex("10040000800000"), bytes.fromhex("100400000041")):
            with self.subTest(data=data.hex()), self.assertRaises(ValueError):
                decompress(data)
        with self.assertRaisesRegex(ValueError, "output size"):
            decompress(bytes.fromhex("10ffffff"))

    def test_zero_and_at_bytes_inside_position_operands(self):
        raw = b"\x04\0" + "あ".encode("cp932") + b"\x04@" + "い".encode("cp932") + b"\r@B@\0"
        tokens, end = tokenize(raw)
        self.assertEqual(end, len(raw))
        self.assertEqual(source_bytes(tokens), raw)
        self.assertIn("あ", readable(tokens))
        self.assertEqual([t["raw_hex"] for t in tokens if t["kind"] == "command"], ["0400", "0440", "0d", "404240"])

    def test_halfwidth_and_unmapped_glyphs_keep_original_bytes(self):
        raw = "ｱあ".encode("cp932") + bytes.fromhex("ffff00")
        tokens, end = tokenize(raw)
        self.assertEqual(source_bytes(tokens), raw)
        self.assertEqual(end, len(raw))
        self.assertTrue(any(t["kind"] == "glyph" for t in tokens))

    def test_truncated_or_unterminated_text_rejected(self):
        for raw in (b"\x04", b"\x82", b"@B", b"ABC", b"@B\0@"):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                tokenize(raw)

    def test_reextraction_preserves_english_notes_review_and_absent_rows(self):
        old = {"source_rom_sha256": "base", "entries": [
            {"id": "one", "source_sha256": "source", "japanese": "old", "english": "Reviewed English",
             "notes": "Keep this", "language_status": "reviewed", "reviewer": "human",
             "status": "native-source-verified; insertion ownership pending"},
            {"id": "two", "source_sha256": "other", "english": "Another route"}]}
        original = deepcopy(old)
        result = merge_catalog(old, [{"id": "one", "source_sha256": "source", "japanese": "new", "evidence": [1]}], "base")
        row = result["entries"][0]
        self.assertEqual((row["english"], row["notes"], row["language_status"], row["reviewer"]),
                         ("Reviewed English", "Keep this", "reviewed", "human"))
        self.assertEqual(len(result["entries"]), 2)
        self.assertEqual(row['status'], 'native-source-verified')
        self.assertEqual(old, original)

    def test_reextraction_accumulates_distinct_observations(self):
        old = {"entries": [{"id": "one", "source_sha256": "source", "evidence": [{"route": "a"}]}]}
        new = [{"id": "one", "source_sha256": "source", "evidence": [{"route": "a"}, {"route": "b"}]}]
        result = merge_catalog(old, new, "base")
        self.assertEqual(result["entries"][0]["evidence"], [{"route": "a"}, {"route": "b"}])

    def test_changed_sources_and_duplicate_ids_rejected(self):
        row = {"id": "one", "source_sha256": "before", "english": "Keep"}
        old = {"source_rom_sha256": "base", "entries": [row]}
        with self.assertRaisesRegex(ValueError, "bytes changed"):
            merge_catalog(old, [{"id": "one", "source_sha256": "after"}], "base")
        with self.assertRaisesRegex(ValueError, "base differs"):
            merge_catalog(old, [], "another")
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            merge_catalog({"entries": [row, row]}, [], "base")
