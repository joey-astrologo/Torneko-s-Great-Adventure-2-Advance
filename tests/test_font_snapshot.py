"""Build-scoped validation cannot leak mutations or accept changed inputs."""
import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from tools import compact_font as font
from tools.rom import load_base


class FontSnapshot(unittest.TestCase):
    def test_one_validation_with_independent_results_and_strict_outside_reads(self):
        with patch.object(font,'_validate_font',wraps=font._validate_font) as validate:
            with patch.object(font,'load_base',wraps=load_base) as base:
                with font.font_snapshot():
                    first=font.load_font();original=first['glyphs']['A']['rows'][0]
                    first['glyphs']['A']['rows'][0]='changed'
                    self.assertEqual(font.load_font()['glyphs']['A']['rows'][0],original)
                    self.assertEqual(validate.call_count,1)
                self.assertEqual(base.call_count,2)
                font.load_font();font.load_font()
                self.assertEqual(validate.call_count,3)
                self.assertEqual(base.call_count,4)

    def test_asset_change_aborts_and_context_is_released(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'font.json';path.write_bytes(font.ASSET.read_bytes())
            with self.assertRaisesRegex(ValueError,'Font asset changed during build'):
                with font.font_snapshot():
                    font.load_font(path)
                    # Even an otherwise valid metadata edit must abort this build.
                    data=json.loads(path.read_bytes());data['snapshot_test']='changed'
                    path.write_text(json.dumps(data))
                    self.assertNotIn('snapshot_test',font.load_font(path))
            self.assertIsNone(font._SNAPSHOT.get())
            self.assertEqual(font.load_font(path)['snapshot_test'],'changed')

    def test_base_change_at_exit_aborts_and_context_is_released(self):
        original=load_base()
        with patch.object(font,'load_base',side_effect=[original,original[:-1]+b'!']):
            with self.assertRaisesRegex(ValueError,'Base ROM changed'):
                with font.font_snapshot():font.load_font()
        self.assertIsNone(font._SNAPSHOT.get())

    def test_invalid_font_is_not_cached(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'font.json';data=json.loads(font.ASSET.read_bytes())
            del data['glyphs']['A'];path.write_text(json.dumps(data))
            with font.font_snapshot():
                with self.assertRaisesRegex(ValueError,'cover all printable ASCII'):font.load_font(path)
                self.assertEqual(font._SNAPSHOT.get()['fonts'],{})
