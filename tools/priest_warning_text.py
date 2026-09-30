"""Private immutable priest expiry notice; preserve the original actor loop."""
import json,struct
from tools.rom import ROOT,digest,require
from tools.compact_font import encode,measure
from tools.extract_shared_text import START,END,extract

CATALOG=ROOT/'translations/priest-warning-review.json'

def add_priest_warning(build):
    c=json.loads(CATALOG.read_text());src=next(r['source'] for r in extract()['entries'] if r['table_offset']==0x4E0)
    require(c['base_rom_sha256']==digest(build.original) and len(c['entries'])==1,'Priest warning base/cohort differs')
    row=c['entries'][0];text=row['english']
    require(row['table_offset']==0x4E0 and row['source']==src and row['status']=='reviewed','Priest warning source/review differs')
    require(not any(ch in text for ch in '{}%\r\n') and measure(text)<=216,'Priest warning exceeds one queue line or contains controls')
    payload=encode(text);at=build.allocate(row['id'],payload,'priest-warning')
    table=bytearray(build.original[START:END]);struct.pack_into('<I',table,0x4E0,at+0x08000000)
    t=build.allocate('priest-warning-table',bytes(table),'priest-warning')
    build.patch('priest-warning-reader',0x14144,struct.pack('<I',START+0x4E0+0x08000000),struct.pack('<I',t+0x4E0+0x08000000),'priest-warning')
    return {'entries':[row|{'offset':at,'encoded_hex':payload.hex(),'maximum_bytes':len(payload),'maximum_segment_widths':[measure(text)],'fields':[],'capacity':'immutable-ROM'}],'table_offset':t,'catalog_sha256':digest(CATALOG.read_bytes()),'scope':c['scope']}
