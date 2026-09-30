"""owned reference-list labels and existing reviewed name table consumers."""
import json,struct
from tools.rom import ROOT,digest,require
from tools.compact_font import encode,measure
from tools.extract_shared_text import START,END,extract
CATALOG=ROOT/'translations/reference-lists-review.json'
SITES=((0x20A84,'item-definitions',0x141B9C),(0x20AFC,'skill-info-definitions',0x1457EC),(0x20CC8,'skill-info-definitions',0x1457EC),(0x20D48,'spell-info-definitions',0x146DF4),(0x20F08,'spell-info-definitions',0x146DF4))

def add_reference_lists(build):
 c=json.loads(CATALOG.read_text());require(c['base_rom_sha256']==digest(build.original),'Reference list base differs');src={r['table_offset']:r['source'] for r in extract()['entries']};table=bytearray(build.original[START:END]);rows=[]
 require({r['table_offset'] for r in c['entries']}=={0x9B0,0x9B4,0x9B8,0x9BC,0x74C},'Reference list label selection differs')
 for r in c['entries']:
  require(r['source']==src[r['table_offset']] and r['status']=='reviewed','Reference list source/review differs')
  payload=encode(r['english']);budget=58 if r['table_offset'] in (0x9B0,0x9B4,0x9B8) else 162
  require(measure(r['english'])<=budget and len(payload)<=61,'Reference label exceeds actual cursor/buffer region')
  at=build.allocate(r['id'],payload,'reference-lists');struct.pack_into('<I',table,r['table_offset'],at+0x08000000);rows.append(r|{'offset':at,'encoded_hex':payload.hex(),'width':measure(r['english']),'width_budget':budget,'capacity':64})
 at=build.allocate('reference-list-private-table',bytes(table),'reference-lists')
 for site,inner in ((0x207F0,0),(0x20A80,0x9BC),(0x20D18,0),(0x20F54,0)):
  build.patch(f'reference-list-table-{site:x}',site,struct.pack('<I',START+inner+0x08000000),struct.pack('<I',at+inner+0x08000000),'reference-lists')
 copies=[]
 for site,ident,original in SITES:
  owned=next(r for r in build.allocations if r['id']==ident);size=owned['end_exclusive']-owned['start'];stride={'item-definitions':24,'skill-info-definitions':36,'spell-info-definitions':12}[ident]
  require(size%stride==0,'Reference definitions stride differs')
  for n in range(size//stride):require(build.data[owned['start']+n*stride+4:owned['start']+(n+1)*stride]==build.original[original+n*stride+4:original+(n+1)*stride],'Reference definitions mechanics changed')
  build.patch(f'reference-list-names-{site:x}',site,struct.pack('<I',original+0x08000000),struct.pack('<I',owned['start']+0x08000000),'reference-lists');copies.append({'literal':site,'allocation':ident,'offset':owned['start'],'stride':stride})
 return {'entries':rows,'table_offset':at,'copies':copies,'catalog_sha256':digest(CATALOG.read_bytes()),'scope':c['scope']}
