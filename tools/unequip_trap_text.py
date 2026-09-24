"""Private direct notices for the native equipment-removal trap."""
import json,struct
from tools.rom import ROOT,digest,require
from tools.extract_shared_text import extract,START,END
from tools.compact_font import encode,measure

CATALOG=ROOT/'translations/unequip-trap-review.json'
SLOTS={0x2F4,0x2EC,0x318,0x438}
LITERALS=(0x27BDC,0x27CA8,0x27CDC)


def add_unequip_trap(build):
    catalog=json.loads(CATALOG.read_text());sources={r['table_offset']:r['source'] for r in extract()['entries']}
    require(catalog['base_rom_sha256']==digest(build.original),'Unequip trap base differs')
    require(len(catalog['entries'])==4 and {r['table_offset'] for r in catalog['entries']}==SLOTS,'Unequip trap selection differs')
    table=bytearray(build.original[START:END]);rows=[]
    for row in catalog['entries']:
        source=sources[row['table_offset']];text=row['english']
        require(row['source']==source and row['status']=='reviewed' and row['review'],'Unequip trap source/review differs')
        require(b'%' not in bytes.fromhex(source['raw_hex']) and not any(c in text for c in '{}%\n\r'),'Unequip trap controls changed')
        payload=encode(text);require(measure(text)<=216 and len(payload)<=256,'Unequip trap line/queue overflow')
        offset=build.allocate(row['id'],payload,'unequip-trap-text');struct.pack_into('<I',table,row['table_offset'],offset+0x08000000)
        rows.append(row|{'offset':offset,'encoded_hex':payload.hex(),'maximum_width':measure(text),'encoded_bytes':len(payload),'direct_rom_stream':True})
    offset=build.allocate('unequip-trap-private-table',bytes(table),'unequip-trap-text')
    for site in LITERALS:build.patch(f'unequip-trap-literal-{site:x}',site,struct.pack('<I',START+0x08000000),struct.pack('<I',offset+0x08000000),'unequip-trap-text')
    return {'entries':rows,'table_offset':offset,'literal_offsets':list(LITERALS),'catalog_sha256':digest(CATALOG.read_bytes()),'scope':catalog['scope']}
