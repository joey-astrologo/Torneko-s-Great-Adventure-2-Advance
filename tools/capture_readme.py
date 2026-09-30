"""Replay ordinary inputs on the current English ROM for the README gallery."""
import json
import shutil

import mgba.log

from tools.emulator import BIOS, Session, version
from tools.extract_graphics_audition import save_json
from tools.rom import ROOT, default_rom, digest, load_base, require


def run():
    mgba.log.silence()
    route_path = ROOT / 'config/routes/readme.json'
    route = json.loads(route_path.read_text())
    release_path = ROOT / 'build/torneko-2-english.release.json'
    release = json.loads(release_path.read_text())
    rom_path = ROOT / 'build' / release['rom']
    rom = rom_path.read_bytes()
    require(digest(rom) == release['rom_sha256'] == route['reference_rom_sha256'],
            'README route needs review against the current English build')
    require(digest(load_base()) == release['source_sha256'], 'Source identity differs')
    save = default_rom().with_suffix('.sav')
    protected = [default_rom(), save, rom_path, release_path,
                 ROOT / 'build' / release['patch']]
    before = {str(p.relative_to(ROOT)): digest(p.read_bytes()) for p in protected}
    output = ROOT / 'build/readme-captures/native'
    captures = []
    with Session(rom, output) as game:
        for step in route['steps']:
            if 'frames' in step:
                game.frames(step['frames'])
            elif 'press' in step:
                game.press(step['press'], hold=step['hold'], wait=step['wait'])
            else:
                name = step['capture']
                picture = game.capture(name)
                require(picture.size == (240, 160), 'Unexpected screen size')
                require(digest(picture.tobytes()) == route['expected_rgb_sha256'][name],
                        f'Replayed {name} differs from the reviewed native capture')
                captures.append({'file': name + '.png', 'frame': game.core.frame_counter,
                                 'rgb_sha256': digest(picture.tobytes()),
                                 'png_sha256': digest((output / (name + '.png')).read_bytes())})
        inputs = game.inputs
    require({row['file'] for row in captures} ==
            {name + '.png' for name in route['expected_rgb_sha256']}, 'Gallery incomplete')
    require(all(digest((ROOT / path).read_bytes()) == sha for path, sha in before.items()),
            'An original or release file changed')
    destination = ROOT / 'docs/images'
    destination.mkdir(parents=True, exist_ok=True)
    for row in captures:
        shutil.copyfile(output / row['file'], destination / row['file'])
    report = {'passed': True, 'rom_sha256': digest(rom),
              'source_rom_sha256': release['source_sha256'], 'emulator': version(), 'bios': BIOS,
              'route': str(route_path.relative_to(ROOT)), 'route_sha256': digest(route_path.read_bytes()),
              'generator_sha256': digest((ROOT / 'tools/capture_readme.py').read_bytes()),
              'initial_save': 'fresh', 'controlled_overrides': [],
              'images': captures, 'inputs': inputs, 'protected_hashes': before,
              'scope': route['scope'] + ' Unedited 240x160 framebuffer captures; no resizing or compositing.'}
    save_json(output / 'report.json', report)
    save_json(destination / 'provenance.json', report)
    print('README: four native screenshots reproduced from a fresh save; source/release files unchanged.')


if __name__ == '__main__':
    run()
