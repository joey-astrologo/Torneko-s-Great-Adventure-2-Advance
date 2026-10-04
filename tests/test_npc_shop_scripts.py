"""The bank replacement must not change another NPC or an instruction byte."""
import struct
import unittest

from tools.lz77 import decompress
from tools.npc_shop_scripts import add_npc_shop_scripts, selectors, SOURCE, BANK_POINTER
from tools.rom import load_base
from tools.rom_build import RomBuild, verify_ledger


class NPCShopOwnership(unittest.TestCase):
    def test_two_selectors_only_and_native_service_aliases(self):
        original = load_base()
        build = RomBuild(original)
        report = add_npc_shop_scripts(build)
        rom, ledger = build.finish()
        self.assertTrue(verify_ledger(original, rom, ledger))
        before, _ = decompress(original, SOURCE)
        pointer = struct.unpack_from('<I', rom, BANK_POINTER)[0]-0x08000000
        after, _ = decompress(rom, pointer)
        self.assertEqual(len(before), len(after))
        self.assertEqual([i for i, (a,b) in enumerate(zip(before, after)) if a != b], [0x794,0x804])
        # Remi's old offset-table word is also read by another map's valid NPC.
        self.assertEqual([r for r in selectors(before) if r['map'] == 10],
                         [r for r in selectors(after) if r['map'] == 10])
        self.assertEqual(rom[SOURCE:0x43B296], original[SOURCE:0x43B296])
        rows = selectors(after)
        for node, root in ((26,0x575),(27,0x5CE)):
            self.assertEqual({r['root'] for r in rows if r['map'] == node and r['selector'] in (1,2)}, {root})
        self.assertEqual(report['new_text_resources'], 0)
        self.assertEqual([(p['start'],p['end_exclusive']) for p in ledger['patches']],
                         [(BANK_POINTER,BANK_POINTER+4)])


if __name__ == '__main__':
    unittest.main()
