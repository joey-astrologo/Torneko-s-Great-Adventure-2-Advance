"""Private staff-use draining and player-pulling messages."""
import json,re,struct
from tools.compact_font import encode,measure
from tools.extract_shared_text import START,END,extract
from tools.inventory_action_text import CONTROL
from tools.rom import ROOT,digest,require
CATALOG=ROOT/'translations/monster-interactions-review.json'
LITERALS={0x2FAB8:{0x478},0x31924:{0x470}}

def add_monster_interactions(build):
    catalog=json.loads(CATALOG.read_text());sources={r['table_offset']:r['source'] for r in extract()['entries']}
    require(catalog['base_rom_sha256']==digest(build.original) and {r['table_offset'] for r in catalog['entries']}==set.union(*LITERALS.values()),'Monster interaction cohort differs')
    rows=[];table=bytearray(build.original[START:END]);widths={'actor':186,'player':98,'item':162};sizes={'actor':63,'player':14,'item':63}
    for row in catalog['entries']:
        text=row['english'];fields=row['fields'];tokens=re.findall(r'\{([^}]+)\}',text)
        require(row['source']==sources[row['table_offset']] and row['status']=='reviewed' and [p for p in tokens if p!='fit']==fields and text.count('{fit}')<=2,'Monster interaction source/review/fields differ')
        payload=b''.join(CONTROL if p=='{fit}' else b'%s' if p.startswith('{') else encode(p)[:-1] for p in re.split(r'(\{[^}]+\})',text))+b'\0'
        maximum=len(payload)+sum(sizes[f]-2 for f in fields)
        segments=[measure(re.sub(r'\{[^}]+\}','',p))+sum(widths[f]*p.count('{'+f+'}') for f in fields) for p in text.split('{fit}')]
        require(re.findall(b'%[sd]',bytes.fromhex(row['source']['raw_hex']))==[b'%s']*len(fields) and maximum<=256 and max(segments)<=216,'Monster interaction byte/pixel bounds exceeded')
        at=build.allocate(row['id'],payload,'monster-interaction-text');struct.pack_into('<I',table,row['table_offset'],at+0x08000000);rows.append(row|{'offset':at,'encoded_hex':payload.hex(),'maximum_bytes':maximum,'maximum_segment_widths':segments,'capacity':256})
    at=build.allocate('monster-interactions-private-table',bytes(table),'monster-interaction-text')
    for site in LITERALS:build.patch(f'monster-interaction-consumer-{site:x}',site,struct.pack('<I',START+0x08000000),struct.pack('<I',at+0x08000000),'monster-interaction-text')
    # Complete 3181C..3191C listing: the only local is the output at SP+0.
    # No incoming stack arguments or offset-dependent locals occur.
    build.patch('monster-pull-frame',0x31824,bytes.fromhex('90b0'),bytes.fromhex('c0b0'),'monster-interaction-text')
    build.patch('monster-pull-unframe',0x3190E,bytes.fromhex('10b0'),bytes.fromhex('40b0'),'monster-interaction-text')
    return {'entries':rows,'table_offset':at,'catalog_sha256':digest(CATALOG.read_bytes()),'scope':catalog['scope']}
