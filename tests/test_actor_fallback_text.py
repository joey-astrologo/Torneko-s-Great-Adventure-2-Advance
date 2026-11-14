"""The unknown-name fix must not translate other shared-table consumers."""
import struct
import unittest

from tools.actor_fallback_text import add_actor_fallback, READERS, SLOT, SOURCE
from tools.compact_font import encode
from tools.extract_shared_text import START, END
from tools.rom import load_base
from tools.rom_build import RomBuild, verify_ledger


class ActorFallbackOwnership(unittest.TestCase):
    def test_two_bindings_preserve_every_other_source_and_instruction(self):
        original = load_base()
        build = RomBuild(original)
        payload = encode('Someone')
        name = build.allocate('result-actor-0', payload, 'results')
        results = {'entries': [dict(id=0, english='Someone', offset=name,
            encoded_hex=payload.hex(), source=dict(offset=SOURCE-0x08000000,
                                                  raw_hex='89bd8ed282a900'))]}
        report = add_actor_fallback(build, results)
        rom, ledger = build.finish()
        self.assertTrue(verify_ledger(original, rom, ledger))
        self.assertEqual(rom[START:END], original[START:END])
        self.assertEqual([(p['start'], p['end_exclusive']) for p in ledger['patches']],
                         [(literal, literal+4) for _, literal, _ in READERS])
        for entry, literal, _ in READERS:
            table = struct.unpack_from('<I', rom, literal)[0]-0x08000000
            self.assertEqual(rom[entry:entry+10], original[entry:entry+10])
            self.assertEqual(struct.unpack_from('<I', rom, table+SLOT)[0], name+0x08000000)
            restored = bytearray(rom[table:table+END-START])
            struct.pack_into('<I', restored, SLOT, SOURCE)
            self.assertEqual(restored, original[START:END])
        self.assertEqual(report['new_text_resources'], 0)
