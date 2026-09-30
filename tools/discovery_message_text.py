"""Private item identification, monster revelation and transformation messages."""
import json,re,struct
from tools.compact_font import encode,measure
from tools.extract_shared_text import START,END,extract
from tools.inventory_action_text import CONTROL
from tools.rom import ROOT,digest,require
CATALOG=ROOT/'translations/discovery-messages-review.json'
LITERALS={0x2C368:{0x35C},0x2A01C:{0x7E0},0x399F4:{0x230},0x32ECC:{0x74},0x33BE4:{0x74},0x40C24:{0x74},0x33B7C:{0x1AC},0x2D98C:{0x9C8},0x2D9B8:{0x95C}}


def add_discovery_messages(build):
    catalog=json.loads(CATALOG.read_text());sources={r['table_offset']:r['source'] for r in extract()['entries']}
    require(catalog['base_rom_sha256']==digest(build.original) and {r['table_offset'] for r in catalog['entries']}==set.union(*LITERALS.values()),'Discovery source cohort differs')
    rows=[];table=bytearray(build.original[START:END])
    for row in catalog['entries']:
        text=row['english'];fields=row['fields'];tokens=re.findall(r'\{([^}]+)\}',text)
        require(row['source']==sources[row['table_offset']] and row['status']=='reviewed' and [p for p in tokens if p!='fit']==fields and text.count('{fit}')<=2,'Discovery review/fields differ')
        payload=b''.join(CONTROL if p=='{fit}' else b'%s' if p[1:-1] in fields and p.startswith('{') else encode(p)[:-1] for p in re.split(r'(\{[^}]+\})',text))+b'\0'
        maximum=len(payload)+61*len(fields)
        widths=[]
        for part in text.split('{fit}'):
            width=measure(re.sub(r'\{[^}]+\}','',part))
            for field in fields:width+=(186 if 'actor' in field else 162)*part.count('{'+field+'}')
            widths.append(width)
        require(bytes.fromhex(row['source']['raw_hex']).count(b'%s')==len(fields) and maximum<=256 and max(widths)<=216,'Discovery field/byte/pixel budget exceeded')
        at=build.allocate(row['id'],payload,'discovery-message-text');struct.pack_into('<I',table,row['table_offset'],at+0x08000000);rows.append(row|{'offset':at,'encoded_hex':payload.hex(),'maximum_bytes':maximum,'maximum_segment_widths':widths,'capacity':256})
    at=build.allocate('discovery-messages-private-table',bytes(table),'discovery-message-text')
    for site in LITERALS:build.patch(f'discovery-message-consumer-{site:x}',site,struct.pack('<I',START+0x08000000),struct.pack('<I',at+0x08000000),'discovery-message-text')
    return {'entries':rows,'table_offset':at,'catalog_sha256':digest(CATALOG.read_bytes()),'scope':catalog['scope']}
