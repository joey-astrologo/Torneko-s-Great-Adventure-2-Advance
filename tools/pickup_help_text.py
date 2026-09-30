"""Owned tutorial-only pickup literals; original item dispatch remains untouched."""
import json,struct
from tools.rom import ROOT,digest,require
from tools.extract_items import source
from tools.compact_font import encode,measure
CATALOG=ROOT/'translations/pickup-help-review.json'
SOURCES={0x24E10:(0x1474C4,[203,204]),0x24E18:(0x147264,[1,3]),0x24E20:(0x1472BC,[30,31]),0x24E28:(0x14743C,[51]),0x24E30:(0x1473F8,[118]),0x24E38:(0x147314,[169]),0x24E40:(0x14734C,[188]),0x24E6C:(0x1473D8,[190])}
def add_pickup_help(build):
 catalog=json.loads(CATALOG.read_text());require(catalog['base_rom_sha256']==digest(build.original),'Pickup help base differs');rows=catalog['entries'];require(len(rows)==8 and {e['literal_offset'] for e in rows}==set(SOURCES),'Pickup help cohort differs');out=[]
 for e in rows:
  lit=e['literal_offset'];src,ids=SOURCES[lit];require(e['status']=='reviewed' and e['source']==source(build.original,src+0x08000000) and e['item_ids']==ids,'Pickup help source/dispatch differs')
  text=e['english'];original=bytes.fromhex(e['source']['raw_hex']);require(not any(c in text for c in '{}%@') and text.count('\t')==original.count(b'\x09') and text.startswith('\n')==original.startswith(b'\r'),'Pickup help controls differ')
  raw=bytearray();widths=[]
  for i,line in enumerate(text.split('\n')):
   if i:raw.append(13)
   indent=32 if line.startswith('\t') else 0
   if indent:raw.append(9);line=line[1:]
   require('\t' not in line,'Pickup help09 marker must begin an authored line');width=measure(line);require(width<=216,'Pickup help line exceeds window');widths.append(width);raw.extend(encode(line)[:-1])
  raw.append(0);require(len(raw)+192+4<=1024,'Pickup help and preceding pickup exceed queue capacity')
  at=build.allocate(e['id'],bytes(raw),'pickup-help');build.patch(e['id']+'-reader',lit,struct.pack('<I',src+0x08000000),struct.pack('<I',at+0x08000000),'pickup-help')
  out.append(e|dict(offset=at,encoded_hex=raw.hex(),layout=dict(line_ends=widths,maximum_width=216,control09_sets_queue_flag=True,queue_capacity=1024,maximum_combined_queue_bytes=len(raw)+196)))
 return dict(entries=out,catalog_sha256=digest(CATALOG.read_bytes()),scope=catalog['scope'])
