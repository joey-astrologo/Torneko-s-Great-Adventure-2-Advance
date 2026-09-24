"""Container wording must preserve count/item roles and unrelated consumers."""
import json,struct,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from tools.rom import load_base
from tools.rom_build import RomBuild
from tools.extract_shared_text import START,END
from tools.container_text import add_containers,OWNERS,CATALOG,KIND_TABLE

class ContainerText(unittest.TestCase):
    def test_private_tables_preserve_every_other_slot_and_consumer(self):
        original=load_base();build=RomBuild(original);report=add_containers(build);rom,_=build.finish()
        self.assertEqual({p['start'] for p in build.patches},set(OWNERS)|{0x250F8,0x25104})
        self.assertEqual(rom[START:END],original[START:END])
        self.assertEqual(rom[KIND_TABLE:KIND_TABLE+8],original[KIND_TABLE:KIND_TABLE+8])
        table=bytearray(rom[report['table_offset']:report['table_offset']+END-START])
        for row in report['entries']:
            slot=row['table_offset']
            self.assertEqual(struct.unpack_from('<I',table,slot)[0],row['offset']+0x08000000)
            table[slot:slot+4]=original[START+slot:START+slot+4]
            self.assertLessEqual(row['maximum_bytes'],192)
            self.assertLessEqual(max(row['maximum_line_widths']),216)
        self.assertEqual(table,original[START:END])
        # Restoring the owned slots reconstructs the entire original table.
        self.assertIn(0x25178,OWNERS)

    def test_rejects_reversing_totals_or_container_and_item(self):
        for slot,text in ((0xA28,'Of {count} items, {total} went into the {kind}.'),
                          (0xC0,'From {item}{fit}: took {pot}.'),
                          (0xB4,'{floor}{pot}{fit} put into {item}.')):
            with self.subTest(slot=slot),tempfile.TemporaryDirectory() as directory:
                catalog=json.loads(CATALOG.read_text())
                next(r for r in catalog['entries'] if r['table_offset']==slot)['english']=text
                path=Path(directory)/'review.json';path.write_text(json.dumps(catalog))
                with patch('tools.container_text.CATALOG',path),self.assertRaisesRegex(ValueError,'roles/order'):
                    add_containers(RomBuild(load_base()))
