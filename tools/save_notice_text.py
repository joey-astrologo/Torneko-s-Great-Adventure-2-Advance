"""Private immutable messages for the two audited save-error modal readers."""
import json,struct
from tools.rom import ROOT,digest,require
from tools.compact_font import encode,measure
from tools.extract_shared_text import START,END,extract

CATALOG=ROOT/'translations/save-notices-review.json'
LITERALS=(0x14E20,0x15058)

def add_save_notices(build):
    catalog=json.loads(CATALOG.read_text())
    require(catalog['base_rom_sha256']==digest(build.original),'Save notice base differs')
    sources={r['table_offset']:r['source'] for r in extract()['entries']}
    require(len(catalog['entries'])==2 and {r['table_offset'] for r in catalog['entries']}=={0x5C4,0x598},'Save notice cohort differs')
    table=bytearray(build.original[START:END]);rows=[]
    for row in catalog['entries']:
        require(row['status']=='reviewed' and row['source']==sources[row['table_offset']],'Save notice source/review differs')
        text=row['english'];lines=text.split('\n');widths=[measure(l) for l in lines]
        require(not any(c in text for c in '{}%\r') and max(widths)<=216 and len(lines)==(4 if row['table_offset']==0x5C4 else 2),'Save notice width/rows/controls differ')
        payload=b'\r'.join(encode(l)[:-1] for l in lines)+b'\0'
        at=build.allocate(row['id'],payload,'save-notice-text')
        struct.pack_into('<I',table,row['table_offset'],at+0x08000000)
        rows.append(row|{'offset':at,'encoded_hex':payload.hex(),'maximum_line_widths':widths,'capacity':'immutable-ROM'})
    at=build.allocate('save-notices-private-table',bytes(table),'save-notice-text')
    for site in LITERALS:
        build.patch(f'save-notice-table-{site:x}',site,struct.pack('<I',START+0x08000000),struct.pack('<I',at+0x08000000),'save-notice-text')
    return {'entries':rows,'table_offset':at,'catalog_sha256':digest(CATALOG.read_bytes()),'scope':catalog['scope']}
