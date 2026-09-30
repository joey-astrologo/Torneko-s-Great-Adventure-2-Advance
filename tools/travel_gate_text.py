"""Private dungeon-entry restrictions within the native128-byte shared scratch."""
import struct,json
from tools.rom import ROOT,digest,require
CATALOG=ROOT/'translations/travel-gate-review.json'
from tools.extract_items import source
from tools.compact_font import encode,measure
TEXTS=[('limit',0x14C8E4,"Only {count} items allowed here.\nCarry fewer items."),('store',0x14C8E8,"No items allowed in this dungeon.\nStore or discard them first."),('sell',0x14C8EC,"No items allowed in this dungeon.\nSell or discard them first."),('level',0x14C8F0,"You must be at level 1\nto enter this dungeon.")]
def add_travel_gate(build):
 catalog=json.loads(CATALOG.read_text());require(catalog['base_rom_sha256']==digest(build.original) and [r['id'] for r in catalog['entries']]==['travel-gate.'+k for k,_,_ in TEXTS],'Travel-gate catalog/base differs');rows=[];table=bytearray(build.original[0x14C8E4:0x14C8F4])
 for index,(key,slot,english) in enumerate(TEXTS):
  reviewed=catalog['entries'][index];english=reviewed['english']
  original=source(build.original,struct.unpack_from('<I',build.original,slot)[0]);require(('%{unclassified-control:64}' in original['japanese'])==(key=='limit'),'Travel restriction format differs')
  require(reviewed['status']=='reviewed' and reviewed['source']==original and english.count('{count}')==int(key=='limit') and not any(c in english.replace('{count}','') for c in '{}%'),'Travel-gate source/substitution differs')
  raw=encode(english).replace(encode('{count}')[:-1],b'%d');maximum=len(raw)+3 if key=='limit' else len(raw);widths=[measure(line.replace('{count}',''))+(30 if '{count}' in line else 0) for line in english.split('\n')]
  require(maximum<=128 and len(widths)==2 and max(widths)<=216,'Travel restriction scratch/window overflow');at=build.allocate('travel-gate.'+key,raw,'travel-gate');struct.pack_into('<I',table,4*index,at+0x08000000)
  rows.append({'id':'travel-gate.'+key,'source':original,'english':english,'status':'reviewed','review':'Independent bilingual review preserves dungeon-entry condition and required item reduction, storage/discard, sale/discard or level1 remedy. Two-line display fits the existing128-byte scratch and216px region. Limit comes from the original signed16-bit getter;32767 is a rendering bound, not a claimed gameplay capacity.','offset':at,'encoded_hex':raw.hex(),'maximum_bytes':maximum,'line_widths':widths,'layout':{'pages':[english.split('\n')]}})
 at=build.allocate('travel-gate-private-pointers',bytes(table),'travel-gate')
 for site,delta in [(0x4BD04,0),(0x4BD30,4),(0x5222C,12)]:build.patch('travel-gate-reader-'+hex(site),site,struct.pack('<I',0x0814C8E4+delta),struct.pack('<I',at+0x08000000+delta),'travel-gate')
 return {'entries':rows,'table_offset':at,'catalog_sha256':digest(CATALOG.read_bytes()),'scope':catalog['scope']}
