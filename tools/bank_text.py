"""Bank formats inserted through owned shared-town pointer slots."""
import json,struct,re
from tools.compact_font import encode,measure
from tools.dialogue_layout import PLAYER_WIDTH
from tools.rom import ROOT,require,digest
from tools.town_text import entries,RELOCATION

CATALOG=ROOT/'translations/bank-review.json'

def compile_bank(row):
 english=row['english']
 if row['index']==81:
  labels=english.split('\n');require(labels==['Deposit','Withdraw','Leave'],'Bank action order changed')
  require(all(measure(s+':')<=57 for s in labels[:2]),'Bank label/colon exceeds amount column')
  rows=[]
  for label in labels[:2]:rows.append(b'\x06\x0c'+encode(label+':')[:-1]+b'\x06\x45'+b'\x03\x05%d\x05'+encode('G max')[:-1])
  rows.append(b'\x06\x0c'+encode(labels[2])[:-1]);payload=b'\r'.join(rows)+b'\0'
  widths=[69+measure('G max')+56]*2+[12+measure(labels[2])]
  require(max(widths)<=176,'Bank amount column overflows')
  return payload,{'pages':[labels],'line_widths':[widths],'native_width':176,'maximum_formatted_bytes':len(payload)+12,'capacity':384}
 fields={'amount':(b'\x03\x05%d\x05',56,8),'count':(b'%d',21,3),'item':(b'%s',80,30),'player':(b'\x7e',PLAYER_WIDTH,1)}
 pages=[];payload=bytearray();widths=[]
 for paragraph in english.split('\n\n'):
  lines=paragraph.split('\n');require(1<=len(lines)<=2,'Bank page must have one or two lines')
  values=[]
  for line in lines:
   plain=line
   for field in fields:plain=plain.replace('{'+field+'}','')
   require('{' not in plain and '}' not in plain,'Unknown bank field')
   values.append(measure(plain)+sum(width*line.count('{'+field+'}') for field,(_,width,_) in fields.items()))
  require(max(values)<=216,'Bank prose exceeds width with eight digits')
  pages.append(lines);widths.append(values)
 for i,lines in enumerate(pages):
  joined='\n'.join(lines)
  for part in re.split(r'(\{(?:amount|count|item|player)\})',joined):
   payload.extend(fields[part[1:-1]][0] if part.startswith('{') else encode(part)[:-1].replace(b'%',b'%%'))
  if i+1<len(pages):payload.extend(b'\r'*(3-len(lines)))
 # Native reward code concatenates up to three copies into the same buffer.
 # Native rewards are one or three gifts. One compact line per gift gives
 # one/two pages without a trailing empty page; each fragment ends in one CR.
 if row['index']==91:
  require(len(pages)==1 and len(pages[0])==1,'Gift fragment must have one line')
  payload.extend(b'\r')
 payload.append(0)
 maximum=len(payload)+sum((capacity-(2 if name!='player' else 1))*english.count('{'+name+'}') for name,(_,_,capacity) in fields.items())
 if row['index']==91:require((maximum-1)*3+1<=384,'Three reward messages exceed bank buffer')
 require(maximum<=384,'Bank format exceeds stack capacity')
 return bytes(payload),{'pages':pages,'line_widths':widths,'native_width':224,'maximum_formatted_bytes':maximum,'capacity':384}

def insert_bank(build,decoded,bank):
 catalog=json.loads(CATALOG.read_text());require(catalog['base_rom_sha256']==digest(build.original),'Bank base differs')
 table={r['index']:r for r in entries()};rows=[];slots=[]
 for row in catalog['entries']:
  entry=table[row['index']];raw=bank['data'][entry['start']:entry['end_exclusive']]
  require(row['status']=='reviewed' and raw.hex()==row['source_hex'] and digest(raw)==row['source_sha256'],'Bank source/review stale')
  payload,layout=compile_bank(row)
  require(re.findall(b'%[sd]',raw)==re.findall(b'%[sd]',payload),'Bank substitutions changed')
  from tools.text_codec import tokenize
  require(sum(t.get('kind')=='command' and t.get('code')==0x7e for t in tokenize(raw)[0])==row['english'].count('{player}'),'Bank player substitution changed')
  offset=build.allocate(row['id'],payload,'bank-services');slot=entry['slot']
  require(struct.unpack_from('<I',decoded,slot)[0]==entry['linked_pointer'],'Bank slot already changed')
  replacement=(offset+0x8000000-RELOCATION)&0xffffffff
  struct.pack_into('<I',decoded,slot,replacement);slots.append(slot)
  rows.append(row|{'offset':offset,'encoded_hex':payload.hex(),'layout':layout,'slot':slot,'replacement':replacement})
 return rows,slots,digest(CATALOG.read_bytes())
