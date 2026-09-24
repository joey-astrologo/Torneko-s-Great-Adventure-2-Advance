"""Reviewed dungeon actor names; preserve the existing relocated data footprint."""
import json,struct
from tools.rom import ROOT,digest,require
from tools.compact_font import encode,measure
from tools.extract_monsters import extract,RESOURCE,LINK_BASE,DEFINITIONS
from tools.lz77 import decompress,pack_literals
CATALOG=ROOT/'translations/monsters-review.json'

def add_monsters(build):
 review=json.loads(CATALOG.read_text());sources=extract();data=bytearray(decompress(build.original,RESOURCE)[0]);rows=[]
 require(review['base_rom_sha256']==digest(build.original),'Monster review base changed')
 require([r['id'] for r in review['entries']]==list(range(141)),'Monster review coverage differs')
 for row,src in zip(review['entries'],sources['entries']):
  require(row['status']=='reviewed' and all(row[k]==src[k] for k in ('id','raw_table','dungeon','definition_offset')),'Monster source/review differs')
  english=row['dungeon_english'];payload=encode(english)
  # Native name+level scratch is [02008D08,02008D48); reserve even signed int32.
  require(len(payload)+6+11<=64 and measure(english)<=114,'Actor name exceeds proven reserve')
  offset=build.allocate('actor-name-'+str(row['id']),payload,'actor-names')
  struct.pack_into('<I',data,row['definition_offset'],offset+0x8000000)
  rows.append({'id':row['id'],'english':english,'offset':offset,'encoded_hex':payload.hex(),'source':row['dungeon'],'width_px':measure(english)})
 packed=pack_literals(data);offset=build.allocate('dungeon-data-with-english-names',packed,'actor-names')
 build.patch('dungeon-data-pointer',0x3a228,struct.pack('<I',0x08477700),struct.pack('<I',offset+0x8000000),'actor-names')
 fmt=encode(' Lv')[:-1]+b'%d\0';fmt=b'%s'+fmt
 level=build.allocate('actor-level-format',fmt,'actor-names')
 build.patch('actor-level-format-pointer',0x9c08,struct.pack('<I',0x0806b3d0),struct.pack('<I',level+0x8000000),'actor-names')
 return {'entries':rows,'review_sha256':digest(CATALOG.read_bytes()),'dungeon_resource':sources['dungeon_resource'],'replacement_resource':offset,'decoded_bytes':len(data),'decoded_sha256':digest(data),'level_format':{'offset':level,'encoded_hex':fmt.hex()},'scope':'Dungeon actor definition name pointers only. Original 64,668-byte resource size, record attributes and linked relocation behavior preserved. Raw result/history table awaits separate width/consumer acceptance.'}
