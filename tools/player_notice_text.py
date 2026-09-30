"""Owned direct player-substitution notices without caller-buffer expansion."""
import json,re,struct
from tools.compact_font import encode,measure
from tools.extract_shared_text import START,END,extract
from tools.inventory_action_text import CONTROL
from tools.rom import ROOT,digest,require
CATALOG=ROOT/'translations/player-notices-review.json'
LITERALS={0x2FA40:{0x47C},0x3CBD0:{0x9C0}}

def add_player_notices(build):
    catalog=json.loads(CATALOG.read_text());sources={r['table_offset']:r['source'] for r in extract()['entries']}
    require(catalog['base_rom_sha256']==digest(build.original) and {r['table_offset'] for r in catalog['entries']}==set.union(*LITERALS.values()),'Player notice cohort differs')
    rows=[];table=bytearray(build.original[START:END])
    for row in catalog['entries']:
        text=row['english'];plain=text.replace('{player}','').replace('{fit}','')
        require(row['source']==sources[row['table_offset']] and row['status']=='reviewed' and text.count('{player}')==1 and bytes.fromhex(row['source']['raw_hex']).count(b'\x7e')==1 and not any(c in plain for c in '{}%\r\n'),'Player notice source/control/review differs')
        payload=b''.join(b'\x7e' if p=='{player}' else CONTROL if p=='{fit}' else encode(p)[:-1] for p in re.split(r'(\{[^}]+\})',text))+b'\0'
        widths=[measure(p.replace('{player}',''))+98*p.count('{player}') for p in text.split('{fit}')]
        require(max(widths)<=216 and len(payload)<=256,'Player notice exceeds native bounds')
        at=build.allocate(row['id'],payload,'player-notice-text');struct.pack_into('<I',table,row['table_offset'],at+0x08000000);rows.append(row|{'offset':at,'encoded_hex':payload.hex(),'maximum_bytes':len(payload),'maximum_segment_widths':widths,'fields':[],'capacity':'direct-ROM'})
    at=build.allocate('player-notices-private-table',bytes(table),'player-notice-text')
    for site in LITERALS:build.patch(f'player-notice-reader-{site:x}',site,struct.pack('<I',START+0x08000000),struct.pack('<I',at+0x08000000),'player-notice-text')
    return {'entries':rows,'table_offset':at,'catalog_sha256':digest(CATALOG.read_bytes()),'scope':catalog['scope']}
