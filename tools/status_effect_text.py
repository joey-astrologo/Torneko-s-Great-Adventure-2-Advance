"""Owned actor sleep/confusion, disguise, HP, level and strength messages."""
import json,re,struct
from tools.compact_font import encode,measure
from tools.extract_shared_text import START,END,extract
from tools.inventory_action_text import CONTROL
from tools.rom import ROOT,digest,require
CATALOG=ROOT/'translations/status-effects-review.json'
LITERALS={0x39080:{0x1DC},0x390B0:{0x11C},0x3988C:{0x1DC},0x398BC:{0x11C},0x3C730:{0x1DC},0x3C768:{0x11C},0x39120:{0x1E8},0x398F4:{0x1E8},0x39784:{0x22C},0x394EC:{0x7F4},0x3957C:{0xEC},0x395AC:{0xA20},0x39200:{0x62C,0x200}}


def add_status_effects(build):
    catalog=json.loads(CATALOG.read_text());sources={r['table_offset']:r['source'] for r in extract()['entries']}
    require(catalog['base_rom_sha256']==digest(build.original) and {r['table_offset'] for r in catalog['entries']}==set.union(*LITERALS.values()),'Status effect source cohort differs')
    table=bytearray(build.original[START:END]);rows=[]
    for row in catalog['entries']:
        text=row['english'];plain=text.replace('{actor}','').replace('{fit}','')
        require(row['source']==sources[row['table_offset']] and row['status']=='reviewed' and text.count('{actor}')==text.count('{fit}')==1 and not any(c in plain for c in '{}%\r\n'),'Status effect source/review/format differs')
        payload=b''.join(b'%s' if p=='{actor}' else CONTROL if p=='{fit}' else encode(p)[:-1] for p in re.split(r'(\{[^}]+\})',text))+b'\0';maximum=len(payload)+61
        widths=[measure(p.replace('{actor}',''))+186*p.count('{actor}') for p in text.split('{fit}')]
        require(max(widths)<=216 and maximum<=256 and bytes.fromhex(row['source']['raw_hex']).count(b'%s')==1,'Status effect bounds differ')
        at=build.allocate(row['id'],payload,'status-effect-text');struct.pack_into('<I',table,row['table_offset'],at+0x08000000)
        rows.append(row|{'offset':at,'encoded_hex':payload.hex(),'maximum_bytes':maximum,'maximum_segment_widths':widths,'capacity':256,'fields':['actor']})
    at=build.allocate('status-effects-private-table',bytes(table),'status-effect-text')
    for site in LITERALS:build.patch(f'status-effects-table-{site:x}',site,struct.pack('<I',START+0x08000000),struct.pack('<I',at+0x08000000),'status-effect-text')
    return {'entries':rows,'table_offset':at,'literals':{str(k):sorted(v) for k,v in LITERALS.items()},'catalog_sha256':digest(CATALOG.read_bytes()),'scope':catalog['scope']}
