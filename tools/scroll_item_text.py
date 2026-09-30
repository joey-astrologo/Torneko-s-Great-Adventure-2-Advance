"""Explicit English inscribed-scroll effects replace Japanese suffix truncation."""
import json,struct
from tools.compact_font import encode,measure
from tools.extract_shared_text import START,END,extract as shared
from tools.extract_items import DEFINITIONS,COUNT,extract,source
from tools.rom import ROOT,digest,require
CATALOG=ROOT/'translations/scroll-item-review.json'

def add_scroll_item(build,items):
    original=build.original;catalog=json.loads(CATALOG.read_text());definitions=extract()['items'];sources={r['id']:r for r in definitions};names={int(r['id'].rsplit('.',1)[1]):r for r in items['entries'] if r['id'].startswith('item.name.')}
    require(catalog['base_rom_sha256']==digest(original) and len(names)==COUNT,'Scroll item source/name set differs')
    expected={r['id'] for r in definitions if r['category']==0 and r['id']!=153}
    require({r['item_id'] for r in catalog['effects']}==expected,'Scroll inscription effect set differs')
    records=bytearray(original[DEFINITIONS:DEFINITIONS+COUNT*24]);rows=[]
    for ident in range(COUNT):struct.pack_into('<I',records,ident*24,names[ident]['offset']+0x08000000)
    for row in catalog['effects']:
        ident=row['item_id'];require(row['status']=='reviewed' and row['source']==sources[ident]['name'],'Scroll effect source/review differs')
        payload=encode(row['english']);require(len(payload)<=64,'Scroll effect scratch overflow')
        at=build.allocate(row['id'],payload,'scroll-item-text');struct.pack_into('<I',records,24*ident,at+0x08000000);rows.append(row|{'offset':at,'encoded_hex':payload.hex()})
    definition_at=build.allocate('scroll-inscription-effect-definitions',bytes(records),'scroll-item-text')
    label,fmt=catalog['entries'];require(label['table_offset']==0x448 and label['source']==next(r['source'] for r in shared()['entries'] if r['table_offset']==0x448),'Scroll inscription kind source differs')
    require(fmt['source']==source(original,struct.unpack_from('<I',original,0xF32C)[0]) and label['english']=='Blank' and fmt['english']=='{kind}: {effect}' and all(r['status']=='reviewed' for r in (label,fmt)),'Scroll inscription format/review differs')
    for row,payload in [(label,encode(label['english'])),(fmt,b'\x03\x04%s'+encode(': ')[:-1]+b'%s\x05\0')]:
        at=build.allocate(row['id'],payload,'scroll-item-text');rows.append(row|{'offset':at,'encoded_hex':payload.hex()})
    table=bytearray(original[START:END]);struct.pack_into('<I',table,0x448,rows[-2]['offset']+0x08000000);table_at=build.allocate('scroll-inscription-kind-table',bytes(table),'scroll-item-text')
    widths=[measure('Blank: '+r['english']) for r in catalog['effects']];sizes=[len(encode('Blank: '+r['english']))+3 for r in catalog['effects']]
    require(max(widths)<=110 and max(sizes)+21<=64,'Inscribed scroll row budget exceeded')
    for site,old,new in [(0xF328,DEFINITIONS,definition_at),(0xF330,START,table_at),(0xF32C,fmt['source']['offset'],rows[-1]['offset'])]:build.patch(f'scroll-inscription-reader-{site:x}',site,struct.pack('<I',old+0x08000000),struct.pack('<I',new+0x08000000),'scroll-item-text')
    # Keep the terminating NUL at the full English effect length. SP+4..44
    # stays the original64-byte field; the original frame and ABI are unchanged.
    build.patch('scroll-inscription-no-japanese-suffix',0xF310,bytes.fromhex('0638'),bytes.fromhex('0046'),'scroll-item-text')
    return {'entries':rows,'table_offset':table_at,'definition_copy_offset':definition_at,'catalog_sha256':digest(CATALOG.read_bytes()),'maximum_base_width':max(widths),'maximum_complete_row_bytes':max(sizes)+21,'scope':catalog['scope']}
