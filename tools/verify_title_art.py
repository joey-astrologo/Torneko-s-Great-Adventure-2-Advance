"""Native title, all five menu scenes, UI restoration and palette validation."""
import argparse
import html
import json
import struct
from pathlib import Path
import mgba.log
from PIL import Image
from tools.emulator import Session, Debugger, BIOS, version
from tools.rom import ROOT, load_base, default_rom, digest, require
from tools.extract_graphics_audition import save_json
from tools.title_art import SOURCES, TABLE, calibrate, edited, linear_tiles, rgb
from tools.trace_graphics_sources import GraphicsTrace, tiled_image

OUT=ROOT/'build/title-insertion'
BASELINE=OUT/'comparison'
CASES=[(13,4,'Family'),(18,7,'Monsters and slime'),(19,0,'Monster collage'),(20,2,'Treasure chest'),(21,1,'Village')]


def unchanged_area(image,index):
    if index==16:return image.crop((0,136,240,160)).tobytes()
    if index==13:return image.crop((0,0,240,124)).tobytes()+image.crop((0,124,164,160)).tobytes()
    return image.crop((0,36,240,160)).tobytes()+image.crop((0,0,164,36)).tobytes()


def run_case(rom,index,delay,folder,base=None,initial_save=None):
    original=load_base();snapshots=[];fade=[]
    with Session(rom,folder,initial_save=initial_save) as g:
        observer=GraphicsTrace(g,rom)
        with Debugger(g,observer.callback,max_events=20000) as trace:
            for address in GraphicsTrace.ADDRESSES[:7]:trace.breakpoint(address)
            g.frames(260)
            for frame in range(261,311):
                g.frames(1)
                m=g.core.memory;picture=g.screen.to_pil().convert('RGB');row=observer.backgrounds[-1] if observer.backgrounds else None
                checked=False
                if row and row['index']==16 and m.u16[0x04000000]&0x100:
                    at=row['resource_offset'];palette=bytes(m[0x05000000:0x05000200])
                    expected=tiled_image(rom[at+512:at+38912],palette,240,160,8)
                    require(expected.tobytes()==picture.tobytes(),f'Title transition frame {frame} differs')
                    checked=True
                fade.append({'frame':frame,'rgb_sha256':digest(picture.tobytes()),'dispcnt':m.u16[0x04000000],
                             'native_title_pixels_checked':checked})
            g.frames(600+delay-g.core.frame_counter)
            for phase,key,wait in [('title',None,0),('menu','START',180),('name','A',180),('cancel','B',120),('reopen','A',120),('back','B',120)]:
                if key:g.press(key,wait=wait)
                picture=g.capture(phase);m=g.core.memory;row=observer.backgrounds[-1];selected=row['index'];at=row['resource_offset']
                require(selected in SOURCES,'Unexpected native background')
                if phase=='menu' and initial_save is None:require(selected==index,'Ordinary RNG selection differs')
                tiles=rom[at+512:at+38912];count=256 if selected==16 else 240
                require(bytes(m[0x06000000:0x06009600])==tiles,'Native full tile upload differs')
                for y in range(20):require([m.u16[0x0600B000+y*64+x*2] for x in range(30)]==list(range(y*30,y*30+30)),'Native background map differs')
                palette=bytes(m[0x05000000:0x05000200]);gamma=struct.unpack('<i',bytes(m[0x03000C38:0x03000C3C]))[0];level=m.u32[0x03000C3C];mono=bool(m.u16[0x03000A0E])
                wanted=b''.join(struct.pack('<H',calibrate(c,original,gamma,level,mono)) for c in struct.unpack('<256H',rom[at:at+512]))
                require(palette[:count*2]==wanted[:count*2],'Native calibrated palette differs')
                background=tiled_image(tiles,palette,240,160,8);background.save(folder/f'{phase}-background.png')
                if phase=='title':require(background.tobytes()==picture.tobytes(),'Native full title differs')
                if phase=='menu':
                    rect=(164,124,240,160) if selected==13 else (164,0,240,36)
                    require(picture.crop(rect).tobytes()==background.crop(rect).tobytes(),'Start menu interferes with corner logo')
                snapshot={'phase':phase,'frame':g.core.frame_counter,'index':selected,'picture':picture,
                          'ui_vram':bytes(m[0x06009600:0x06018000]),'ui_palette':palette[480:], 'oam':bytes(m[0x07000000:0x07000400]),
                          'palette_sha256':digest(palette),'tile_sha256':digest(tiles),'gamma':gamma,'level':level,'monochrome':mono,
                          'png_sha256':digest((folder/f'{phase}.png').read_bytes()),'pixels_compared':38400 if phase=='title' else None}
                if base:
                    previous=base[len(snapshots)]
                    require(previous['index']==selected and previous['frame']==g.core.frame_counter,'Baseline route changed')
                    require(unchanged_area(picture,selected)==unchanged_area(previous['picture'],selected),'Unrelated scene pixels changed')
                    for field in ('ui_vram','oam'):require(snapshot[field]==previous[field],f'Native {field} changed')
                    if selected!=16:require(snapshot['ui_palette']==previous['ui_palette'],'UI palette changed')
                    snapshot['all_unedited_screen_pixels_and_ui_bytes_match_baseline']=True
                snapshots.append(snapshot)
        report={'source_sha256':digest(rom),'inputs':g.inputs,'background_loads':observer.backgrounds,'native_copies':observer.copies,
                'transition_frames':fade,'cases':[{k:v for k,v in s.items() if k not in ('picture','ui_vram','ui_palette','oam')} for s in snapshots],
                'controlled_overrides':[], 'scope':'Ordinary cold boot, START, name-entry opening, B cancellation and A reopening. Complete graphics uploads/maps/calibrated palettes checked; native UI compared against identical inputs on the pre-insertion build.'}
        save_json(folder/'report.json',report)
    return snapshots,report


def palette_probes(rom,output):
    """Controlled pure-function calls on a restored snapshot; no RAM ownership claim."""
    from tools.verify_compact_font import call_thumb
    original=load_base();results=[]
    with Session(rom,output) as g:
        g.frames(600);snap=g.snapshot()
        for gamma in (-2,-1):
            for level in range(5):
                for mono in (False,True):
                    g.restore(snap);g.core.memory.u32[0x03000C38]=gamma&0xffffffff;g.core.memory.u32[0x03000C3C]=level
                    for c in range(32):
                        value=c|((31-c)<<5)|(((c*7)%32)<<10)
                        first=call_thumb(g,0x08003490 if mono else 0x08003434,value)['r0']
                        actual=call_thumb(g,0x08003550 if mono else 0x080034F8,first)['r0']
                        require(actual==calibrate(value,original,gamma,level,mono),'Native calibration model mismatch')
                    results.append({'gamma':gamma,'level':level,'monochrome':mono,'colors_checked':32})
        g.restore(snap)
        require(g.snapshot().battery==snap.battery,'Palette probes changed battery')
    return {'cases':results,'colors_checked':640,'scope':'Controlled native colour functions, two signed gamma rows, five palette levels, colour/monochrome. Only 03000C38/03000C3C temporarily overridden, with full snapshot restoration. All calls preserve callee-saved registers/SP.'}


def run(source):
    mgba.log.silence();rom=(source/'torneko-2-english.gba').read_bytes();build=json.loads((source/'build.json').read_text())
    # Rebuild the same current text/arrival assets with original title art.
    # Future text batches must not depend on a historical English release.
    from tools.build_english import build_rom
    previous, reference_build=build_rom(include_title_art=False)
    BASELINE.mkdir(parents=True,exist_ok=True)
    (BASELINE/'torneko-2-english.gba').write_bytes(previous)
    save_json(BASELINE/'build.json',reference_build)
    save=default_rom().with_suffix('.sav');save_hash=digest(save.read_bytes())
    require(digest(rom)==build['output_sha256'],'Build identity differs')
    reports=[]
    for index,delay,name in CASES:
        old,_=run_case(previous,index,delay,OUT/'native-baseline'/str(index))
        _,report=run_case(rom,index,delay,OUT/'native'/str(index),base=old)
        reports.append({'index':index,'name':name,'report':report})
    supplied=save.read_bytes()
    old,_=run_case(previous,19,0,OUT/'native-baseline/supplied',initial_save=supplied)
    _,supplied_report=run_case(rom,19,0,OUT/'native/supplied',base=old,initial_save=supplied)
    calibration=palette_probes(rom,OUT/'calibration-probes')
    require(digest(save.read_bytes())==save_hash and digest(load_base())==build['source_sha256'],'Original files changed')
    result={'passed':True,'rom_sha256':digest(rom),'baseline_sha256':digest(previous),'source_save_sha256':save_hash,
            'emulator':version(),'bios':BIOS,'cases':reports,'supplied_save_route':supplied_report,'palette_probes':calibration,
            'generator_sha256':digest(Path(__file__).read_bytes()),'source_files_unchanged':True,
            'scope':'All six approved resources rendered natively. Five ordinary menu selections plus supplied-save boot; start menu/name editor/cancel/reopen compared with previous ROM. 50 consecutive title-transition frames per route, stable full-title pixels, tile/map/palette/UI isolation, and 640 controlled native colour conversions. No full-game coverage claim.'}
    save_json(OUT/'native-report.json',result)
    cards=[]
    for index,_,name in CASES:
        cards.append(f'<section><h2>{html.escape(name)}</h2><div class="row">'+''.join(f'<figure><figcaption>{phase}</figcaption><img src="native/{index}/{phase}.png"></figure>' for phase in ('menu','name','cancel','reopen'))+'</div></section>')
    page='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Torneko 2 · Inserted title and logos</title><style>body{background:#101a23;color:#eee;font:16px system-ui;margin:32px}h1,h2{color:#efbc68}.row{display:flex;gap:16px;flex-wrap:wrap}figure{margin:0 0 24px}img{width:480px;max-width:100%;image-rendering:pixelated}figcaption{margin:8px 0}section{border-top:1px solid #345;padding-top:16px}a{color:#8bcfe4}</style><h1>Inserted title and corner logos</h1><p>Actual mGBA screenshots from the patched ROM. Floating corner lettering; original title footer and surrounding artwork preserved.</p><p><a href="native-report.json">Native checks</a> · <a href="acceptance.json">Insertion acceptance</a> · <a href="../torneko-2-english.gba">Latest ROM</a> · <a href="../torneko-2-english.bps">Latest BPS</a></p><h2>Title screen</h2><img src="native/19/title.png">'''+''.join(cards)+f'<p>ROM SHA256: {digest(rom)}</p></html>'
    (OUT/'index.html').write_text(page)
    print('Title/background native validation passed: five selections, supplied save, UI restoration and 640 colour probes.')
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,default=ROOT/'build/english');run(p.parse_args().source.resolve())
