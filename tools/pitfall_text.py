"""Private direct notices for the native pitfall trap."""
import json,struct
from tools.rom import ROOT,digest,require
from tools.extract_shared_text import extract,START,END
from tools.compact_font import encode,measure

CATALOG=ROOT/'translations/pitfall-review.json'
SLOTS={0x334,0x328,0x338}
LITERALS={0x28434:0,0x5468:0x338}


def add_pitfall(build):
    catalog=json.loads(CATALOG.read_text());sources={r['table_offset']:r['source'] for r in extract()['entries']}
    require(catalog['base_rom_sha256']==digest(build.original),'Pitfall base differs')
    require(len(catalog['entries'])==3 and {r['table_offset'] for r in catalog['entries']}==SLOTS,'Pitfall selection differs')
    table=bytearray(build.original[START:END]);rows=[]
    for row in catalog['entries']:
        source=sources[row['table_offset']];text=row['english']
        require(row['source']==source and row['status']=='reviewed' and row['review'],'Pitfall source/review differs')
        require(b'%' not in bytes.fromhex(source['raw_hex']) and not any(c in text for c in '{}%\n\r'),'Pitfall controls changed')
        payload=encode(text);require(measure(text)<=216 and len(payload)<=256,'Pitfall line/queue overflow')
        offset=build.allocate(row['id'],payload,'pitfall-text');struct.pack_into('<I',table,row['table_offset'],offset+0x08000000)
        rows.append(row|{'offset':offset,'encoded_hex':payload.hex(),'maximum_width':measure(text),'encoded_bytes':len(payload),'direct_rom_stream':True})
    offset=build.allocate('pitfall-private-table',bytes(table),'pitfall-text')
    for site,addend in LITERALS.items():build.patch(f'pitfall-literal-{site:x}',site,struct.pack('<I',START+0x08000000+addend),struct.pack('<I',offset+0x08000000+addend),'pitfall-text')
    return {'entries':rows,'table_offset':offset,'literal_offsets':list(LITERALS),'catalog_sha256':digest(CATALOG.read_bytes()),'scope':catalog['scope']}
