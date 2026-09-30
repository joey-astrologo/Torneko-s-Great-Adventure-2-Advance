"""Owned battle totals, damage absorption and Cop Out announcement readers."""
import json,re,struct
from tools.compact_font import encode,measure
from tools.extract_shared_text import START,END,extract
from tools.inventory_action_text import CONTROL
from tools.rom import ROOT,digest,require
CATALOG=ROOT/'translations/battle-results-review.json'
LITERALS={0xC95C:{0x7D0},0xBEBC:{0x898},0x33DCC:{0x954,0x958,0x82C,0x830},0x417DC:{0x954,0x958,0x82C,0x830}}


def add_battle_results(build):
    catalog=json.loads(CATALOG.read_text());sources={r['table_offset']:r['source'] for r in extract()['entries']}
    require(catalog['base_rom_sha256']==digest(build.original) and {r['table_offset'] for r in catalog['entries']}==set.union(*LITERALS.values()),'Battle result source cohort differs')
    table=bytearray(build.original[START:END]);rows=[]
    for row in catalog['entries']:
        text=row['english'];slot=row['table_offset'];tokens=re.findall(r'\{([^}]+)\}',text);fields=[t for t in tokens if t not in ('player','fit')]
        require(row['source']==sources[slot] and row['status']=='reviewed' and fields==row['fields'] and set(tokens)<={'actor','amount','player','fit'},'Battle result source/review/fields differ')
        payload=b''.join({'{actor}':b'%s','{amount}':b'%d','{player}':b'\x7e','{fit}':CONTROL}.get(p,encode(p)[:-1]) for p in re.split(r'(\{[^}]+\})',text))+b'\0'
        require(re.findall(b'%[sd]',payload)==re.findall(b'%[sd]',bytes.fromhex(row['source']['raw_hex'])),'Battle result argument types/order differ')
        widths=[measure(re.sub(r'\{[^}]+\}','',p))+186*p.count('{actor}')+98*p.count('{player}')+66*p.count('{amount}') for p in text.split('{fit}')]
        maximum=len(payload)+sum(61 if t=='actor' else 9 for t in fields)
        require(max(widths)<=216 and maximum<=256 and text.count('{fit}')<=1,'Battle result native bounds exceeded')
        at=build.allocate(row['id'],payload,'battle-result-text');struct.pack_into('<I',table,slot,at+0x08000000)
        rows.append(row|{'offset':at,'encoded_hex':payload.hex(),'maximum_bytes':maximum,'maximum_segment_widths':widths,'capacity':256})
    at=build.allocate('battle-results-private-table',bytes(table),'battle-result-text')
    for site in LITERALS:build.patch(f'battle-results-table-{site:x}',site,struct.pack('<I',START+0x08000000),struct.pack('<I',at+0x08000000),'battle-result-text')
    return {'entries':rows,'table_offset':at,'catalog_sha256':digest(CATALOG.read_bytes()),'scope':catalog['scope']}
