"""Private Throw consumer text with its native 256-byte output unchanged."""
import json
import re
import struct
from tools.compact_font import encode, measure
from tools.extract_shared_text import START, END, extract
from tools.inventory_action_text import CONTROL
from tools.rom import ROOT, digest, require

CATALOG=ROOT/'translations/projectile-review.json'
OWNERS={0x25A58:0,0x25A90:0,0x25B10:0,0x260E0:0,0x263F0:0,0x25FEC:0x1D4}
SLOTS={0x80,0x1C8,0x1D4,0x1EC,0x2D0}


def add_projectiles(build):
    catalog=json.loads(CATALOG.read_text());sources={r['table_offset']:r['source'] for r in extract()['entries']}
    require(catalog['base_rom_sha256']==digest(build.original) and {r['table_offset'] for r in catalog['entries']}==SLOTS,'Projectile review cohort differs')
    table=bytearray(build.original[START:END]);entries=[]
    for row in catalog['entries']:
        require(row['status']=='reviewed' and row['source']==sources[row['table_offset']],'Projectile source/review differs')
        text=row['english'];fields=re.findall(r'\{(item|actor)\}',text)
        require(fields==(['item','actor'] if row['table_offset']==0x1C8 else ['item']) and text.count('{fit}')==1,'Projectile field/break ownership differs')
        plain=re.sub(r'\{(?:item|actor|fit)\}','',text)
        require(not any(c in plain for c in '{}%\r\n'),'Unsupported projectile controls')
        payload=b''.join(b'%s' if p in ('{item}','{actor}') else CONTROL if p=='{fit}' else encode(p)[:-1] for p in re.split(r'(\{item\}|\{actor\}|\{fit\})',text))+b'\0'
        require(re.findall(b'%[sd]',bytes.fromhex(row['source']['raw_hex']))==re.findall(b'%[sd]',payload),'Projectile native arguments changed')
        widths=[measure(re.sub(r'\{(?:item|actor)\}','',part))+162*part.count('{item}')+186*part.count('{actor}') for part in text.split('{fit}')]
        maximum=len(payload)+61*len(fields)
        require(max(widths)<=216 and maximum<=256,'Projectile text exceeds original buffer/lines')
        offset=build.allocate(row['id'],payload,'projectile-text');struct.pack_into('<I',table,row['table_offset'],offset+0x08000000)
        entries.append(row|{'offset':offset,'encoded_hex':payload.hex(),'field_roles':fields,'maximum_line_widths':widths,'maximum_bytes':maximum,'capacity':256,'item_capacity':64,'actor_capacity':64,'native_join_limit':215})
    offset=build.allocate('projectile-private-table',bytes(table),'projectile-text')
    for site,relative in OWNERS.items():
        build.patch(f'projectile-consumer-{site:x}',site,struct.pack('<I',START+relative+0x08000000),struct.pack('<I',offset+relative+0x08000000),'projectile-text')
    return {'entries':entries,'table_offset':offset,'consumer_literals':OWNERS,'catalog_sha256':digest(CATALOG.read_bytes()),'scope':catalog['scope']}
