"""dungeon shop confirmations; private caller ownership."""
import json,re,struct
from pathlib import Path
from tools.compact_font import encode,measure
from tools.extract_shared_text import START,END,extract
from tools.rom import ROOT,digest,require
CATALOG=ROOT/'translations/dungeon-shop-review.json'
LITERALS=(0x24480,0x24544,0x24588,0x245D4,0x2461C)

def add_dungeon_shop(build):
 c=json.loads(CATALOG.read_text());sources={r['table_offset']:r['source'] for r in extract()['entries']};table=bytearray(build.original[START:END]);rows=[]
 require(c['base_rom_sha256']==digest(build.original) and {r['table_offset'] for r in c['entries']}=={0x41C,0x420,0x424,0x428,0x464},'Shop cohort differs')
 for row in c['entries']:
  text=row['english'];src=sources[row['table_offset']];require(row['status']=='reviewed' and row['source']==src and text.count('{amount}')==bytes.fromhex(src['raw_hex']).count(b'%d'),'Shop source/review/arguments differ')
  payload=b''.join(b'\x03\x05%d\x05' if p=='{amount}' else b'\r' if p=='\n' else encode(p)[:-1] for p in re.split(r'(\{amount\}|\n)',text))+b'\0'
  widths=[measure(p.replace('{amount}',''))+66*p.count('{amount}') for p in text.split('\n')];maximum=len(payload)+9*text.count('{amount}')
  require(len(widths)<=2 and max(widths)<=216 and maximum<=256,'Shop native bounds exceeded')
  at=build.allocate(row['id'],payload,'dungeon-shop-text');struct.pack_into('<I',table,row['table_offset'],at+0x08000000);rows.append(row|{'offset':at,'encoded_hex':payload.hex(),'maximum_bytes':maximum,'maximum_line_widths':widths,'capacity':256})
 at=build.allocate('dungeon-shop-private-table',bytes(table),'dungeon-shop-text')
 for site in LITERALS:build.patch(f'dungeon-shop-table-{site:x}',site,struct.pack('<I',START+0x08000000),struct.pack('<I',at+0x08000000),'dungeon-shop-text')
 return {'entries':rows,'table_offset':at,'catalog_sha256':digest(CATALOG.read_bytes()),'scope':c['scope']}
