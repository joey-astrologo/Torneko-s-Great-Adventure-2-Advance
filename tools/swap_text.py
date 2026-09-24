"""Owned Floor/Swap messages with two bounded item arguments."""
import json,re,struct
from tools.rom import ROOT,digest,require
from tools.extract_shared_text import START,END,extract
from tools.compact_font import encode,measure
from tools.inventory_action_text import CONTROL

CATALOG=ROOT/'translations/swap-review.json'
OWNERS={0x25664:(0x8F0,),0x256C0:(0x154,),0x256F8:(0x1EC,),0x25728:(0x80,),0x257EC:(0xC4,)}

def add_swap(build):
    catalog=json.loads(CATALOG.read_text());allowed={n for ns in OWNERS.values() for n in ns}
    require(catalog['base_rom_sha256']==digest(build.original),'Swap base differs')
    require(len(catalog['entries'])==len(allowed) and {r['table_offset'] for r in catalog['entries']}==allowed,'Unowned swap selection')
    sources={r['table_offset']:r['source'] for r in extract()['entries']};table=bytearray(build.original[START:END]);rows=[]
    for row in catalog['entries']:
        source=sources[row['table_offset']];text=row['english']
        require(row['status']=='reviewed' and row['source']==source,'Swap source/review differs')
        plain=text.replace('{floor}','').replace('{item}','').replace('{fit}','')
        require(not any(c in plain for c in '{}%\n\r') and text.count('{fit}')<=1,'Unowned swap format')
        fields=re.findall(r'\{(?:floor|item)\}',text)
        require(fields==(['{floor}','{item}'] if row['table_offset']==0xC4 else
                         ['{item}'] if row['table_offset'] in (0x80,0x1EC) else []),'Swap argument order/roles changed')
        payload=b''.join(b'%s' if part in ('{floor}','{item}') else CONTROL if part=='{fit}' else encode(part)[:-1]
                         for part in re.split(r'(\{floor\}|\{item\}|\{fit\})',text))+b'\0'
        require(re.findall(b'%[sd]',bytes.fromhex(source['raw_hex']))==re.findall(b'%[sd]',payload),'Swap source fields differ')
        widths=[measure(part.replace('{floor}','').replace('{item}',''))+162*(part.count('{floor}')+part.count('{item}'))
                for part in text.split('{fit}')]
        maximum=len(payload)+61*len(fields)
        require(max(widths)<=216 and maximum<=192,'Swap width/native buffer budget exceeded')
        offset=build.allocate(row['id'],payload,'swap-text');struct.pack_into('<I',table,row['table_offset'],offset+0x08000000)
        rows.append(row|{'offset':offset,'encoded_hex':payload.hex(),'maximum_line_widths':widths,
                         'maximum_bytes':maximum,'capacity':192,'item_capacity':64,'field_roles':fields})
    offset=build.allocate('swap-text-table',bytes(table),'swap-text')
    for site in OWNERS:
        build.patch(f'swap-consumer-{site:x}',site,struct.pack('<I',START+0x08000000),struct.pack('<I',offset+0x08000000),'swap-text')
    return {'entries':rows,'table_offset':offset,'consumer_literals':list(OWNERS),
            'catalog_sha256':digest(CATALOG.read_bytes()),'scope':catalog['scope']}
