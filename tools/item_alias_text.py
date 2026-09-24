"""Private unidentified-name table; original assignment and sentinel stay intact."""
import json,struct
from tools.rom import ROOT,digest,require
from tools.compact_font import encode,measure
from tools.extract_item_aliases import extract,START,END

CATALOG=ROOT/'translations/item-aliases-review.json'

def add_aliases(build):
    catalog=json.loads(CATALOG.read_text());source=extract()
    require(catalog['base_rom_sha256']==digest(build.original),'Alias base differs')
    require([r['id'] for r in catalog['entries']]==list(range(154)),'Alias selection incomplete or includes sentinel')
    require(len({r['name'].casefold() for r in catalog['entries']})==154,'Alias display names collide')
    data=bytearray(build.original[START:END]);rows=[]
    for row in catalog['entries']:
        require(row['source']==source['entries'][row['id']] and row['status']=='reviewed'
                and row['bilingual_review'],'Alias source/language review differs')
        payload=encode(row['name']);require(measure(row['name'])<=80 and len(payload)<=31,'Alias exceeds base-name budget')
        offset=build.allocate('item-appearance-'+str(row['id']),payload,'item-appearance-prototype')
        struct.pack_into('<I',data,row['id']*24,offset+0x08000000)
        rows.append(row|{'offset':offset,'encoded_hex':payload.hex()})
    restored=bytearray(data)
    for row in rows:restored[row['id']*24:row['id']*24+4]=build.original[START+row['id']*24:START+row['id']*24+4]
    require(restored==build.original[START:END] and data[154*24:]==build.original[START+154*24:END],
            'Alias metadata or sentinel changed')
    offset=build.allocate('item-appearance-private-table',bytes(data),'item-appearance-prototype')
    for site in (0xF628,0xF64C,0xF684):
        build.patch('item-appearance-consumer-'+hex(site),site,struct.pack('<I',START+0x08000000),
                    struct.pack('<I',offset+0x08000000),'item-appearance-prototype')
    require(build.data[START:END]==build.original[START:END]
            and build.data[0x9FD8:0x9FDC]==build.original[0x9FD8:0x9FDC],'Original alias assignment table changed')
    return {'entries':rows,'table_offset':offset,'record_count':155,'translated_names':154,
            'review_sha256':digest(CATALOG.read_bytes()),'original_assignment_and_sentinel_preserved':True}
