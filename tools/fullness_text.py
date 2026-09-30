"""Three owned native maximum-fullness decimal formatters."""
import json,struct
from tools.rom import ROOT,digest,require
from tools.compact_font import encode,measure
from tools.extract_shared_text import START,END,extract
CATALOG=ROOT/'translations/fullness-review.json'
LITERALS=(0x331F8,0x33994,0x33A10)


def add_fullness(build):
    catalog=json.loads(CATALOG.read_text());source=next(r['source'] for r in extract()['entries'] if r['table_offset']==0xD0)
    require(catalog['base_rom_sha256']==digest(build.original) and len(catalog['entries'])==1,'Fullness source cohort differs')
    row=catalog['entries'][0];text=row['english'];plain=text.replace('{amount}','')
    require(row['source']==source and row['status']=='reviewed' and text.count('{amount}')==1 and not any(c in plain for c in '{}%\n\r'),'Fullness source/review/fields differ')
    payload=b'%d'.join(encode(p)[:-1] for p in text.split('{amount}'))+b'\0';width=measure(plain)+66;maximum=len(payload)+9
    require(width<=216 and maximum<=256 and bytes.fromhex(source['raw_hex']).count(b'%d')==1,'Fullness format bounds differ')
    at=build.allocate(row['id'],payload,'fullness-text');table=bytearray(build.original[START:END]);struct.pack_into('<I',table,0xD0,at+0x08000000)
    table_at=build.allocate('fullness-private-table',bytes(table),'fullness-text')
    for site in LITERALS:build.patch(f'fullness-table-{site:x}',site,struct.pack('<I',START+0x08000000),struct.pack('<I',table_at+0x08000000),'fullness-text')
    return {'entries':[row|{'offset':at,'encoded_hex':payload.hex(),'maximum_bytes':maximum,'maximum_width':width,'capacity':256}], 'table_offset':table_at,'literals':list(LITERALS),'catalog_sha256':digest(CATALOG.read_bytes()),'scope':catalog['scope']}
