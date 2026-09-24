"""Prevent menu-fit claims from hiding a one-pixel overflow or missing glyph."""

import unittest

from tools.audition_fonts import metrics
from tools.compact_font import COMPACT_ASSET, TORNEKO3_ASSET, load_font


class FontAuditionTest(unittest.TestCase):
    def test_real_action_boundaries_for_both_fonts(self):
        old,new = load_font(COMPACT_ASSET),load_font(TORNEKO3_ASSET)
        self.assertFalse(metrics(old,'Unequip',36)['fits'])
        self.assertTrue(metrics(new,'Unequip',36)['fits'])
        self.assertEqual(metrics(new,'Examine',36)['remaining'],-1)
        self.assertTrue(metrics(new,'Examine',37)['fits'])
        self.assertEqual(metrics(new,'Exchange',36)['remaining'],-6)

    def test_ink_overhang_and_unknown_characters_are_not_ignored(self):
        synthetic = {'glyphs':{'a':{'advance':3,'rows':['....#']}}}
        self.assertEqual(metrics(synthetic,'a',4)['remaining'],-1)
        with self.assertRaises(ValueError):
            metrics(load_font(),'caf\u00e9',100)
