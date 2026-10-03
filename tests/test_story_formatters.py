"""Consumer classification and bounded story substitutions."""
import json, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
from tools.rom import ROOT, load_base, digest
from tools.rom_build import RomBuild
from tools.event_prose_text import add_prose, STATIC_FORMAT_SOURCES
from tools.well_level_text import CATALOG as WELL, compile_acknowledgement
from tools.village_prose_text import CATALOG as VILLAGE, compile_village

class StoryFormatters(unittest.TestCase):
    def test_story_consumers_share_banks_without_overlapping_slots(self):
        import struct
        from tools.opening_text import banks, BANK_RAM
        from tools.event_text import table_entries
        from tools.floor_progress_text import add_progress
        from tools.well_level_text import add_well_level
        from tools.village_prose_text import add_village_prose
        from tools.medal_text import add_medals
        from tools.story_command_text import add_commands
        resources=banks();data={b['id']:bytearray(b['data']) for b in resources}
        changed={b['id']:[] for b in resources};build=RomBuild(load_base())
        ordinary,_=add_prose(build,data,changed)
        offsets={r['id']:r['rom_offset'] for r in ordinary}
        for insert in (add_progress,add_well_level,add_village_prose,add_medals):
            for row in insert(build,data,changed)['entries']:
                self.assertNotIn(row['id'],offsets)
                offsets[row['id']]=row['offset']
        for row in add_commands(build,data,changed)['entries']:
            self.assertNotIn(row['id'],offsets)
            offsets[row['id']]=row['rom_offset']
        self.assertEqual(len(offsets),909)
        self.assertEqual({r['id'] for r in ordinary if r.get('editorial_reconstruction')},
                         {'event-bank-3.3ec2', 'event-bank-4.0d25'})
        for bank in resources:
            slots=changed[bank['id']];self.assertEqual(len(slots),len(set(slots)))
            restored=bytearray(data[bank['id']])
            for slot in slots:restored[slot:slot+4]=bank['data'][slot:slot+4]
            self.assertEqual(restored,bank['data'])
            for entry in table_entries(bank):
                if entry['id'] not in offsets:continue
                value=struct.unpack_from('<I',data[bank['id']],entry['slot'])[0]
                target=(BANK_RAM+entry['strings_offset']+entry['group_offset']+value)&0xFFFFFFFF
                self.assertEqual(target,0x08000000+offsets[entry['id']])
        build.finish()

    def test_static_formatter_consumers_cannot_enter_ordinary_prose(self):
        drafts={r['id']:r for name in ('final-quest','postgame')
                for r in json.loads((ROOT/f'translations/{name}-draft.json').read_text())['entries']}
        for ident in STATIC_FORMAT_SOURCES:
            source=drafts[ident]
            self.assertNotIn(b'%',bytes.fromhex(source['raw_hex']))
            row={'id':ident,'source_hex':source['raw_hex'],'source_sha256':source['source_sha256'],
                 'english':source['english_draft'],'status':'reviewed','prose_review':source['prose_review']}
            with tempfile.TemporaryDirectory(prefix='static-formatter-test-') as folder:
                path=Path(folder)/'catalog.json'
                path.write_text(json.dumps({'base_rom_sha256':digest(load_base()),'entries':[row],'excluded':[]}))
                with patch('tools.event_prose_text.CATALOG',path):
                    with self.assertRaisesRegex(ValueError,'Special formatter'):
                        add_prose(RomBuild(load_base()),{}, {})

    def test_well_labels_are_bounded_as_complete_substitutions(self):
        data=json.loads(WELL.read_text());row=data['entries'][0]
        payload,layout=compile_acknowledgement(row,data['labels'])
        self.assertEqual(payload.count(b'%s'),1)
        self.assertEqual(layout['field_width'],42)
        self.assertLessEqual(layout['maximum_formatted_bytes'],256)
        with self.assertRaisesRegex(ValueError,'wrapping reserve'):
            compile_acknowledgement(row,[{'english':'W'*20}])
        with self.assertRaisesRegex(ValueError,'substitution'):
            compile_acknowledgement(row|{'english':row['english']+' {difficulty}'},data['labels'])

    def test_village_argument_and_output_have_separate_budgets(self):
        row=next(r for r in json.loads(VILLAGE.read_text())['entries'] if r['id']=='event-bank-5.4a81')
        payload,layout=compile_village(row)
        self.assertEqual(payload.count(b'%s'),1)
        self.assertEqual((layout['field_width'],layout['field_bytes']),(112,16))
        self.assertGreater(layout['maximum_formatted_bytes'],256)
        self.assertLessEqual(layout['maximum_formatted_bytes'],448)
        with self.assertRaisesRegex(ValueError,'stack capacity'):
            compile_village(row|{'english':row['english']+'\n\n'+('A further paragraph. '*8)})
