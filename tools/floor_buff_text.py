"""Own the exhausted item bonus-effect message and its raw item-name lookup."""
import json,struct
from tools.compact_font import encode,measure
from tools.extract_items import DEFINITIONS,COUNT
from tools.extract_shared_text import START,END,extract
from tools.inventory_action_text import CONTROL
from tools.rom import ROOT,digest,require
CATALOG=ROOT/'translations/floor-buff-review.json'


def add_floor_buffs(build,items):
    catalog=json.loads(CATALOG.read_text());source=next(r['source'] for r in extract()['entries'] if r['table_offset']==0x8EC)
    require(catalog['base_rom_sha256']==digest(build.original) and len(catalog['entries'])==1,'Floor buff catalog/base differs')
    row=catalog['entries'][0];text=row['english']
    require(row['source']==source and row['status']=='reviewed' and text.count('{item}')==text.count('{fit}')==1,'Floor buff source/review differs')
    parts=text.split('{fit}');widths=[measure(p.replace('{item}',''))+162*p.count('{item}') for p in parts]
    require(max(widths)<=216 and text.startswith('{item}{fit}') and not any(c in text.replace('{item}','').replace('{fit}','') for c in '{}%\r\n'),'Floor buff format/width differs')
    payload=b'%s'+CONTROL+encode(parts[1]);maximum=len(payload)+61;require(maximum<=256,'Floor buff output exceeds256bytes')
    at=build.allocate(row['id'],payload,'floor-buff-text');table=bytearray(build.original[START:END]);struct.pack_into('<I',table,0x8EC,at+0x08000000)
    table_at=build.allocate('floor-buff-private-table',bytes(table),'floor-buff-text')
    build.patch('floor-buff-message-table',0x33548,struct.pack('<I',START+0x08000000),struct.pack('<I',table_at+0x08000000),'floor-buff-text')
    names={int(r['id'].rsplit('.',1)[1]):r for r in items['entries'] if r['id'].startswith('item.name.')}
    require(set(names)==set(range(COUNT)),'Floor buff requires all original item names')
    definitions=bytearray(build.original[DEFINITIONS:DEFINITIONS+COUNT*24])
    for ident,r in names.items():struct.pack_into('<I',definitions,ident*24,r['offset']+0x08000000)
    defs=build.allocate('floor-buff-item-definitions',bytes(definitions),'floor-buff-text')
    build.patch('floor-buff-item-table',0x33550,struct.pack('<I',DEFINITIONS+0x08000000),struct.pack('<I',defs+0x08000000),'floor-buff-text')
    return {'entries':[row|{'offset':at,'encoded_hex':payload.hex(),'maximum_bytes':maximum,'maximum_segment_widths':widths,'fields':['item'],'capacity':256}], 'table_offset':table_at,'definition_copy_offset':defs,'catalog_sha256':digest(CATALOG.read_bytes()),'scope':catalog['scope']}
