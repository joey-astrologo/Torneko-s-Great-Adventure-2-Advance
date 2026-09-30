"""Capture all five menu backgrounds through ordinary, timed START inputs."""
import json
import mgba.log
from tools.emulator import Session, Debugger, BIOS, version
from tools.rom import ROOT, load_base, default_rom, digest, require
from tools.extract_graphics_audition import save_json
from tools.trace_graphics_sources import GraphicsTrace, tiled_image
from tools.capture_title_audition import BASELINE, OUT

CASES = [(13,4,'Family'), (18,7,'Monsters and slime'), (19,0,'Monster collage'),
         (20,2,'Treasure chest'), (21,1,'Village')]
FOLDER = OUT / 'backgrounds'


def run():
    mgba.log.silence()
    original, rom = load_base(), BASELINE.read_bytes()
    protected = [default_rom(), default_rom().with_suffix('.sav'), BASELINE, BASELINE.with_suffix('.bps')]
    before = {str(p.relative_to(ROOT)):digest(p.read_bytes()) for p in protected}
    rows = []
    for index,delay,name in CASES:
        folder = FOLDER / 'reference' / str(index)
        rectangle = [164,124 if index == 13 else 0,76,36]
        with Session(rom,folder) as game:
            observer = GraphicsTrace(game,rom)
            with Debugger(game,observer.callback,max_events=10000) as trace:
                for address in GraphicsTrace.ADDRESSES[:7]:
                    trace.breakpoint(address)
                game.frames(600+delay)
                game.press('START',wait=180)
                selected = observer.backgrounds[-1]
                require(selected['index'] == index, 'Native menu selection changed')
                start = selected['resource_offset']
                require(rom[start:start+38912] == original[start:start+38912], 'Current menu resource changed')
                tiles = rom[start+512:start+38912]
                m = game.core.memory
                require(bytes(m[0x06000000:0x06009600]) == tiles, 'Native menu tiles differ')
                for y in range(20):
                    require([m.u16[0x0600B000+y*64+x*2] for x in range(30)] == list(range(y*30,y*30+30)), 'Menu map differs')
                palette = bytes(m[0x05000000:0x05000200])
                background = tiled_image(tiles,palette,240,160,8)
                background.save(folder/'background.png')
                (folder/'native.palette').write_bytes(palette)
                menu = game.capture('menu')
                menu_frame = game.core.frame_counter
                game.press('A',wait=180)
                editor = game.capture('name')
                require(bytes(m[0x06000000:0x06009600]) == tiles, 'Name editor changed background tiles')
                require(bytes(m[0x05000000:0x050001E0]) == palette[:480], 'Name editor changed background palette')
                require(selected['palette_count'] == 240 and max(tiles) < 240, 'Background uses UI palette entries')
                x,y,w,h = rectangle
                region = (x,y,x+w,y+h)
                background_pixels = list(background.crop(region).get_flattened_data())
                overlaps = {label:sum(a!=b for a,b in zip(background_pixels,picture.crop(region).get_flattened_data()))
                            for label,picture in [('menu',menu),('name',editor)]}
                require(overlaps['menu'] == 0, 'Proposed logo rectangle overlaps native start menu')
                files = {label:digest((folder/f'{label}.png').read_bytes()) for label in ('background','menu','name')}
                row = {'index':index,'name':name,'delay_after_frame_600':delay,'menu_frame':menu_frame,
                       'name_frame':game.core.frame_counter,'source_rom_sha256':digest(rom),
                       'background':str((folder/'background.png').relative_to(OUT)),
                       'menu':str((folder/'menu.png').relative_to(OUT)), 'editor':str((folder/'name.png').relative_to(OUT)),
                       'files_sha256':files,'rectangle_xywh':rectangle,'palette_count':240,
                       'native_palette_sha256':digest(palette),'tile_sha256':digest(tiles),
                       'ui_pixels_in_logo_rectangle':overlaps, 'selected':selected,'inputs':game.inputs}
                save_json(folder/'trace.json',{'case':row,'background_loads':observer.backgrounds,'native_copies':observer.copies})
                rows.append(row)
    require(all(digest((ROOT/p).read_bytes()) == sha for p,sha in before.items()), 'Protected files changed')
    save_json(FOLDER/'reference.json',{'passed':True,'source_sha256':digest(original),'baseline_sha256':digest(rom),
              'emulator':version(),'bios':BIOS,'cases':rows,'protected_hashes':before,'original_files_and_release_unchanged':True,
              'scope':'Five naturally selected backgrounds via fresh boot with recorded START timing, then A for name entry. No ROM/RAM/register edits. Native tiles/map/calibrated palette verified; proposed corner rectangles clear of native start menu. Name editor naturally covers parts of the original logo; overlap counts retained. Artwork compositing remains offline.'})
    print('All five native menu/name backgrounds captured; logo rectangles clear of start menu.')


if __name__ == '__main__':
    run()
