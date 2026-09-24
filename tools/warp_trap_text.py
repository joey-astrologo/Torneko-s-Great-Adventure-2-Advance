"""Private table for the native warp-trap announcement and failed activation."""
import json,struct
from tools.rom import ROOT,digest,require
from tools.extract_shared_text import extract,START,END
from tools.compact_font import encode,measure

CATALOG=ROOT/'translations/warp-trap-review.json'
SLOTS={0x2F0,0x2EC}


def add_warp_trap(build):
    catalog=json.loads(CATALOG.read_text());sources={r['table_offset']:r['source'] for r in extract()['entries']}
    require(catalog['base_rom_sha256']==digest(build.original),'Warp trap base differs')
    require(len(catalog['entries'])==2 and {r['table_offset'] for r in catalog['entries']}==SLOTS,'Warp trap selection differs')
    table=bytearray(build.original[START:END]);rows=[]
    for row in catalog['entries']:
        source=sources[row['table_offset']];text=row['english']
        require(row['source']==source and row['status']=='reviewed' and row['review'],'Warp trap review/source differs')
        require(b'%' not in bytes.fromhex(source['raw_hex']) and not any(c in text for c in '{}%\n\r'),'Warp trap controls changed')
        payload=encode(text);width=measure(text);require(width<=216 and len(payload)<=256,'Warp trap warning exceeds native line/queue bounds')
        offset=build.allocate(row['id'],payload,'warp_trap-text');struct.pack_into('<I',table,row['table_offset'],offset+0x08000000)
        rows.append(row|{'offset':offset,'encoded_hex':payload.hex(),'maximum_width':width,'encoded_bytes':len(payload),'direct_rom_stream':True})
    offset=build.allocate('warp_trap-private-table',bytes(table),'warp_trap-text')
    build.patch('warp_trap-consumer-literal',0x276B8,struct.pack('<I',START+0x08000000),struct.pack('<I',offset+0x08000000),'warp_trap-text')
    return {'entries':rows,'table_offset':offset,'literal_offset':0x276B8,'catalog_sha256':digest(CATALOG.read_bytes()),'scope':catalog['scope']}
