"""Owned dungeon-entry and saved-village overwrite confirmation literals."""
import json,struct
from tools.rom import ROOT,digest,require
from tools.extract_items import source
from tools.dialogue_layout import compile_dialogue
from tools.compact_font import encode,measure
from tools.text_codec import tokenize
CATALOG=ROOT/'translations/travel-confirm-review.json'
SITES={0x14C7EC:(0x4BB2C,0x4CA24,0x522CC),0x14C809:(0x4BB30,0x4CA28,0x522D0)}
def add_travel_confirm(build):
 c=json.loads(CATALOG.read_text());require(c['base_rom_sha256']==digest(build.original) and {e['source']['offset'] for e in c['entries']}==set(SITES) and len(c['entries'])==2,'Travel confirmation source cohort differs');rows=[]
 for e in c['entries']:
  src=e['source']['offset'];require(e['source']==source(build.original,src+0x08000000) and e['status']=='reviewed' and e['literals']==list(SITES[src]),'Travel confirmation review/source differs');original=bytes.fromhex(e['source']['raw_hex']);text=e['english']
  if src==0x14C809:
   require(original.count(b'\x1f')==1 and original.count(b'\x14')==2 and text.count('{village}')==1 and text.count('{center}')==2,'Travel saved-name controls differ');raw,layout=compile_dialogue(text.replace('{village}','{player}'),tokenize(original.replace(b'\x1f',b'\x7e'))[0]);raw=raw.replace(b'\x7e',b'\x1f');layout['pages']=[[line.replace('{player}','{village}') for line in page] for page in layout['pages']];layout['line_widths']=[[measure(line.replace('{village}','').replace('{center}',''))+112*line.count('{village}') for line in page] for page in layout['pages']];layout['commands']=['{center}','{village}','{center}'];layout['saved_village_maximum_width']=112
  else:raw,layout=compile_dialogue(text,tokenize(original)[0])
  require(len(layout['pages'])==1 and max(layout['line_widths'][0])<=216,'Travel confirmation window exceeded');at=build.allocate(e['id'],raw,'travel-confirm');rows.append(e|dict(offset=at,encoded_hex=raw.hex(),layout=layout))
  for site in SITES[src]:build.patch('travel-confirm-'+hex(site),site,struct.pack('<I',src+0x08000000),struct.pack('<I',at+0x08000000),'travel-confirm')
 return dict(entries=rows,catalog_sha256=digest(CATALOG.read_bytes()),scope=c['scope'])
