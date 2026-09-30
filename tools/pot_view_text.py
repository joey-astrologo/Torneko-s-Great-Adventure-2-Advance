"""Private native pot-view empty and concealed-content labels."""
import json,struct
from tools.rom import ROOT,digest,require
from tools.compact_font import encode,measure
from tools.extract_shared_text import START,END,extract
CATALOG=ROOT/'translations/pot-view-review.json'
def add_pot_view(build):
 require(struct.unpack_from('<2I',build.original,0x1E9C)==(0x08002168,0x08002168),'Legacy07/08 control behavior changed')
 c=json.loads(CATALOG.read_text());require(c['base_rom_sha256']==digest(build.original) and {r['table_offset'] for r in c['entries']}=={0x20,0x24},'Pot-view review cohort differs');sources={r['table_offset']:r['source'] for r in extract()['entries']};table=bytearray(build.original[START:END]);rows=[]
 for row in c['entries']:
  require(row['status']=='reviewed' and row['source']==sources[row['table_offset']],'Pot-view source/review differs')
  raw=(b'\x07'+encode(row['english'])[:-1]+b'\x08\0') if row['table_offset']==0x24 else b' '+encode(row['english'].lstrip())
  require(measure(row['english'])<=162,'Pot-view width overflow');at=build.allocate(row['id'],raw,'pot-view');struct.pack_into('<I',table,row['table_offset'],at+0x08000000);rows.append(row|{'offset':at,'encoded_hex':raw.hex(),'width':measure(row['english']),'layout':{'pages':[[row['id']]]}})
 at=build.allocate('pot-view-private-table',bytes(table),'pot-view')
 for site in (0x18DE0,0x18F74,0x18FB8,0x190E0):build.patch('pot-view-reader-'+hex(site),site,struct.pack('<I',START+0x08000000),struct.pack('<I',at+0x08000000),'pot-view')
 return {'entries':rows,'table_offset':at,'catalog_sha256':digest(CATALOG.read_bytes()),'scope':c['scope']}
