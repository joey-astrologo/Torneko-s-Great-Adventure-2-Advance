"""two-command town root: measured34px label region, closed before child."""
import json,struct
from tools.rom import ROOT,digest,require
from tools.compact_font import encode,measure
from tools.extract_shared_text import START,END,extract
CATALOG=ROOT/'translations/town-root-review.json'
def add_town_root(build):
 c=json.loads(CATALOG.read_text());r=c['entries'][0];src=next(x['source'] for x in extract()['entries'] if x['table_offset']==0x994)
 require(c['base_rom_sha256']==digest(build.original) and len(c['entries'])==1 and r['source']==src and r['status']=='reviewed' and r['english']=='  Items\n  Option','Town root source/review differs')
 payload=encode(r['english']);require(max(map(measure,r['english'].split('\n')))<=40,'Town root exceeds cursor/label width');at=build.allocate(r['id'],payload,'town-root');table=bytearray(build.original[START:END]);struct.pack_into('<I',table,0x994,at+0x08000000);t=build.allocate('town-root-private-table',bytes(table),'town-root')
 build.patch('town-root-reader',0x206B8,struct.pack('<I',START+0x08000000),struct.pack('<I',t+0x08000000),'town-root')
 build.patch('town-root-width',0x2069A,bytes.fromhex('0422'),bytes.fromhex('0522'),'town-root')
 return {'entries':[r|{'offset':at,'encoded_hex':payload.hex(),'width_budget':34,'cursor_reserve':6,'width':40,'rows':2}],'table_offset':t,'catalog_sha256':digest(CATALOG.read_bytes()),'scope':c['scope']}
