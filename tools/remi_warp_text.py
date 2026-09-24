"""Private dungeon names for Remi's selector and destination sentence only."""
import json,struct
from tools.rom import ROOT,digest,require
from tools.extract_shared_text import extract,START,END
from tools.compact_font import encode,measure

CATALOG=ROOT/'translations/remi-warp-names-review.json'
DUNGEONS={0,1,2,3,4,5,6,8,9,10}


def add_warp_names(build):
    catalog=json.loads(CATALOG.read_text());require(catalog['base_rom_sha256']==digest(build.original),'Warp name base differs')
    require(len(catalog['entries'])==10 and {r['dungeon_id'] for r in catalog['entries']}==DUNGEONS,'Warp name set differs')
    sources=extract()['entries'];table=bytearray(build.original[START:END]);rows=[]
    for row in catalog['entries']:
        index=row['table_index'];require(index==0x174+row['dungeon_id'],'Warp name index differs')
        require(row['source']==sources[index]['source'] and row['status']=='reviewed' and row['review'],'Warp source/review differs')
        payload=encode(row['english']);width=measure(row['english'])
        require(width<=122 and len(payload)<=57,'Warp name exceeds menu/argument reserve')
        offset=build.allocate(row['id'],payload,'remi-warp-names');struct.pack_into('<I',table,index*4,offset+0x08000000)
        rows.append(row|{'offset':offset,'encoded_hex':payload.hex(),'layout':{'pages':[[row['english']]],'line_widths':[[width]],
            'native_width':128,'initial_x':6,'text_budget':122,'direct_rom_stream':True}})
    offset=build.allocate('remi-private-dungeon-name-table',table,'remi-warp-names')
    for name,literal in (('remi-destination-name-table',0x1EFB8),('remi-warp-selector-name-table',0x1F234)):
        build.patch(name,literal,struct.pack('<I',START+0x08000000),struct.pack('<I',offset+0x08000000),'remi-warp-names')
    return {'entries':rows,'table_offset':offset,'catalog_sha256':digest(CATALOG.read_bytes()),'scope':catalog['scope']}
