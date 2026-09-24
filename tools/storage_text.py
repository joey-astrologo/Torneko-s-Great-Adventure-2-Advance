"""Owned repaired-storage menu and observed transaction acknowledgements."""
import json,struct,re
from tools.compact_font import encode,measure
from tools.rom import ROOT,digest,require
from tools.town_text import entries,RELOCATION
CATALOG=ROOT/'translations/storage-review.json'

def compile_storage(row):
 text=row['english']
 if row['id']=='storage.menu':
  require(len(text)==8 and all(measure(s)<=100 for s in text),'Storage label exceeds its 100px column')
  payload=b'\r'.join(b'\x06\x0c'+encode(text[i])[:-1]+b'\x06\x7c'+encode(text[i+1])[:-1] for i in range(0,8,2))+b'\0'
  return payload,{'pages':[text],'native_width':224,'column_starts':[12,124],'column_budgets':[100,100],'native_rows':4,'direct_rom_stream':True}
 fields={'{amount}':(b'\x03\x05%d\x05',70,10),'{count}':(b'%d',21,3),'{item}':(b'%s',162,63)}
 pages=[p.split('\n') for p in text.split('\n\n')];widths=[];payload=bytearray();extra=0
 for n,lines in enumerate(pages):
  require(1<=len(lines)<=2,'Storage page needs one or two lines')
  values=[]
  for line in lines:
   plain=line
   reserve=0
   for marker,(_,width,_) in fields.items():
    reserve+=plain.count(marker)*width;plain=plain.replace(marker,'')
   require(not any(c in plain for c in '{}%'),'Unknown storage format field')
   values.append(measure(plain)+reserve)
  require(max(values)<=216,'Storage message exceeds expanded line budget')
  widths.append(values)
  for part in re.split(r'(\{amount\}|\{count\}|\{item\})','\n'.join(lines)):
   if part in fields:
    raw,_,maximum=fields[part];payload.extend(raw);extra+=maximum-2
   else:payload.extend(encode(part)[:-1])
  if n+1<len(pages):payload.extend(b'\r'*(3-len(lines)))
 payload.append(0);maximum=len(payload)+extra
 formatted=any(marker in text for marker in fields)
 require(not formatted or maximum<=256,'Storage format exceeds 256-byte buffer')
 return bytes(payload),{'pages':pages,'line_widths':widths,'native_width':224,
                        'direct_rom_stream':not formatted,'maximum_formatted_bytes':maximum,
                        'capacity':256 if formatted else None}

def insert_storage(build,decoded,bank):
 catalog=json.loads(CATALOG.read_text());require(catalog['base_rom_sha256']==digest(build.original),'Storage base differs')
 table={r['index']:r for r in entries()};rows=[];slots=[]
 for row in catalog['entries']:
  require(row['status']=='reviewed','Unreviewed storage resource')
  payload,layout=compile_storage(row);offset=build.allocate(row['id'],payload,'storage-services');owned=[]
  for index in row['indexes']:
   entry=table[index];raw=bank['data'][entry['start']:entry['end_exclusive']]
   require(raw.hex()==row['source_hex'] and digest(raw)==row['source_sha256'],'Storage source changed')
   require(re.findall(b'%[sdc]',raw)==re.findall(b'%[sdc]',payload),'Storage substitutions changed')
   slot=entry['slot'];require(struct.unpack_from('<I',decoded,slot)[0]==entry['linked_pointer'],'Storage slot already changed')
   struct.pack_into('<I',decoded,slot,(offset+0x8000000-RELOCATION)&0xffffffff);owned.append(slot);slots.append(slot)
  rows.append(row|{'offset':offset,'encoded_hex':payload.hex(),'layout':layout,'slots':owned})
 return rows,slots,digest(CATALOG.read_bytes())
