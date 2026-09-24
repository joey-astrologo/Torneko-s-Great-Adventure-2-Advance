"""Owned Equip/Remove/Drop reads, retaining the native 192-byte outputs."""
import json,re,struct
from tools.rom import ROOT,digest,require
from tools.extract_shared_text import START,END,extract
from tools.compact_font import encode,measure

CATALOG=ROOT/'translations/inventory-actions-review.json'
CONTROL=b'\x0e\x0aI'
OWNERS={0x2471C:(0x78,),0x24774:(0x7C,),0x247B8:(0x80,),0x24880:(0x88,0x84),
        0x24994:(0x80,),0x249D8:(0x94,),0x24EB8:(0x80,),0x24EE8:(0xA8,),
        0x24F60:(0xAC,),0x24F80:(0xA14,)}

def add_actions(build):
    return add_reviewed_actions(build,CATALOG,OWNERS,'inventory-actions')

def add_reviewed_actions(build,catalog_path,owners,owner):
    catalog=json.loads(catalog_path.read_text());allowed={n for ns in owners.values() for n in ns}
    require(catalog['base_rom_sha256']==digest(build.original),'Inventory-action base differs')
    require(len(catalog['entries'])==len(allowed) and {r['table_offset'] for r in catalog['entries']}==allowed,
            'Unowned inventory-action selection')
    sources={r['table_offset']:r['source'] for r in extract()['entries']}
    table=bytearray(build.original[START:END]);entries=[]
    for row in catalog['entries']:
        text=row['english'];source=sources[row['table_offset']]
        require(row['source']==source and row['status']=='reviewed','Inventory action source/review differs')
        plain=text.replace('{item}','').replace('{fit}','')
        require(not any(c in plain for c in '{}%\r') and text.count('{fit}')<=1
                and not ('{fit}' in text and '\n' in text),'Unowned inventory-action format')
        pieces=re.split(r'(\{item\}|\{fit\}|\n)',text)
        payload=b''.join(b'%s' if p=='{item}' else CONTROL if p=='{fit}' else b'\r' if p=='\n'
                         else encode(p)[:-1] for p in pieces)+b'\0'
        require(re.findall(b'%[sd]',bytes.fromhex(source['raw_hex']))==re.findall(b'%[sd]',payload),
                'Inventory-action arguments changed')
        widths=[measure(p.replace('{item}',''))+162*p.count('{item}')
                for p in re.split(r'\{fit\}|\n',text)]
        require(max(widths)<=216,'Inventory-action fallback exceeds safe width')
        maximum=len(payload)+61*text.count('{item}')
        require(maximum<=192,'Inventory action exceeds native192-byte buffer')
        offset=build.allocate(row['id'],payload,owner)
        struct.pack_into('<I',table,row['table_offset'],offset+0x08000000)
        entries.append(row|{'offset':offset,'encoded_hex':payload.hex(),'maximum_line_widths':widths,
                            'maximum_bytes':maximum,'capacity':192,'item_capacity':64,
                            'native_join_limit':215 if '{fit}' in text else None})
    offset=build.allocate(owner+'-table',bytes(table),owner)
    for site in owners:
        build.patch(f'{owner}-consumer-{site:x}',site,struct.pack('<I',START+0x08000000),
                    struct.pack('<I',offset+0x08000000),owner)
    return {'entries':entries,'table_offset':offset,'consumer_literals':list(owners),
            'catalog_sha256':digest(catalog_path.read_bytes()),'scope':catalog['scope']}
