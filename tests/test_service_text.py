"""Regression guards for the native visual review's spacing and column issues."""
import json,unittest
from tools.bank_text import CATALOG,compile_bank
from tools.compact_font import encode,load_font,measure
from tools.numeric_font import ALIASES,glyph
from tools.numeric_font import validate_native_digits
from tools.rom import load_base
from tools.storage_text import CATALOG as STORAGE,compile_storage


class ServiceTypographyTest(unittest.TestCase):
    def test_bank_gift_preserves_dynamic_fields_and_three_gift_capacity(self):
        payload,layout=compile_bank({'index':91,'english':'{player} got {item}!'})
        self.assertEqual(payload.count(b'\x7e'),1)
        self.assertEqual(payload.count(b'%s'),1)
        self.assertEqual(payload.count(b'\r'),1)
        self.assertEqual(layout['line_widths'],[[206]])
        self.assertLessEqual(3*(layout['maximum_formatted_bytes']-1)+1,384)

    def test_native_decimal_tables_keep_number_values(self):
        validate_native_digits(load_base())
        self.assertEqual(ALIASES[0x8755],'1')
        self.assertEqual(ALIASES[0x875d],'9')
        self.assertEqual(ALIASES[0x875e],'0')
        self.assertNotIn(0x8754,ALIASES)  # Equipped-and-cursed icon.

    def test_storage_keeps_both_columns_within_original_window(self):
        row=json.loads(STORAGE.read_text())['entries'][0]
        payload,layout=compile_storage(row)
        self.assertEqual(payload.count(b'\x06\x0c'),4)
        self.assertEqual(payload.count(b'\x06\x7c'),4)
        self.assertEqual(layout['column_budgets'],[100,100])
        row['english'][0]='W'*17
        with self.assertRaisesRegex(ValueError,'100px'):
            compile_storage(row)

    def test_word_spaces_are_narrow_without_compressing_letters(self):
        font=load_font()
        self.assertEqual(measure(' '),3)
        self.assertEqual(measure('W'),6)
        self.assertEqual(measure('12 x Iron arrow')-measure('12xIronarrow'),9)
        self.assertEqual(font['glyphs'][' ']['source_hex'][:2],'06')

    def test_inverse_digit_background_has_no_vertical_seams(self):
        font=load_font()
        for code in range(0x8740,0x874a):
            g=glyph(font,code)
            self.assertEqual(g['advance'],6)
            self.assertTrue(all(row[-1]=='#' for row in g['rows'][3:14]))
        self.assertFalse(set(range(0x874a,0x8755)) & set(ALIASES))

    def test_bank_colons_attach_before_positioning_the_amount(self):
        row=next(r for r in json.loads(CATALOG.read_text())['entries'] if r['index']==81)
        payload,layout=compile_bank(row)
        for label in ('Deposit:','Withdraw:'):
            self.assertIn(encode(label)[:-1]+b'\x06\x45',payload)
            self.assertLessEqual(12+measure(label),69)
        self.assertLessEqual(max(layout['line_widths'][0]),176)
        self.assertEqual(payload.count(b'%d'),2)

    def test_storage_dynamic_fields_reserve_expanded_width(self):
        row={'id':'probe','english':'Break {item}?'}
        payload,layout=compile_storage(row)
        self.assertIn(b'%s',payload)
        self.assertEqual(layout['maximum_formatted_bytes'],len(payload)+61)
        self.assertLessEqual(max(layout['line_widths'][0]),216)
        with self.assertRaisesRegex(ValueError,'expanded line budget'):
            compile_storage({'id':'probe','english':'Break {item} or {item}?'})
        with self.assertRaisesRegex(ValueError,'Unknown storage format field'):
            compile_storage({'id':'probe','english':'Sell {unknown}?'})

    def test_storage_many_small_pages_cannot_overrun_format_buffer(self):
        text='\n\n'.join(['A short page.']*12+['{count} items.'])
        with self.assertRaisesRegex(ValueError,'256-byte buffer'):
            compile_storage({'id':'probe','english':text})

    def test_item_description_keeps_player_substitution_and_width_reserve(self):
        from tools.item_text import compile_description
        src={'raw_hex':'7e00'}
        payload=compile_description('{player} recovers HP.',src)
        self.assertEqual(payload[0],0x7e)
        with self.assertRaisesRegex(ValueError,'player substitution differs'):
            compile_description('You recover HP.',src)
        with self.assertRaisesRegex(ValueError,'Info layout'):
            compile_description('{player} '+('W'*23),src)
        # Native name editor permits seven 14px Japanese glyphs (98px).
        with self.assertRaisesRegex(ValueError,'Info layout'):
            compile_description('Stops {player} from tripping when\ncarried outside a pot.',src)
        compile_description('Stops {player} from tripping\nwhen carried outside a pot.',src)
