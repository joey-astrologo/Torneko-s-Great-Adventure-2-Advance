"""Owned HP-recovery and warp formatters with their original256-byte outputs."""
import json,re,struct
from tools.compact_font import encode,measure
from tools.extract_shared_text import START,END,extract
from tools.inventory_action_text import CONTROL
from tools.rom import ROOT,digest,require
CATALOG=ROOT/'translations/recovery-review.json'
LITERALS=(0x13E30,0x13EB0,0x40E30,0x122EC)
SLOTS={0x120,0x124,0x210}


def add_recovery(build):
    catalog=json.loads(CATALOG.read_text());sources={r['table_offset']:r['source'] for r in extract()['entries']}
    require(catalog['base_rom_sha256']==digest(build.original) and {r['table_offset'] for r in catalog['entries']}==SLOTS,'Recovery source cohort differs')
    entries=[];table=bytearray(build.original[START:END])
    for row in catalog['entries']:
        require(row['status']=='reviewed' and row['source']==sources[row['table_offset']],'Recovery source/review differs')
        text=row['english'];fields=re.findall(r'\{(actor|amount)\}',text)
        require(fields=={0x120:['actor','amount'],0x124:['amount'],0x210:['actor']}[row['table_offset']],'Recovery fields differ')
        plain=re.sub(r'\{(?:actor|amount|fit)\}','',text)
        require(not any(c in plain for c in '{}%\r\n'),'Unsupported recovery controls')
        payload=b''.join(b'%s' if p=='{actor}' else b'%d' if p=='{amount}' else CONTROL if p=='{fit}' else encode(p)[:-1] for p in re.split(r'(\{actor\}|\{amount\}|\{fit\})',text))+b'\0'
        require(re.findall(b'%[sd]',payload)==re.findall(b'%[sd]',bytes.fromhex(row['source']['raw_hex'])),'Recovery native argument order differs')
        widths=[measure(re.sub(r'\{(?:actor|amount)\}','',part))+186*part.count('{actor}')+66*part.count('{amount}') for part in text.split('{fit}')]
        maximum=len(payload)+61*fields.count('actor')+9*fields.count('amount')
        require(max(widths)<=216 and maximum<=256,'Recovery exceeds native budgets')
        address=build.allocate(row['id'],payload,'recovery-text');struct.pack_into('<I',table,row['table_offset'],address+0x08000000)
        entries.append(row|{'offset':address,'encoded_hex':payload.hex(),'fields':fields,'maximum_line_widths':widths,'maximum_bytes':maximum,'capacity':256,'actor_capacity':64})
    offset=build.allocate('recovery-private-table',bytes(table),'recovery-text')
    for site in LITERALS:build.patch(f'recovery-table-{site:x}',site,struct.pack('<I',START+0x08000000),struct.pack('<I',offset+0x08000000),'recovery-text')
    return {'entries':entries,'table_offset':offset,'consumer_literals':list(LITERALS),'catalog_sha256':digest(CATALOG.read_bytes()),'scope':catalog['scope']}
