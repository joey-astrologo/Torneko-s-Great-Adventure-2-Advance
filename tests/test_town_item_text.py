"""Town action ownership and its narrower cursor budget are independent of dialogue."""
import json,struct,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from tools.rom import load_base
from tools.rom_build import RomBuild
from tools.town_item_text import add_town_actions,CATALOG
from tools.extract_action_labels import START,END

class TownItemText(unittest.TestCase):
    def test_sparse_consumer_table_and_unrelated_action_slots(self):
        original=load_base();build=RomBuild(original);report=add_town_actions(build);rom,_=build.finish()
        self.assertEqual({r['start'] for r in build.patches},{0x1E490,0x1E560,0x1E62C})
        self.assertEqual(rom[START:END],original[START:END])
        message_pointers=struct.unpack_from('<110I',rom,report['message_table_offset'])
        self.assertEqual({i for i,p in enumerate(message_pointers) if p},{59,108,109})
        for row in report['entries']:
            self.assertEqual(message_pointers[row['index']],row['offset']+0x08000000)
        copied=bytearray(rom[report['action_table_offset']:report['action_table_offset']+END-START])
        for row in report['labels']:
            offset=row['index']*4
            self.assertEqual(struct.unpack_from('<I',copied,offset)[0],row['offset']+0x08000000)
            copied[offset:offset+4]=original[START+offset:START+offset+4]
        self.assertEqual(copied,original[START:END])

    def test_discard_cannot_be_mistaken_for_fitting_the_town_menu(self):
        catalog=json.loads(CATALOG.read_text())
        next(r for r in catalog['labels'] if r['index']==44)['english']='Discard'
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'review.json';path.write_text(json.dumps(catalog))
            with patch('tools.town_item_text.CATALOG',path),self.assertRaisesRegex(ValueError,'budget'):
                add_town_actions(RomBuild(load_base()))

    def test_home_book_keeps_its_approved_text_after_private_consumer_relocation(self):
        from tools.build_dialogue import add_dialogue
        from tools.verify_home_books import EnglishTrace
        build=RomBuild(load_base());dialogue=add_dialogue(build,include_story=False)
        town=add_town_actions(build)
        row=next(r for r in town['entries'] if r['index']==59)
        prior=next(r for r in dialogue['entries'] if r['id']==row['id'])
        self.assertNotIn('english',prior)  # Compiled dialogue records carry bytes/layout.
        trace=EnglishTrace(None,'view-empty',{'dialogue':dialogue,'town_actions':town})
        relocated=trace.checks.resources[row['offset']+0x08000000]
        self.assertEqual(relocated['encoded_hex'],prior['encoded_hex'])
        self.assertEqual(relocated['id'],prior['id'])
