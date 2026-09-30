"""Export the latest compiled ROM and verified BPS pair directly into build/."""

import argparse
import json
from pathlib import Path
import subprocess
import tempfile

from tools.rom import ROOT, default_rom, digest, load_base, require

NAME = 'torneko-2-english'


def run(source=ROOT / 'build/english', output=ROOT / 'build'):
    source, output = Path(source).resolve(), Path(output).resolve()
    require(source != output, 'Release output must differ from the compiler directory')
    ledger_bytes = (source / 'build.json').read_bytes()
    ledger = json.loads(ledger_bytes)
    rom = (source / f'{NAME}.gba').read_bytes()
    patch = (source / f'{NAME}.bps').read_bytes()
    base = load_base()
    require(digest(rom) == ledger['output_sha256'], 'Compiled ROM differs from ledger')
    require(digest(base) == ledger['source_sha256'], 'Release base differs from ledger')
    bps = ledger['bps']
    require(bps['source_sha256'] == digest(base) and
            bps['target_sha256'] == digest(rom) and
            bps['patch_sha256'] == digest(patch) and bps['apply_matches_target'],
            'Compiled BPS differs from ledger')
    output.mkdir(parents=True, exist_ok=True)
    require(default_rom().resolve() not in
            {output / f'{NAME}.gba', output / f'{NAME}.bps'}, 'Cannot replace the source ROM')
    manifest = {
        'rom': f'{NAME}.gba', 'patch': f'{NAME}.bps',
        'source_sha256': digest(base), 'rom_sha256': digest(rom),
        'patch_sha256': digest(patch), 'build_ledger_sha256': digest(ledger_bytes),
        'inserted_resources': ledger['total_reviewed_inserted_resources'],
        'inserted_graphics': ledger.get('total_reviewed_inserted_graphics', 0),
        'patch_apply_matches_rom': True,
        'status': 'development',
        'scope': 'Latest compiled English build; translation and full-game playtesting remain in progress. '
                 'Patch verification does not establish native acceptance or complete localization.',
    }
    # Validate in a disposable directory before touching the previous exported pair.
    # The manifest is installed last and is the consistency marker for both files.
    with tempfile.TemporaryDirectory(prefix='.release-', dir=output) as directory:
        staged = Path(directory)
        (staged / 'source.gba').write_bytes(base)
        (staged / f'{NAME}.gba').write_bytes(rom)
        (staged / f'{NAME}.bps').write_bytes(patch)
        applied = staged / 'applied.gba'
        subprocess.run([str(ROOT / '.tools/bin/flips'), '--apply', '--exact',
                        str(staged / f'{NAME}.bps'), str(staged / 'source.gba'),
                        str(applied)], check=True, capture_output=True)
        require(applied.read_bytes() == rom, 'Release patch does not reproduce the ROM')
        require((source / 'build.json').read_bytes() == ledger_bytes and
                (source / f'{NAME}.gba').read_bytes() == rom and
                (source / f'{NAME}.bps').read_bytes() == patch,
                'Compiler output changed during export')
        (staged / f'{NAME}.release.json').write_text(json.dumps(manifest, indent=2) + '\n')
        (output / f'{NAME}.release.json').unlink(missing_ok=True)
        for suffix in ('gba', 'bps', 'release.json'):
            (staged / f'{NAME}.{suffix}').replace(output / f'{NAME}.{suffix}')
    print(output / f'{NAME}.gba')
    print(output / f'{NAME}.bps')
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=ROOT / 'build/english')
    parser.add_argument('--output', type=Path, default=ROOT / 'build')
    args = parser.parse_args()
    run(args.source, args.output)
