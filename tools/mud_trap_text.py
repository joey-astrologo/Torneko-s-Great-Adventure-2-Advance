"""Private direct notices for the native mud trap."""
import json,struct
from tools.rom import ROOT,digest,require
from tools.extract_shared_text import extract,START,END
from tools.compact_font import encode,measure

CATALOG=ROOT/'translations/mud-trap-review.json'
SLOTS={0x2F4,0x2EC,0x320,0x324,0x328}
LITERALS=(0x27E04,0x27EA4,0x27EC0)


def add_mud_trap(build):
    catalog=json.loads(CATALOG.read_text());sources={r['table_offset']:r['source'] for r in extract()['entries']}
    require(catalog['base_rom_sha256']==digest(build.original),'Mud trap base differs')
    require(len(catalog['entries'])==5 and {r['table_offset'] for r in catalog['entries']}==SLOTS,'Mud trap selection differs')
    table=bytearray(build.original[START:END]);rows=[]
    for row in catalog['entries']:
        source=sources[row['table_offset']];text=row['english']
        require(row['source']==source and row['status']=='reviewed' and row['review'],'Mud trap source/review differs')
        require(b'%' not in bytes.fromhex(source['raw_hex']) and not any(c in text for c in '{}%\n\r'),'Mud trap controls changed')
        payload=encode(text);require(measure(text)<=216 and len(payload)<=256,'Mud trap line/queue overflow')
        offset=build.allocate(row['id'],payload,'mud-trap-text');struct.pack_into('<I',table,row['table_offset'],offset+0x08000000)
        rows.append(row|{'offset':offset,'encoded_hex':payload.hex(),'maximum_width':measure(text),'encoded_bytes':len(payload),'direct_rom_stream':True})
    offset=build.allocate('mud-trap-private-table',bytes(table),'mud-trap-text')
    for site in LITERALS:build.patch(f'mud-trap-literal-{site:x}',site,struct.pack('<I',START+0x08000000),struct.pack('<I',offset+0x08000000),'mud-trap-text')
    return {'entries':rows,'table_offset':offset,'literal_offsets':list(LITERALS),'catalog_sha256':digest(CATALOG.read_bytes()),'scope':catalog['scope']}
