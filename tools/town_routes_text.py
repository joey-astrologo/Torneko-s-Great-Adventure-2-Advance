"""Private older town/dungeon travel tables; keep owned early labels and geometry."""
import json,struct
from tools.rom import ROOT,digest,require
from tools.extract_items import source
from tools.compact_font import encode,measure
CATALOG=ROOT/'translations/town-routes-review.json'
BASE=0x14BE98
END=0x14BECC
SITES={0x4CC64:4,0x4CD9C:0,0x4CDAC:36}
INHERITED={1:'rom.0006c154',2:'rom.0006c14c',3:'rom.0006c144'}
def add_town_routes(build):
 c=json.loads(CATALOG.read_text());require(c['base_rom_sha256']==digest(build.original) and len(c['entries'])==9 and {i for e in c['entries'] for i in e['table_indices']}==set(range(13))-set(INHERITED),'Town route source cohort differs');table=bytearray(build.original[BASE:END]);inherited=[];rows=[]
 for i,ident in INHERITED.items():
  owned=next(a for a in build.allocations if a['id']==ident);patch=next(p for p in build.patches if p['id']==ident+'-pointer');require(patch['start']==BASE+4*i and patch['after_hex']==struct.pack('<I',owned['start']+0x08000000).hex() and bytes(build.data[BASE+4*i:BASE+4*i+4])==bytes.fromhex(patch['after_hex']),'Inherited town label ownership differs');table[4*i:4*i+4]=bytes.fromhex(patch['after_hex']);inherited.append(dict(index=i,id=ident,offset=owned['start']))
 for e in c['entries']:
  require(e['status']=='reviewed' and not any(ch in e['english'] for ch in '{}%@\n'),'Town route label review/control differs');budget=96 if e['table_indices']==[0] else 76 if any(i>=8 for i in e['table_indices']) else 140;require(e['text_budget']==budget and measure(e['english'])<=budget,'Town route label region exceeded')
  for i in e['table_indices']:require(e['source']==source(build.original,struct.unpack_from('<I',table,4*i)[0]),'Town route source identity differs')
  raw=(b'' if e['table_indices']==[0] else b'\x06\x0c')+encode(e['english']);at=build.allocate(e['id'],raw,'town-routes');rows.append(e|dict(offset=at,encoded_hex=raw.hex(),layout=dict(pages=[[e['english']]],line_widths=[[measure(e['english'])]],text_budget=budget,left_inset=0 if budget==96 else 12)))
  for i in e['table_indices']:struct.pack_into('<I',table,4*i,at+0x08000000)
 at=build.allocate('town-routes-private-table',bytes(table),'town-routes')
 for site,delta in SITES.items():build.patch('town-routes-reader-'+hex(site),site,struct.pack('<I',BASE+delta+0x08000000),struct.pack('<I',at+delta+0x08000000),'town-routes')
 return dict(entries=rows,table_offset=at,inherited=inherited,catalog_sha256=digest(CATALOG.read_bytes()),scope=c['scope'])
