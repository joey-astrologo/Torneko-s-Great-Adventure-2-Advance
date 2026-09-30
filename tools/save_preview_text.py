"""three-row title save-preview formats and location-name readers."""
import json,re,struct
from tools.rom import ROOT,digest,require
from tools.compact_font import encode,measure
from tools.extract_shared_text import START,END,extract
from tools.extract_items import source
from tools.text_codec import tokenize
CATALOG=ROOT/'translations/save-preview-review.json'
TOKENS={'{inset}':b'\x04\x14','{village}':b'%s','{level}':b'%d','{hp}':b'%d','{maxhp}':b'%d','{place}':b'%s','{floor}':b'%d','{attempt}':b'%d','{player}':b'\x7e','\n':b'\r'}
BOUNDS={'{inset}':20,'{village}':112,'{level}':30,'{hp}':30,'{maxhp}':30,'{place}':173,'{floor}':30,'{attempt}':30,'{player}':98}

def add_save_preview(build):
 c=json.loads(CATALOG.read_text());require(c['base_rom_sha256']==digest(build.original),'Save-preview base differs');sources={r['table_offset']:r['source'] for r in extract()['entries']};table=bytearray(build.original[START:END]);locations=bytearray(build.original[0x14E6DC:0x14E6E8]);rows=[]
 # Retain already-owned global name/village editor substitutions if a shared
 # literal has further consumers inside this original function.
 for slot in (0x18C,0x964):table[slot:slot+4]=build.data[START+slot:START+slot+4]
 for row in c['entries']:
  text=row['english'];slot=row.get('table_offset');src=row['source'];require(row['status']=='reviewed' and source(build.original,src['offset']+0x08000000)==src,'Save-preview source/review differs')
  if slot is not None:require(src==sources[slot],'Save-preview shared source differs')
  pieces=re.split(r'(\{[^}]+\}|\n)',text);require(all(p in TOKENS or not any(x in p for x in '{}%\r') for p in pieces),'Unknown save-preview control')
  payload=b''.join(TOKENS[p] if p in TOKENS else encode(p)[:-1] for p in pieces)+b'\0'
  original_fields=[f[-1:] for f in re.findall(b'%[0-9]*[sd]',bytes.fromhex(src['raw_hex']))];require(original_fields==[f[-1:] for f in re.findall(b'%[sd]',payload)],'Save-preview argument order differs')
  require(text.count('{player}')==sum(t['raw_hex']=='7e' for t in tokenize(bytes.fromhex(src['raw_hex']))[0]),'Save-preview player control differs')
  widths=[]
  for line in text.split('\n'):
   bound=measure(re.sub(r'\{[^}]+\}','',line))+sum(BOUNDS[t] for t in re.findall(r'\{[^}]+\}',line));widths.append(bound)
  # Dungeon names have98px maximum; the town field may contain two explicit
  # lines (ending summary) or a98px native player control in the home label.
  if slot in (0x5C8,0xA0C):widths[-1]-=173-(18 if slot==0xA0C else 98)
  maximum=len(payload)+sum(15 if token=='{village}' else 127 if token=='{place}' else 3 for token in re.findall(r'\{[^}]+\}',text) if token!='{player}')
  require(max(widths)<=216 and len(widths)<=3 and maximum<=256,'Save-preview width/byte/rows overflow')
  at=build.allocate(row['id'],payload,'save-preview');rows.append(row|{'offset':at,'encoded_hex':payload.hex(),'line_widths':widths,'maximum_bytes':maximum,'capacity':256 if original_fields else 'immutable-ROM'})
  if slot is not None:struct.pack_into('<I',table,slot,at+0x08000000)
  else:struct.pack_into('<I',locations,4*row['location_id'],at+0x08000000)
 at=build.allocate('save-preview-private-table',bytes(table),'save-preview');loc=build.allocate('save-preview-town-locations',bytes(locations),'save-preview')
 for site in (0x14978,0x149B8,0x14A18,0x14B28):build.patch(f'save-preview-table-{site:x}',site,struct.pack('<I',START+0x08000000),struct.pack('<I',at+0x08000000),'save-preview')
 for site in (0x52B2C,0x52B38):build.patch(f'save-preview-location-{site:x}',site,struct.pack('<I',0x0814E6DC),struct.pack('<I',loc+0x08000000),'save-preview')
 return {'entries':rows,'table_offset':at,'location_table_offset':loc,'catalog_sha256':digest(CATALOG.read_bytes()),'scope':c['scope']}
