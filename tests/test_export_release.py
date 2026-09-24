"""The public ROM/patch pair must agree and survive rejected exports."""
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from tools.bps import create_patch
from tools.export_release import NAME, run
from tools.rom import digest


class ExportReleaseTests(unittest.TestCase):
    def test_round_trip_and_rejected_update_preserves_previous_pair(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, output = root / 'compiler', root / 'release'
            source.mkdir()
            original = bytes(range(256)) * 8
            translated = original[:200] + b'English' + original[207:]
            base = root / 'japanese.gba'
            base.write_bytes(original)
            target = source / f'{NAME}.gba'
            target.write_bytes(translated)
            patch_file = source / f'{NAME}.bps'
            ledger = {'source_sha256': digest(original), 'output_sha256': digest(translated),
                      'total_reviewed_inserted_resources': 1,
                      'bps': create_patch(base, target, patch_file)}
            ledger_file = source / 'build.json'
            ledger_file.write_text(json.dumps(ledger))
            with patch('tools.export_release.load_base', return_value=original), \
                    patch('tools.export_release.default_rom', return_value=base):
                manifest = run(source, output)
                self.assertEqual((output / f'{NAME}.gba').read_bytes(), translated)
                self.assertEqual((output / f'{NAME}.bps').read_bytes(), patch_file.read_bytes())
                self.assertTrue(manifest['patch_apply_matches_rom'])
                before = {p.name: p.read_bytes() for p in output.iterdir()}
                # A ledger matching a damaged BPS must still fail patch application.
                damaged = bytearray(patch_file.read_bytes())
                damaged[-1] ^= 0x80
                patch_file.write_bytes(damaged)
                ledger['bps']['patch_sha256'] = digest(damaged)
                ledger_file.write_text(json.dumps(ledger))
                with self.assertRaises(subprocess.CalledProcessError):
                    run(source, output)
                self.assertEqual(before, {p.name: p.read_bytes() for p in output.iterdir()})
                self.assertEqual(base.read_bytes(), original)
                self.assertEqual(target.read_bytes(), translated)


if __name__ == '__main__':
    unittest.main()
