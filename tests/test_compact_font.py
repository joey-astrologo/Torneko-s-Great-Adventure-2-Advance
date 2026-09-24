"""Guard checked insertion and the new English encoding against silent corruption."""

import json
from pathlib import Path
import tempfile
import unittest

from tools.compact_font import ASSET, COMPACT_ASSET, TORNEKO3_ASSET, encode, load_font, measure
from tools.rom import load_base
from tools.rom_build import RomBuild


class CompactFontTest(unittest.TestCase):
    def test_literal_ascii_avoids_original_control_parser(self):
        self.assertEqual(encode("a@~\\\nZ"), bytes.fromhex("f061f040f07ef05c0df05a00"))
        for text in ("a\0b", "\t", "café", "’"):
            with self.subTest(text=text), self.assertRaises(ValueError):
                encode(text)

    def test_original_shape_width_ownership_and_coverage_are_enforced(self):
        def shape(font):
            font["glyphs"]["A"]["rows"][4] = "######"

        def width(font):
            g = font["glyphs"]["I"]
            g["advance"] = 5
            g["rows"] = [r[:5] for r in g["rows"]]

        def ownership(font):
            font["glyphs"]["A"]["origin"] = "new"

        def coverage(font):
            del font["glyphs"]["z"]

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "font.json"
            for mutate in (shape, width, ownership, coverage):
                font = json.loads(COMPACT_ASSET.read_text())
                mutate(font)
                path.write_text(json.dumps(font))
                with self.subTest(mutation=mutate.__name__), self.assertRaises(ValueError):
                    load_font(path)

    def test_measure_requires_one_supported_line(self):
        font = load_font(COMPACT_ASSET)
        self.assertEqual(measure(" Start adventure", font), 82)
        self.assertLess(measure("ill", font), measure("WWW", font))
        with self.assertRaises(ValueError):
            measure("first\nsecond", font)

    def test_imported_font_preserves_original_ink_and_advances(self):
        font = load_font(TORNEKO3_ASSET)
        self.assertEqual(measure(' Start adventure',font),83)
        self.assertEqual(measure('Unequip',font),34)
        self.assertEqual(measure('Examine',font),37)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'font.json'
            for field,value in [('advance',5),('origin','new'),('source_bitmap_hex','00'*72)]:
                changed = json.loads(TORNEKO3_ASSET.read_text())
                changed['glyphs']['A'][field] = value
                path.write_text(json.dumps(changed))
                with self.subTest(field=field),self.assertRaises(ValueError):
                    load_font(path)


class RomBuildTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original = load_base()

    def test_source_mismatch_and_overlapping_noop_patch_rejected(self):
        build = RomBuild(self.original)
        before = self.original[0x1A04:0x1A0C]
        with self.assertRaisesRegex(ValueError, "Source-byte mismatch"):
            build.patch("wrong", 0x1A04, bytes(8), before, "test")
        build.patch("first", 0x1A04, before, before, "test")
        with self.assertRaisesRegex(ValueError, "overlap"):
            build.patch("overlap", 0x1A06, before[2:4], before[2:4], "test")

    def test_unowned_edits_and_overwritten_patch_rejected(self):
        for offset, message in ((0x1A04, "patch was overwritten"), (0x1000, "Unowned changes")):
            build = RomBuild(self.original)
            build.patch("entry", 0x1A04, self.original[0x1A04:0x1A0C], bytes(8), "test")
            build.data[offset] ^= 1
            with self.subTest(offset=offset), self.assertRaisesRegex(ValueError, message):
                build.finish()

    def test_append_alignment_identity_and_resource_integrity(self):
        build = RomBuild(self.original)
        start = build.allocate("font", b"abc", "test")
        second = build.allocate("hook", b"xyz", "test", alignment=4)
        self.assertEqual((start, second), (len(self.original), len(self.original) + 4))
        with self.assertRaisesRegex(ValueError, "identity"):
            build.allocate("font", b"duplicate", "test")
        data, ledger = build.finish()
        self.assertEqual(data[:len(self.original)], self.original)
        self.assertEqual(data[start:second + 3], b"abc\xffxyz")
        self.assertEqual(ledger["output_bytes"], 16 * 1024 * 1024)
        build.data[second] ^= 1
        with self.assertRaisesRegex(ValueError, "resource was overwritten"):
            build.finish()

    def test_alignment_padding_and_unowned_append_rejected(self):
        for mutate in ("padding", "append"):
            build = RomBuild(self.original)
            first = build.allocate("font", b"abc", "test")
            build.allocate("hook", b"xyz", "test")
            if mutate == "padding":
                build.data[first + 3] = 0
            else:
                build.data.extend(b"unexpected")
            with self.subTest(mutation=mutate), self.assertRaises(ValueError):
                build.finish()
