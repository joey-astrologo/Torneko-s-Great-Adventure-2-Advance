import json,struct
from tools.rom import ROOT,digest,require
from tools.extract_items import source
from tools.compact_font import encode,measure
from tools.dialogue_layout import compile_dialogue
from tools.text_codec import tokenize
CATALOG=ROOT/'translations/carpenter-review.json'
SITES={0x502D8:0x14D058,0x502F0:0x14D09E,0x50334:0x14D0E2,0x5035C:0x14D14A,0x50360:0x14D18B,0x5036C:0x14D30B,0x503C0:0x14D21F,0x503E0:0x14D25F,0x503F4:0x14D2AF}
def add_carpenter(build):
 c=json.loads(CATALOG.read_text());require(c['base_rom_sha256']==digest(build.original) and len(c['entries'])==9 and {e['literal_offset'] for e in c['entries']}==set(SITES),'Carpenter source cohort differs');rows=[]
 for e in c['entries']:
  lit=e['literal_offset'];src=SITES[lit];text=e['english'];require(e['source']==source(build.original,src+0x08000000) and e['status']=='reviewed','Carpenter source/review differs')
  if lit==0x5035C:
   require(bytes.fromhex(e['source']['raw_hex']).count(b'%-03d')==1 and text.count('{count}')==1 and not any(x in text.replace('{count}','') for x in '{}%@'),'Carpenter count directive differs')
   lines=text.split('\n');widths=[measure(line.replace('{count}',''))+18*line.count('{count}') for line in lines];require(len(lines)==2 and max(widths)<=216,'Carpenter count window exceeded');raw=encode(text).replace(encode('{count}')[:-1],b'%d');maximum=len(raw)+1;require(maximum<=128,'Carpenter count exceeds128-byte shared scratch');layout=dict(pages=[lines],line_widths=[widths],maximum_width=216,encoded_bytes=len(raw),count_maximum=255,maximum_formatted_bytes=maximum)
  else:
   require('%' not in text,'Unexpected carpenter format');raw,layout=compile_dialogue(text,tokenize(bytes.fromhex(e['source']['raw_hex']))[0])
  at=build.allocate(e['id'],raw,'carpenter-text');build.patch(e['id']+'-reader',lit,struct.pack('<I',src+0x08000000),struct.pack('<I',at+0x08000000),'carpenter-text');rows.append(e|dict(offset=at,encoded_hex=raw.hex(),layout=layout))
 return dict(entries=rows,catalog_sha256=digest(CATALOG.read_bytes()),scope=c['scope'])
