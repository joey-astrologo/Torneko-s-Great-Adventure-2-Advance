"""The computed damage reader must inherit earlier combat table patches."""
import struct
import unittest

from tools.compact_font import encode
from tools.extract_shared_text import START, END
from tools.rom import load_base
from tools.rom_build import RomBuild
from tools.shield_reflection_text import add_shield_reflection


class ShieldReflectionOwnership(unittest.TestCase):
    def test_private_damage_table_preserves_inherited_bindings(self):
        original = load_base()
        build = RomBuild(original)
        at = build.allocate('existing-damage',encode('Damage'),'test-inherited')
        build.patch('existing-damage-slot',START+0x19C,original[START+0x19C:START+0x1A0],
                    struct.pack('<I',0x08000000+at),'test-inherited')
        inherited = bytes(build.data[START:END])
        report = add_shield_reflection(build)
        row = report['entries'][0]
        table = bytearray(build.data[report['table_offset']:report['table_offset']+END-START])
        self.assertEqual(struct.unpack_from('<I',table,0x19C)[0],0x08000000+at)
        self.assertEqual(struct.unpack_from('<I',table,0x224)[0],0x08000000+row['offset'])
        table[0x224:0x228] = inherited[0x224:0x228]
        self.assertEqual(bytes(table),inherited)
        self.assertEqual(bytes(build.data[START:END]),inherited)
        self.assertEqual({p['start'] for p in build.patches},{START+0x19C,0xCF50})
        self.assertEqual(struct.unpack_from('<I',build.data,0xCF50)[0],0x08000000+report['table_offset'])


if __name__ == '__main__':
    unittest.main()
