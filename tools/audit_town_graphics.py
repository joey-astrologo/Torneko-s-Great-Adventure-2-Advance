"""Inspect the scrolling scene table, replacements and static object layers.

The native tile getter is tested with explicit disposable state overrides.
Object palettes come from the native initialized lookup table. These checks do
not establish ordinary scene entry or cover independently animated NPC sprites.
"""
import argparse
import html
import json
from pathlib import Path
import struct

import mgba.log
from PIL import Image

from tools.emulator import Session
from tools.rom import ROOT, default_rom, digest, load_base, require
from tools.trace_graphics_sources import tiled_image
from tools.verify_compact_font import call_thumb
from tools.verify_storage import SAVE

BASE, TABLE, COUNT = 0x08000000, 0x13E674, 28


def word(data, at):
    return struct.unpack_from('<I', data, at)[0]


def descriptors(rom):
    require(word(rom, 0x3C5C) == BASE+TABLE and rom[0x3C0A:0x3C0E].hex() == '1b2c00dd',
            'Reinspect scrolling scene table or upper bound')
    rows = []
    for index in range(COUNT):
        at = TABLE+index*24
        source,w,h,n,pad,overlays,door,objects = struct.unpack_from('<I4H3I',rom,at)
        require(w > 0 and h > 0 and w % 8 == 0 and pad == 0, 'Unexpected scene dimensions')
        source -= BASE
        require(512 <= source <= len(rom)-w*(h//8*8), 'Scene pixels outside ROM')
        row = dict(index=index, descriptor_range=[at,at+24], descriptor_hex=rom[at:at+24].hex(),
            resource_range=[source,source+w*(h//8*8)], palette_range=[source-512,source],
            logical_dimensions=[w,h], tile_dimensions=[w//8,h//8], overlays=[], door=None, objects=[])
        for i in range(n+bool(door)):
            at = (overlays+i*16 if i<n else door)-BASE
            pointer,x,y,width,height,flags = struct.unpack_from('<I4HI',rom,at)
            require(width and height and x+width <= w//8 and y+height <= h//8,
                    'Replacement rectangle outside drawable scene')
            pointer -= BASE
            require(0 <= pointer <= len(rom)-width*height*64, 'Replacement pixels outside ROM')
            replacement = dict(descriptor_range=[at,at+16], descriptor_hex=rom[at:at+16].hex(),
                resource_range=[pointer,pointer+width*height*64], rectangle_tiles=[x,y,width,height],
                flags=flags, kind='overlay' if i<n else 'door')
            if i<n:
                row['overlays'].append(replacement)
            else:
                row['door']=replacement
        if objects:
            count, pointer = struct.unpack_from('<II',rom,objects-BASE)
            for i in range(count):
                at = pointer-BASE+i*16
                x,y,width,height,tile,palette,pad,flags = struct.unpack_from('<hhBBHHHI',rom,at)
                require(width and height and pad == 0, 'Unexpected scene object shape')
                pixels = word(rom,0x2C2C)-BASE+tile*128
                require(0 <= pixels <= len(rom)-width*height*128, 'Object pixels outside ROM')
                row['objects'].append(dict(index=i, descriptor_range=[at,at+16],
                    descriptor_hex=rom[at:at+16].hex(), position=[x,y], dimensions=[width*16,height*16],
                    tile=tile, palette=palette, flags=flags,
                    resource_range=[pixels,pixels+width*height*128]))
        rows.append(row)
    return rows


def selected_pointer(row, x, y, flags=0, door=False):
    width,height=row['tile_dimensions']
    if not (0 <= x < width and 0 <= y < height):
        return 0
    for replacement in row['overlays'] + ([row['door']] if door and row['door'] else []):
        if replacement['kind']=='overlay' and not replacement['flags'] & flags:
            continue
        rx,ry,rw,rh=replacement['rectangle_tiles']
        if rx <= x < rx+rw and ry <= y < ry+rh:
            return BASE+replacement['resource_range'][0]+((y-ry)*rw+x-rx)*64
    return BASE+row['resource_range'][0]+(y*width+x)*64


def corners(x,y,w,h):
    return {(x,y),(x+w-1,y),(x,y+h-1),(x+w-1,y+h-1),(x+w//2,y+h//2)}


def native_getters(game, rows):
    snapshot=game.snapshot()
    cases=[]
    m=game.core.memory
    for row in rows:
        variants=[('base',0,False,corners(0,0,*row['tile_dimensions']) |
                  {(-1,0),(0,-1),(row['tile_dimensions'][0],0),(0,row['tile_dimensions'][1])})]
        for index,replacement in enumerate(row['overlays']):
            variants.append((f'overlay-{index}',replacement['flags'],False,
                             corners(*replacement['rectangle_tiles'])))
        if row['door']:
            variants.append(('door',0,True,corners(*row['door']['rectangle_tiles'])))
        for label,flags,door,points in variants:
            game.restore(snapshot)
            # The descriptor and selector state are explicit research inputs.
            # Map 0 uses the normal odd/even door branch; scenes 25/26 use the
            # cutscene branch as well. Neither is presented as natural access.
            values=[(0x02001274,BASE+row['descriptor_range'][0],4),
                    (0x02001278,row['index'],4),(0x0200127C,flags,4),
                    (0x0200FED8,0,1),(0x0200FF19,int(door),1),(0x0201183C,int(door),1)]
            controls=[]
            for address,value,size in values:
                before=bytes(m[address:address+size])
                data=value.to_bytes(size,'little')
                controls.append(dict(address=address,before_hex=before.hex(),after_hex=data.hex()))
                for offset,byte in enumerate(data):
                    m.u8[address+offset]=byte
            results=[]
            for x,y in sorted(points):
                expected=selected_pointer(row,x,y,flags,door)
                result=call_thumb(game,0x0800361C,x+3,y)
                require(result['r0']==expected, 'Native scene tile selector differs: '+str((row['index'],label,x,y)))
                results.append(dict(tile=[x,y],expected_pointer=expected,**result))
            require(game.snapshot().battery==snapshot.battery, 'Tile getter changed battery')
            cases.append(dict(scene=row['index'],variant=label,controls=controls,results=results))
    game.restore(snapshot)
    return dict(cases=cases, calls=sum(len(c['results']) for c in cases),
                original_snapshot_sha256=digest(snapshot.state),
                battery_unchanged=True, full_snapshot_restored=True)


def run(source, output):
    mgba.log.silence()
    original=load_base()
    save=default_rom().with_suffix('.sav')
    source_save_sha=digest(save.read_bytes())
    rom=(source/'torneko-2-english.gba').read_bytes()
    build=json.loads((source/'build.json').read_text())
    require(digest(rom)==build['output_sha256'], 'Town graphics ROM differs')
    # The complete getter and sprite/palette fetch instructions are unchanged.
    code_ranges=[(0x361C,0x3784),(0x39D0,0x3B0C),(0x3BF4,0x3CE8),
                 (0x2B28,0x2C38),(0x3118,0x3238)]
    for lo,hi in code_ranges:
        require(original[lo:hi]==rom[lo:hi], 'Reinspect changed graphics consumer')
    rows=descriptors(rom)
    require(rows==descriptors(original), 'Scrolling scene descriptors changed')
    output.mkdir(parents=True,exist_ok=True)
    pictures=[]
    for row in rows:
        index=row['index']
        lo,hi=row['palette_range']
        palette=rom[lo:hi]
        regions=[('base',row['resource_range'],[n*8 for n in row['tile_dimensions']])]
        regions += [(f'overlay-{i}',v['resource_range'],[n*8 for n in v['rectangle_tiles'][2:]])
                    for i,v in enumerate(row['overlays'])]
        if row['door']:
            v=row['door']
            regions.append(('door',v['resource_range'],[n*8 for n in v['rectangle_tiles'][2:]]))
        for label,(lo,hi),dimensions in regions:
            require(rom[lo:hi]==original[lo:hi], 'Scene graphic pixels changed')
            picture=tiled_image(rom[lo:hi],palette,*dimensions,8)
            file=f'{index:02}-{label}.png'
            picture.save(output/file)
            pictures.append((file,picture))
    with Session(rom,output/'native',initial_save=SAVE.read_bytes()) as game:
        game.frames(600);game.press('START',wait=180);game.press('A',wait=300)
        require(game.core.memory.u32[0x0200FF0C]==288 and game.core.memory.u32[0x0200FF10]==224,
                'Native storage graphics fixture differs')
        snapshot=game.snapshot()
        native=native_getters(game,rows)
        m=game.core.memory
        unique={}
        for row in rows:
            for obj in row['objects']:
                palette=obj['palette']
                slot=0x02000B00+(palette>>4)*4
                lookup=m.u32[slot]+(palette&15)*2
                resolved=m.u16[lookup]
                require(resolved<=0x20C, 'Object palette lookup outside native bound')
                address=word(rom,0x31F4 if resolved<=0x1CC else 0x3228)+resolved*32
                raw=bytes(m[address:address+32])
                require(BASE<=address<BASE+len(rom)-31 and raw==rom[address-BASE:address-BASE+32],
                        'Object palette is not an exact ROM resource')
                obj.update(palette_lookup=lookup,palette_id=resolved,palette_source=address,
                           palette_hex=raw.hex(),palette_lookup_pointer=m.u32[slot])
                key=tuple(obj['resource_range']),tuple(obj['dimensions']),raw
                if key not in unique:
                    width,height=obj['dimensions']
                    picture=Image.new('RGB',(width,height))
                    lo,hi=obj['resource_range']
                    require(rom[lo:hi]==original[lo:hi], 'Object graphic changed')
                    for i in range((hi-lo)//128):
                        piece=tiled_image(rom[lo+i*128:lo+(i+1)*128],raw,16,16,4)
                        picture.paste(piece,(i%(width//16)*16,i//(width//16)*16))
                    file=f'{row["index"]:02}-object-{obj["index"]}.png'
                    picture.save(output/file)
                    unique[key]=file
                    pictures.append((file,picture))
                obj['image']=unique[key]
        require(game.snapshot().battery==snapshot.battery, 'Research changed battery')
        inputs=game.inputs
    require(digest(load_base())==digest(original) and digest(save.read_bytes())==source_save_sha,
            'Supplied source ROM/save changed')
    report=dict(passed=True,rom_sha256=digest(rom),source_rom_sha256=digest(original),
        source_save_sha256=source_save_sha,fixture_save_sha256=digest(SAVE.read_bytes()),
        tool_sha256=digest(Path(__file__).read_bytes()),address_space='ROM file offsets; exclusive ranges unless CPU address noted',
        table_range=[TABLE,TABLE+24*COUNT],records=rows,native=native,inputs=inputs,
        unchanged_consumer_ranges=[dict(range=[lo,hi],sha256=digest(rom[lo:hi])) for lo,hi in code_ranges],
        unique_object_images=len(unique),scope=__doc__,source_files_unchanged=True)
    (output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    cards=''.join(f'<figure><figcaption>{html.escape(file)}</figcaption><img src="{file}"></figure>'
                  for file,_ in pictures)
    (output/'index.html').write_text('<!doctype html><meta charset="utf-8"><title>Scrolling scene graphics</title>'
        '<style>body{background:#18222b;color:white;font:16px system-ui}figure{display:inline-block;vertical-align:top;margin:16px}'
        'img{image-rendering:pixelated;max-width:100%}a{color:#9df}</style><h1>Scrolling scene graphics</h1>'
        '<p>Decoded bases, flag replacements, door states and static object layers. '
        'Visual review is recorded separately; independently animated actors remain outside this audit.</p>'
        '<a href="report.json">Native selector evidence and source ranges</a>'+cards)
    print('Town graphics:',COUNT,'records;',len(native['cases']),'selector states;',native['calls'],
          'native calls;',len(unique),'unique static object images')
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,default=ROOT/'build/english')
    parser.add_argument('--output',type=Path,default=ROOT/'build/graphics-discovery/town')
    args=parser.parse_args()
    run(args.source,args.output)
