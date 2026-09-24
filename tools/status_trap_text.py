"""Private direct notices for the sleep, illusion-gas and confusion trap handlers."""
import json,struct
from tools.rom import ROOT,digest,require
from tools.extract_shared_text import extract,START,END
from tools.compact_font import encode,measure

CATALOG=ROOT/'translations/status-traps-review.json'
SLOTS={0x2EC,0x2F4,0x308,0x310,0x314}
LITERALS=(0x27A48,0x27AC4,0x27B38,0x27B80)


def add_status_traps(build):
    catalog=json.loads(CATALOG.read_text());sources={r['table_offset']:r['source'] for r in extract()['entries']}
    require(catalog['base_rom_sha256']==digest(build.original),'Status trap base differs')
    require(len(catalog['entries'])==5 and {r['table_offset'] for r in catalog['entries']}==SLOTS,'Status trap selection differs')
    table=bytearray(build.original[START:END]);rows=[]
    for row in catalog['entries']:
        source=sources[row['table_offset']];text=row['english']
        require(row['source']==source and row['status']=='reviewed' and row['review'],'Status trap source/review differs')
        require(b'%' not in bytes.fromhex(source['raw_hex']) and not any(c in text for c in '{}%\n\r'),'Status trap controls changed')
        payload=encode(text);require(measure(text)<=216 and len(payload)<=256,'Status trap line/queue overflow')
        offset=build.allocate(row['id'],payload,'status-trap-text');struct.pack_into('<I',table,row['table_offset'],offset+0x08000000)
        rows.append(row|{'offset':offset,'encoded_hex':payload.hex(),'maximum_width':measure(text),'encoded_bytes':len(payload),'direct_rom_stream':True})
    offset=build.allocate('status-traps-private-table',bytes(table),'status-trap-text')
    for site in LITERALS:build.patch(f'status-trap-literal-{site:x}',site,struct.pack('<I',START+0x08000000),struct.pack('<I',offset+0x08000000),'status-trap-text')
    return {'entries':rows,'table_offset':offset,'literal_offsets':list(LITERALS),'catalog_sha256':digest(CATALOG.read_bytes()),'scope':catalog['scope']}
