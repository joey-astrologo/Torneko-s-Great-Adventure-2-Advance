"""Capture unmodified native title references on disposable cartridges."""
import json
import struct

import mgba.log
from tools.emulator import Debugger, Session, BIOS, version
from tools.extract_graphics_audition import save_json
from tools.rom import ROOT, default_rom, digest, load_base, require
from tools.trace_graphics_sources import BACKGROUND_TABLE, GraphicsTrace, tiled_image

OUT = ROOT / 'build/title-audition'
# Original artwork reference retained after the approved title insertion.
BASELINE = ROOT / 'build/title-insertion/pre-insertion/torneko-2-english.gba'


def capture(rom, name, menu=False):
    folder = OUT / 'reference' / name
    cases = []
    with Session(rom, folder) as game:
        observer = GraphicsTrace(game, rom)
        with Debugger(game, observer.callback, max_events=10000) as trace:
            for address in GraphicsTrace.ADDRESSES[:7]:
                trace.breakpoint(address)
            stages = [('title', None, 600)]
            if menu:
                stages += [('menu', 'START', 180), ('name', 'A', 180)]
            for label, key, frames in stages:
                game.press(key, wait=frames) if key else game.frames(frames)
                screen = game.capture(label)
                memory, selected = game.core.memory, observer.backgrounds[-1]
                start = selected['resource_offset']
                tiles = rom[start + 512:start + 38912]
                require(bytes(memory[0x06000000:0x06009600]) == tiles, 'Native tiles differ')
                for y in range(20):
                    require([memory.u16[0x0600B000+y*64+x*2] for x in range(30)] == list(range(y*30,y*30+30)), 'Native map differs')
                palette = bytes(memory[0x05000000:0x05000200])
                background = tiled_image(tiles, palette, 240, 160, 8)
                background.save(folder / f'{label}-background.png')
                (folder / f'{label}.palette').write_bytes(palette)
                (folder / f'{label}.tiles').write_bytes(tiles)
                if label == 'title':
                    require(selected['index'] == 16, 'Unexpected title record')
                    require(screen.tobytes() == background.tobytes(), 'Full native title differs from reconstruction')
                cases.append({'id': f'{name}/{label}', 'frame': game.core.frame_counter,
                              'rom_sha256': digest(rom), 'selected': selected,
                              'png_sha256': digest((folder / f'{label}.png').read_bytes()),
                              'rgb_sha256': digest(screen.tobytes()), 'tiles_sha256': digest(tiles),
                              'palette_sha256': digest(palette), 'complete_native_frame_matches': label == 'title'})
        save_json(folder / 'trace.json', {'source_sha256': digest(rom), 'inputs': game.inputs,
                  'background_loads': observer.backgrounds, 'native_copies': observer.copies,
                  'cases': cases, 'scope': 'Native cold boot and ordinary inputs; no state or register overrides.'})
    return cases


def run():
    mgba.log.silence()
    original, baseline = load_base(), BASELINE.read_bytes()
    source_save = default_rom().with_suffix('.sav')
    protected = [default_rom(), source_save, BASELINE, BASELINE.with_suffix('.bps')]
    before = {str(p.relative_to(ROOT)): digest(p.read_bytes()) for p in protected}
    cases = capture(original, 'japanese', menu=True) + capture(baseline, 'english')
    for key in ('rgb_sha256', 'tiles_sha256', 'palette_sha256'):
        require(cases[0][key] == cases[-1][key], f'Current English title differs: {key}')
    palette = (OUT / 'reference/japanese/title.palette').read_bytes()
    colors = []
    for value in struct.unpack('<256H', palette):
        colors.append([((value >> shift & 31) << 3) | ((value >> shift & 31) >> 2) for shift in (0,5,10)])
    save_json(OUT / 'reference/palette.json', colors)
    require(original[0x5FD98:0x5FD9D] == bytes((13,18,19,20,21)), 'Menu selector changed')
    menu_family = []
    for index in original[0x5FD98:0x5FD9D]:
        record = BACKGROUND_TABLE + index * 20
        source = struct.unpack_from('<I', original, record)[0] - 0x08000000
        raw_palette = original[source:source+512]
        image = tiled_image(original[source+512:source+38912], raw_palette, 240,160,8)
        path = OUT / 'reference' / f'menu-{index}-stored-palette.png'
        image.save(path)
        menu_family.append({'index': index, 'record_offset': record, 'record_hex': original[record:record+20].hex(),
                            'resource_offset': source, 'resource_end_exclusive': source+38912,
                            'sha256': digest(original[source:source+38912]),
                            'image': str(path.relative_to(OUT)),
                            'native_observed': index == cases[1]['selected']['index'],
                            'preview': 'Decoded stored palette, before native calibration/fades.'})
    require(cases[1]['tiles_sha256'] == cases[2]['tiles_sha256'], 'Menu/name backgrounds differ')
    require(all(digest((ROOT/p).read_bytes()) == value for p,value in before.items()), 'Protected file changed')
    save_json(OUT / 'reference/provenance.json', {
        'passed': True, 'source_rom': str(default_rom().relative_to(ROOT)), 'source_sha256': digest(original),
        'source_save_sha256': before[str(source_save.relative_to(ROOT))], 'baseline_rom': str(BASELINE.relative_to(ROOT)),
        'baseline_sha256': digest(baseline), 'emulator': version(), 'bios': BIOS,
        'cases': cases, 'menu_background_candidates': menu_family, 'original_files_and_reference_unchanged': True,
        'protected_hashes': before, 'title_reference_matches_pre_insertion_build': True,
        'scope': 'Unmodified native title at cold-boot frame 600 for both ROMs. Japanese START then A for menu/name. Separate stored-palette previews for all five menu backgrounds; only one selected natively.'})
    print('Captured title reference; Japanese/pre-insertion English pixels identical.')


if __name__ == '__main__':
    run()
