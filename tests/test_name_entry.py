import unittest

from tools.build_english import build_rom
from tools.compact_font import encode
from tools.name_entry import CHARACTERS, IDS, TABLE, TABLE_REFERENCES, indexed, keyboard_pages
from tools.rom import load_base


class NameEntryTest(unittest.TestCase):
    def test_name_record_capacity_and_sentinels(self):
        self.assertEqual(indexed('Torneko')[7:], b'\x01' + b'\0' * 8)
        for text in ('', 'TornekoX', 'é', '\0', '\n'):
            with self.assertRaises(ValueError):
                indexed(text)
        self.assertEqual(len(indexed('WWWWWWW')), 16)
        self.assertEqual(len(encode('WWWWWWW')), 15)

    def test_existing_id_meanings_and_original_keys_remain_available(self):
        original = load_base()
        data, report = build_rom()
        offset = report['name_entry']['glyph_table'] - 0x08000000
        glyphs = data[offset:offset + 512]
        self.assertEqual(glyphs[:2], original[TABLE:TABLE + 2])
        self.assertEqual(glyphs[4:0xB9 * 2], original[TABLE + 4:TABLE + 0xB9 * 2])
        self.assertEqual(len(set(IDS.values())), 69)
        self.assertTrue(all(0xB9 <= ident <= 0xFD for ident in IDS.values()))
        for char in CHARACTERS:
            self.assertEqual(glyphs[IDS[char] * 2:IDS[char] * 2 + 2], encode(char)[:2])
        pages = keyboard_pages(original)
        self.assertEqual(pages[2], original[0x147F80:0x147FC0])
        self.assertEqual(pages[3], original[0x147F00:0x147F40])
        self.assertEqual(pages[4], original[0x147F40:0x147F80])
        for char in CHARACTERS:
            self.assertTrue(any(IDS[char] in page[4:] for page in pages[:2]))
        for site in TABLE_REFERENCES:
            self.assertEqual(int.from_bytes(data[site:site + 4], 'little'), offset + 0x08000000)
        self.assertTrue(report['unowned_original_bytes_preserved'])


if __name__ == '__main__':
    unittest.main()
