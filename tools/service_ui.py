"""Reviewed dungeon UI resources with original geometry and bounded formats."""
import json,struct
from tools.compact_font import encode,measure
from tools.rom import ROOT,require,digest
from tools.text_codec import tokenize

CATALOG=ROOT/'translations/dungeon-ui-review.json'
OWNER='dungeon-ui'

def text(s):return encode(s)[:-1]
def spaced(s):return b' '.join(text(x) for x in s.split(' '))
def payload(row):
 kind=row['kind'];labels=row['english']
 if kind=='plain':
  require(all(measure(s)<=216 for s in labels.split('\n')),'Dungeon UI prose exceeds 216 px')
  return encode(labels)
 if kind=='option':
  require(measure(labels.replace(' ','') )+labels.count(' ')*6<=65,'Option label exceeds its column')
  return bytes.fromhex(row['prefix_hex'])+spaced(labels)+(b'%s' if row.get('suffix') else b'')+(b'\r' if row['newline'] else b'')+b'\0'
 if kind=='toggle':
  a,b=labels;selected=row['selected']
  require(measure(a)+6+measure(b)<=192-77,'Toggle fields exceed window')
  return b'\x06\x4d'+(b'\x01' if selected==0 else b'')+text(a)+(b'\x02' if selected==0 else b'')+b' '+(b'\x01' if selected==1 else b'')+text(b)+(b'\x02' if selected==1 else b'')+b'\0'
 if kind=='status':
  a,b=labels;require(measure(a)<=61 and measure(b)<=52,'Status label exceeds numeric column')
  return text(a)+bytes.fromhex(row['middle_hex'])+text(b)+bytes.fromhex(row['end_hex']).replace(b'/',text('/'))+b'\0'
 raise ValueError(kind)

def add_ui(build,extra_catalog=None):
 catalog=json.loads(CATALOG.read_text());require(catalog['base_rom_sha256']==digest(build.original),'Dungeon UI base changed')
 if extra_catalog:
  extra=json.loads(extra_catalog.read_text());require(extra['base_rom_sha256']==digest(build.original),'Additional UI base changed')
  require(not {r['id'] for r in catalog['entries']}&{r['id'] for r in extra['entries']},'Duplicate additional UI identity')
  catalog['entries']+=extra['entries']
 rows=[]
 tables={0x140d68:bytearray(build.original[0x140d68:0x1417a0]),
         0x148080:bytearray(build.original[0x148080:0x148098]),
         0x148064:bytearray(build.original[0x148064:0x148074])}
 for row in catalog['entries']:
  source=row['source'];raw=bytes.fromhex(row['source_hex'])
  require(row['status']=='reviewed' and build.original[source:source+len(raw)]==raw and digest(raw)==row['source_sha256'],'Dungeon UI source/review changed')
  data=payload(row);offset=build.allocate(row['id'],data,OWNER)
  for site in row['pointers']:
   base=next(base for base,data in tables.items() if base<=site<base+len(data))
   require(struct.unpack_from('<I',tables[base],site-base)[0]==source+0x8000000,'Copied UI pointer changed')
   struct.pack_into('<I',tables[base],site-base,offset+0x8000000)
  rows.append(row|{'offset':offset,'encoded_hex':data.hex()})
 for base,sites in [(0x140d68,[0x19b2c,0x19bec,0x19c94,0x1a9f0,0x1aa74,0x1aaec]),
                    (0x148080,[0x1a650]),(0x148064,[0x1a698,0x1a6c0,0x1a6f4])]:
  offset=build.allocate(f'ui-table-{base:x}',bytes(tables[base]),OWNER)
  for site in sites:
   delta=8 if site==0x1a6f4 else 0
   build.patch(f'ui-consumer-{site:x}',site,struct.pack('<I',base+delta+0x8000000),struct.pack('<I',offset+delta+0x8000000),OWNER)
 # Formatted option rows stay within the 36 bytes exercised by the original map row.
 options={r['id']:bytes.fromhex(r['encoded_hex']) for r in rows if r['kind']=='option'}
 toggles=[r for r in rows if r['kind']=='toggle']
 for ident,raw in options.items():
  group=next(r['suffix'] for r in rows if r['id']==ident)
  for toggle in [bytes.fromhex(r['encoded_hex'])[:-1] for r in toggles if r['group']==group] if group else [b'']:
   result=raw.replace(b'%s',toggle).replace(b'%c',b'\x07')
   require(len(result)<=36,'Option output exceeds original observed extent')
 return {'entries':rows,'review_sha256':digest(CATALOG.read_bytes()),'options_max_bytes':36,'original_geometry':True,
         'additional_review_sha256':digest(extra_catalog.read_bytes()) if extra_catalog else None}
