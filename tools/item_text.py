"""First reviewed item names/descriptions through isolated native consumer tables."""
import json,struct,re
from tools.compact_font import encode,measure
from tools.dialogue_layout import PLAYER_WIDTH
from tools.extract_items import DEFINITIONS,COUNT,DESCRIPTIONS,CATEGORY_DESCRIPTIONS,extract,source
from tools.rom import ROOT,digest,require
CATALOG=ROOT/'translations/items-review.json'

def compile_description(english,src):
 from tools.text_codec import tokenize
 lines=english.split('\n')
 require(len(lines)<=4 and all(measure(line.replace('{player}',''))+PLAYER_WIDTH*line.count('{player}')<=216 for line in lines),'Item description exceeds Info layout')
 require(not any(c in english.replace('{player}','') for c in '{}'),'Unknown item description field')
 source_players=sum(t.get('kind')=='command' and t.get('code')==0x7e for t in tokenize(bytes.fromhex(src['raw_hex']))[0])
 require(english.count('{player}')==source_players,'Item description player substitution differs')
 return b''.join(b'\x7e' if part=='{player}' else encode(part)[:-1] for part in re.split(r'(\{player\})',english))+b'\0'


def add_items(build,extra_catalog=None,reserve_inscription=False):
 from tools.item_spacing import add_spacing
 spacing=add_spacing(build)
 review=json.loads(CATALOG.read_text());require(review['base_rom_sha256']==digest(build.original),'Item base changed')
 if extra_catalog:
  extra=json.loads(extra_catalog.read_text());require(extra['base_rom_sha256']==digest(build.original),'Additional item base changed')
  require(not {r['id'] for r in review['entries']}&{r['id'] for r in extra['entries']},'Duplicate additional item definition')
  review['entries']+=extra['entries']
 original=build.original;definitions=bytearray(original[DEFINITIONS:DEFINITIONS+COUNT*24]);descriptions=bytearray(original[DESCRIPTIONS:DESCRIPTIONS+222*4]);categories=bytearray(original[CATEGORY_DESCRIPTIONS:CATEGORY_DESCRIPTIONS+14*4]);rows=[]
 source_items={r['id']:r for r in extract()['items']}
 def allocate(ident,english,src,capacity):
  require(src and source(original,0x8000000+src['offset'])==src,'Item text source changed')
  data=encode(english) if ident.startswith('item.name.') else compile_description(english,src)
  if ident=='item.name.0':
   require(src['raw_hex']=='030691668ee80500','Bare-hands source colour changed')
   data=b'\x03\x06'+data[:-1]+b'\x05\0'
  require(len(data)<=capacity,'Item text exceeds byte allowance')
  offset=build.allocate(ident,data,'item-text');rows.append({'id':ident,'english':english,'offset':offset,'encoded_hex':data.hex(),'source':src,'capacity':capacity});return 0x8000000+offset
 for row in review['entries']:
  i=row['id'];require(row['status']=='reviewed' and row['name_source']==source_items[i]['name'],'Item review identity changed')
  # First cohort reserves space for markers and numeric suffixes in 64-byte list output.
  require(measure(row['name'])<=80 and len(encode(row['name']))<=31,'Item name exceeds base-name reserve')
  struct.pack_into('<I',definitions,i*24,allocate(f'item.name.{i}',row['name'],row['name_source'],31))
  if row['description']:
   require(row['description_source']==source_items[i]['description'],'Item description identity changed')
   struct.pack_into('<I',descriptions,i*4,allocate(f'item.description.{i}',row['description'],row['description_source'],256))
 for category,english in review['category_descriptions'].items():
  i=int(category);src=source(original,struct.unpack_from('<I',categories,i*4)[0])
  struct.pack_into('<I',categories,i*4,allocate(f'item.category.{i}',english,src,256))
 for row in review.get('special_descriptions',[]):
  require(row['id']==221 and row['status']=='reviewed','Unowned special description')
  require(row['source']==extract()['special_description_221'],'Special description source changed')
  struct.pack_into('<I',descriptions,221*4,allocate('item.description.221',row['english'],row['source'],256))
 # Name formatter plus the bank's raw gift-name lookup receive the copied
 # definitions. Reward item IDs/effects still use their original tables.
 sites=[i for i in range(0xf244,0xf688,4) if original[i:i+4]==struct.pack('<I',DEFINITIONS+0x8000000)]
 require(sites==[0xf29c,0xf328,0xf368,0xf3c4,0xf3f4,0xf414,0xf438,0xf470,0xf490,0xf4e4,0xf580,0xf5dc], 'Item definition consumers changed')
 # The optional inscription compiler supplies an independently owned effect
 # name table for this one reader; ordinary names retain the complete labels.
 if reserve_inscription:sites.remove(0xf328)
 require(original[0x1e380:0x1e384]==struct.pack('<I',DEFINITIONS+0x8000000),'Bank reward name consumer changed')
 sites.extend([0x1e380,0x1e44c])
 require(original[0x1e44c:0x1e450]==struct.pack('<I',DEFINITIONS+0x8000000),'Bakery name/price consumer changed')
 # Fused equipment with no remaining ability bits uses a separate category
 # fallback at 17BF8; the ordinary category reader uses 17E68.
 for ident,data,base,consumers in [('definitions',definitions,DEFINITIONS,sites),('descriptions',descriptions,DESCRIPTIONS,[0x17e6c,0x17ef0]),('categories',categories,CATEGORY_DESCRIPTIONS,[0x17bf8,0x17e68])]:
  offset=build.allocate('item-'+ident,bytes(data),'item-text')
  for site in consumers:build.patch(f'item-{ident}-{site:x}',site,struct.pack('<I',base+0x8000000),struct.pack('<I',offset+0x8000000),'item-text')
 # The shared arrow count template contains a Japanese counter. Isolate its one consumer.
 table=bytearray(original[0x140d68:0x140d78]);old=struct.unpack_from('<I',table,12)[0]
 require(old==0x80648c0,'Missing arrow count format')
 fmt=b'\x03%c%s'+encode(' x ')[:-1]+b'%s\x05\0';offset=build.allocate('item-arrow-count',fmt,'item-text');struct.pack_into('<I',table,12,offset+0x8000000)
 table_offset=build.allocate('item-arrow-format-table',bytes(table),'item-text')
 build.patch('item-arrow-format-consumer',0xf4e0,struct.pack('<I',0x8140d68),struct.pack('<I',table_offset+0x8000000),'item-text')
 return {'entries':rows,'review_sha256':digest(CATALOG.read_bytes()),'additional_review_sha256':digest(extra_catalog.read_bytes()) if extra_catalog else None,'definition_count':COUNT,'first_name_budget':80,'inventory_row_budget':162,'inventory_bytes':64,'spacing':spacing,'arrow_format':{'offset':offset,'encoded_hex':fmt.hex(),'source':old}}
