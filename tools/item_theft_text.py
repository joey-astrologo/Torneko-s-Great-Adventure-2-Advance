"""Owned item theft/waiting formats, retaining the original256-byte output."""
import json,re,struct
from tools.compact_font import encode,measure
from tools.extract_shared_text import START,END,extract
from tools.inventory_action_text import CONTROL
from tools.rom import ROOT,digest,require

CATALOG=ROOT/'translations/item-theft-review.json'
LITERALS=(0x2A824,0x2BEA4,0x2BED4,0x2C0EC,0x2C110,0x2C148)


def add_item_theft(build):
    catalog=json.loads(CATALOG.read_text());sources={r['table_offset']:r['source'] for r in extract()['entries']}
    arguments={0x2AC:['actor'],0x2B0:['actor','player','item'],0x2B8:['actor'],0x710:['actor','kind'],0x718:[]}
    bounds={'actor':(186,63),'player':(98,14),'item':(162,63),'kind':(measure('items'),len(encode('items'))-1)}
    require(catalog['base_rom_sha256']==digest(build.original) and {r['table_offset'] for r in catalog['entries']}==set(arguments),'Item theft source cohort differs')
    table=bytearray(build.original[START:END]);entries=[]
    for row in catalog['entries']:
        text=row['english'];slot=row['table_offset'];fields=re.findall(r'\{(?!fit\})([^}]+)\}',text)
        require(row['source']==sources[slot] and row['status']=='reviewed' and row['review'],'Item theft review/source differs')
        require(fields==arguments[slot] and text.count('{fit}')==(2 if slot==0x2B0 else int(bool(fields))),'Item theft fields/breaks differ')
        require(not any(c in re.sub(r'\{[^}]+\}','',text) for c in '{}%\r\n'),'Unsupported item theft controls')
        payload=b''.join(CONTROL if p=='{fit}' else b'%s' if p.startswith('{') else encode(p)[:-1] for p in re.split(r'(\{[^}]+\})',text))+b'\0'
        require(re.findall(b'%[sd]',payload)==re.findall(b'%[sd]',bytes.fromhex(row['source']['raw_hex'])),'Item theft native arguments differ')
        widths=[measure(re.sub(r'\{[^}]+\}','',p))+sum(p.count('{'+f+'}')*bounds[f][0] for f in fields) for p in text.split('{fit}')]
        maximum=len(payload)+sum(bounds[f][1]-2 for f in fields)
        require(max(widths)<=216 and maximum<=256,'Item theft exceeds original line/buffer budgets')
        offset=build.allocate(row['id'],payload,'item-theft')
        struct.pack_into('<I',table,slot,offset+0x08000000)
        entries.append(row|{'offset':offset,'encoded_hex':payload.hex(),'maximum_bytes':maximum,'maximum_line_widths':widths,'capacity':256,'fields':fields})
    offset=build.allocate('item-theft-private-table',bytes(table),'item-theft')
    for site in LITERALS:build.patch(f'item-theft-table-{site:x}',site,struct.pack('<I',START+0x08000000),struct.pack('<I',offset+0x08000000),'item-theft')
    return {'entries':entries,'table_offset':offset,'consumer_literals':list(LITERALS),'catalog_sha256':digest(CATALOG.read_bytes()),'scope':catalog['scope']}
