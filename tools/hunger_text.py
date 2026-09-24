"""Private table for the five warnings selected by native fullness transitions."""
import json,struct
from tools.rom import ROOT,digest,require
from tools.extract_shared_text import extract,START,END
from tools.compact_font import encode,measure

CATALOG=ROOT/'translations/hunger-review.json'
SLOTS=set(range(0x23C,0x250,4))


def add_hunger(build):
    catalog=json.loads(CATALOG.read_text());sources={r['table_offset']:r['source'] for r in extract()['entries']}
    require(catalog['base_rom_sha256']==digest(build.original),'Hunger base differs')
    require(len(catalog['entries'])==5 and {r['table_offset'] for r in catalog['entries']}==SLOTS,'Hunger selection differs')
    table=bytearray(build.original[START:END]);rows=[]
    for row in catalog['entries']:
        source=sources[row['table_offset']];text=row['english']
        require(row['source']==source and row['status']=='reviewed' and row['review'],'Hunger review/source differs')
        require(b'%' not in bytes.fromhex(source['raw_hex']) and not any(c in text for c in '{}%\n\r'),'Hunger controls changed')
        payload=encode(text);width=measure(text);require(width<=216 and len(payload)<=256,'Hunger warning exceeds native line/queue bounds')
        offset=build.allocate(row['id'],payload,'hunger-text');struct.pack_into('<I',table,row['table_offset'],offset+0x08000000)
        rows.append(row|{'offset':offset,'encoded_hex':payload.hex(),'maximum_width':width,'encoded_bytes':len(payload),'direct_rom_stream':True})
    offset=build.allocate('hunger-private-table',bytes(table),'hunger-text')
    build.patch('hunger-consumer-literal',0x9148,struct.pack('<I',START+0x08000000),struct.pack('<I',offset+0x08000000),'hunger-text')
    return {'entries':rows,'table_offset':offset,'literal_offset':0x9148,'catalog_sha256':digest(CATALOG.read_bytes()),'scope':catalog['scope']}
