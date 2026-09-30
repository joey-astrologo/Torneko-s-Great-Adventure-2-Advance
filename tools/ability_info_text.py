"""Private fused-equipment Info descriptions, retaining the original frame/UI."""
import json,struct
from tools.rom import ROOT,digest,require
from tools.compact_font import encode,measure
from tools.extract_items import source
from tools.extract_shared_text import START,END
CATALOG=ROOT/'translations/ability-info-review.json'
def add_ability_info(build):
 c=json.loads(CATALOG.read_text());require(c['base_rom_sha256']==digest(build.original) and len(c['entries'])==41 and [r['index'] for r in c['entries']]==list(range(41)),'Ability Info cohort/base differs');table=bytearray(build.original[0x1447A8:0x144848]);rows=[]
 for row in c['entries']:
  pointer=struct.unpack_from('<I',build.original,0x1447A8+4*row['index'] if row['index']<40 else START+0x9FC)[0]
  require(row['status']=='reviewed' and row['source']==source(build.original,pointer),'Ability Info source differs');require(not any(c in row['english'] for c in '{}%'),'Unexpected ability Info substitution');lines=row['english'].split('\n');raw=encode(row['english']);widths=[measure(s) for s in lines]
  require(len(lines)<=3 and max(widths)<=216 and len(raw)+2<=256,'Ability Info native layout/buffer overflow');at=build.allocate(row['id'],raw,'ability-info');rows.append(row|{'offset':at,'encoded_hex':raw.hex(),'line_widths':widths,'maximum_bytes':len(raw)+2,'layout':{'pages':[lines]}})
  if row['index']<40:struct.pack_into('<I',table,row['index']*4,at+0x08000000)
 at=build.allocate('ability-info-private-table',bytes(table),'ability-info');build.patch('ability-info-reader',0x17CA4,struct.pack('<I',0x081447A8),struct.pack('<I',at+0x08000000),'ability-info')
 table=bytearray(build.original[START:END]);struct.pack_into('<I',table,0x9FC,rows[-1]['offset']+0x08000000);special=build.allocate('ability-info-unbreakable-table',bytes(table),'ability-info');build.patch('ability-info-unbreakable-reader',0x17CC8,struct.pack('<I',START+0x08000000),struct.pack('<I',special+0x08000000),'ability-info')
 return {'entries':rows,'table_offset':at,'catalog_sha256':digest(CATALOG.read_bytes()),'scope':c['scope']}
