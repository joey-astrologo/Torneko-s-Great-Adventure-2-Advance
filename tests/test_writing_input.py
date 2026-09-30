"""Protect input bounds, Thumb literal alignment and preserved lookup mechanics."""
import struct
import unittest
from tools.rom import load_base
from tools.rom_build import RomBuild
from tools.compact_font import font_snapshot
from tools.writing_input import far,add_input

class WritingInputOwnership(unittest.TestCase):
    def test_far_jump_loads_its_own_literal_at_both_halfword_alignments(self):
        for site in (0x080182E8,0x0801A2BA):
            for register in (0,3):
                target=0x08812380
                code=far(site,target,register)
                ldr,bx=struct.unpack_from('<HH',code)
                self.assertEqual(ldr&0xF800,0x4800)
                self.assertEqual((ldr>>8)&7,register)
                self.assertEqual(bx,0x4700|(register<<3))
                literal=((site+4)&~3)+(ldr&255)*4
                self.assertEqual(struct.unpack_from('<I',code,literal-site)[0],target|1)
                self.assertEqual(len(code),10 if site&2 else 8)

    def test_writing_preserves_original_entries_and_target_sets(self):
        original=load_base();build=RomBuild(original)
        with font_snapshot():report=add_input(build)
        rom,_=build.finish()
        for table in report['tables']:
            start=table['source_offset'];end=table['end_exclusive'];count=len(table['original_entries']);at=table['offset']
            names=[r for r in report['entries'] if r['family']==table['family']]
            self.assertEqual(rom[at:at+8*count],original[start:end-8])
            self.assertEqual(rom[at+8*(count+len(names)):at+8*(count+len(names)+1)],original[end-8:end])
            self.assertEqual({r['target'] for r in names},{r['target'] for r in table['original_entries']})
            self.assertTrue(all(1<=len(r['english'])<=15 for r in names))
        # Restore only declared patch bytes; every other original byte stays exact.
        restored=bytearray(rom[:len(original)])
        for p in build.patches:restored[p['start']:p['end_exclusive']]=bytes.fromhex(p['before_hex'])
        self.assertEqual(restored,original)
        # Caller allocations/deallocations remain paired for each grown frame.
        for push,pop in ((0x1828E,0x1850C),(0x3545A,0x354CC),(0x3EF4A,0x3EFBC)):
            self.assertEqual(struct.unpack_from('<H',rom,push)[0],0xB089)
            self.assertEqual(struct.unpack_from('<H',rom,pop)[0],0xB009)
        self.assertEqual(len(report['entries']),106)

if __name__=='__main__':unittest.main()
