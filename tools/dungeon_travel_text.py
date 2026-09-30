"""Private destination labels for the native52304 travel picker."""
import json,struct
from tools.rom import ROOT,digest,require
from tools.extract_items import source
from tools.compact_font import encode,measure
CATALOG=ROOT/'translations/dungeon-travel-review.json'
def add_dungeon_travel(build):
 c=json.loads(CATALOG.read_text());require(c['base_rom_sha256']==digest(build.original) and [r['index'] for r in c['entries']]==list(range(8)),'Dungeon travel source cohort differs');rows=[];table=bytearray(build.original[0x14D71C:0x14D738])
 for row in c['entries']:
  i=row['index'];ptr=0x0814D42C if i==7 else struct.unpack_from('<I',table,4*i)[0];require(row['status']=='reviewed' and row['source']==source(build.original,ptr),'Dungeon travel source differs');english=row['english'];require(not any(c in english for c in '{}%@\n'),'Unexpected dungeon travel control');require(measure(english)<=(152 if i==7 else 138),'Dungeon travel label exceeds original region');raw=(b'\x14' if i==7 else b'\x06\x06')+encode(english);at=build.allocate(row['id'],raw,'dungeon-travel');rows.append(row|{'offset':at,'encoded_hex':raw.hex(),'layout':{'pages':[[english]],'line_widths':[[measure(english)]],'maximum_width':152 if i==7 else 138}})
  if i!=7:struct.pack_into('<I',table,4*i,at+0x08000000)
 at=build.allocate('dungeon-travel-private-labels',bytes(table),'dungeon-travel')
 for site,old,new in [(0x52420,0x0814D71C,at+0x08000000),(0x523B8,0x0814D42C,rows[-1]['offset']+0x08000000)]:build.patch('dungeon-travel-reader-'+hex(site),site,struct.pack('<I',old),struct.pack('<I',new),'dungeon-travel')
 return {'entries':rows,'table_offset':at,'catalog_sha256':digest(CATALOG.read_bytes()),'scope':c['scope']}
