"""Swapping messages must preserve item roles and other shared-table consumers."""
import json,struct,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from tools.rom import load_base
from tools.rom_build import RomBuild
from tools.extract_shared_text import START,END
from tools.swap_text import add_swap,OWNERS,CATALOG

class SwapText(unittest.TestCase):
    def test_only_owned_reads_and_five_private_slots_change(self):
        original=load_base();build=RomBuild(original);report=add_swap(build);rom,_=build.finish()
        self.assertEqual({p['start'] for p in build.patches},set(OWNERS))
        self.assertEqual(rom[START:END],original[START:END])
        copied=bytearray(rom[report['table_offset']:report['table_offset']+END-START])
        for row in report['entries']:
            slot=row['table_offset']
            self.assertEqual(struct.unpack_from('<I',copied,slot)[0],row['offset']+0x08000000)
            copied[slot:slot+4]=original[START+slot:START+slot+4]
            self.assertLessEqual(row['maximum_bytes'],192)
            self.assertLessEqual(max(row['maximum_line_widths']),216)
        self.assertEqual(copied,original[START:END])
        restored=bytearray(rom[0x25648:0x257F8])
        for site in OWNERS:restored[site-0x25648:site-0x25648+4]=original[site:site+4]
        self.assertEqual(restored,original[0x25648:0x257F8])

    def test_floor_and_inventory_cannot_be_reversed_by_translation(self):
        catalog=json.loads(CATALOG.read_text())
        next(r for r in catalog['entries'] if r['table_offset']==0xC4)['english']='Swapped {item}{fit} for {floor}.'
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'review.json';path.write_text(json.dumps(catalog))
            with patch('tools.swap_text.CATALOG',path),self.assertRaisesRegex(ValueError,'argument order/roles'):
                add_swap(RomBuild(load_base()))
