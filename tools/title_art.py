"""Owned insertion of approved title and floating-logo menu resources."""
import json
import struct
from tools.rom import ROOT, digest, require

OWNER = 'title-background-artwork'
APPROVAL = ROOT/'assets/title-screen/approved.json'
PACKED = ROOT/'assets/title-screen/packed'
TABLE = 0x13EC14
SOURCES = {16:0x42F138,13:0x555B04,18:0x55F304,19:0x568B04,20:0x572304,21:0x57BB04}
RECORDS = {16:'38f14208000000000000000000000001feffffff',13:'045b550800000000000000000000f000ffffffff',
           18:'04f3550800000000000000000000f000ffffffff',19:'048b560800000000000000000000f000ffffffff',
           20:'0423570800000000000000000000f000ffffffff',21:'04bb570800000000000000000000f000ffffffff'}


def rgb(value):
    return tuple(((value>>s&31)<<3)|((value>>s&31)>>2) for s in (0,5,10))


def calibrate(value, original, gamma, level=4, monochrome=False):
    first=original[0x5FC38+max(-5,min(5,gamma))*32:0x5FC38+max(-5,min(5,gamma))*32+32]
    second=original[0x5FCF8+max(0,min(7,level))*32:0x5FCF8+max(0,min(7,level))*32+32]
    channels=[value>>s&31 for s in (0,5,10)]
    if monochrome:channels=[sum(channels)//3]*3
    channels=[first[v] for v in channels]
    if monochrome:channels=[sum(channels)//3]*3
    return sum(second[v]<<s for v,s in zip(channels,(0,5,10)))


def linear_tiles(tiles):
    return bytes(tiles[(y//8*30+x//8)*64+y%8*8+x%8] for y in range(160) for x in range(240))


def tiled_pixels(pixels):
    return bytes(pixels[(ty+y)*240+tx+x] for ty in range(0,160,8) for tx in range(0,240,8) for y in range(8) for x in range(8))


def edited(index,x,y):
    return y<136 if index==16 else x>=164 and (y>=124 if index==13 else y<36)


def add_title_art(build):
    approval=json.loads(APPROVAL.read_text());manifest=json.loads((PACKED/'manifest.json').read_text())
    require(approval['status']=='approved-for-insertion','Title art lacks approval')
    require(manifest['approval_sha256']==digest(APPROVAL.read_bytes()),'Repack approved title artwork')
    for path,sha in manifest['input_hashes'].items():require(digest((ROOT/path).read_bytes())==sha,'Title packing input changed: '+path)
    entries=[]
    require({e['index'] for e in manifest['entries']}==set(SOURCES),'Missing approved graphic')
    for entry in manifest['entries']:
        index=entry['index'];record=TABLE+index*20;source=SOURCES[index]
        require(build.original[record:record+20]==bytes.fromhex(RECORDS[index]),'Native background descriptor changed')
        require(digest(build.original[source:source+38912])==entry['original_resource_sha256'],'Original artwork changed')
        payload=(PACKED/f'{index}.bin').read_bytes()
        require(len(payload)==38912 and digest(payload)==entry['packed_sha256'],'Packed artwork changed')
        at=build.allocate(f'title-background-{index}',payload,OWNER)
        build.patch(f'title-background-pointer-{index}',record,struct.pack('<I',0x08000000+source),struct.pack('<I',0x08000000+at),OWNER)
        entries.append({**entry,'rom_offset':at,'record_offset':record,'original_resource_offset':source})
    return {'approval_sha256':digest(APPROVAL.read_bytes()),'manifest_sha256':digest((PACKED/'manifest.json').read_bytes()),
            'generator_sha256':digest((ROOT/'tools/title_art.py').read_bytes()),'entries':entries,'english_graphic_count':6,
            'scope':'Six private 8bpp palette/tile resources; six descriptor-pointer patches. Original source resources, instructions, all other descriptor fields, RAM/save layout and menu UI palette remain unchanged. Original footer and background pixels outside the corner rectangles are exact at every native palette setting.'}
