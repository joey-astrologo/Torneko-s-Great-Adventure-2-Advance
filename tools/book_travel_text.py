"""Private legacy record-menu and travel confirmations."""
import json,struct
from tools.rom import ROOT,digest,require
from tools.compact_font import encode,measure
from tools.extract_items import source
CATALOG=ROOT/'translations/book-travel-review.json'
def add_book_travel(build):
 c=json.loads(CATALOG.read_text());require(c['base_rom_sha256']==digest(build.original),'Book/travel base differs');rows=[]
 for row in c['entries']:
  require(row['status']=='reviewed' and row['source']==source(build.original,row['source']['offset']+0x08000000),'Book/travel source differs')
  ident=row['id'];text=row['english'];require(text.count('{saved}')==int(ident=='travel.overwrite') and not any(c in text.replace('{saved}','') for c in '{}%'),'Book/travel substitutions differ');widths=[measure(line.replace('{saved}',''))+(112 if '{saved}' in line else 0) for line in text.split('\n')]
  if ident in ('book.records','book.scores','book.trade'):
   require(max(widths)<=66,'Legacy book cursor/label overflow');raw=b'\x06\x06'+encode(text)
  elif ident=='travel.choices':
   require(text=='Yes / No' and measure('Yes')<=26 and measure('No')<=42,'Travel choice columns overflow');raw=b'\x06\x06'+encode('Yes')[:-1]+b'\x06\x26'+encode('No')
  else:
   require(max(widths)<=(80 if ident=='travel.question' else 216) and len(widths)<=(1 if ident=='travel.question' else 2),'Book/travel modal overflow');raw=b'\r'.join(b'\x14'+encode(line).replace(encode('{saved}')[:-1],b'\x1f')[:-1] for line in text.split('\n'))+b'\0'
  at=build.allocate(ident,raw,'book-travel');rows.append(row|{'offset':at,'encoded_hex':raw.hex(),'line_widths':widths,'layout':{'pages':[text.split('\n')]}})
 by_id={r['id']:r for r in rows}
 table=b''.join(struct.pack('<I',by_id['book.'+key]['offset']+0x08000000) for key in ('records','scores','records','scores','trade'));at=build.allocate('book-travel-record-labels',table,'book-travel')
 for site,old,new in [(0x50AC4,0x0814D348,0x08000000+at+8),(0x50B1C,0x0814D340,0x08000000+at),(0x50B7C,0x0806C344,0x08000000+by_id['book.empty']['offset'])]:
  build.patch('book-travel-literal-'+hex(site),site,struct.pack('<I',old),struct.pack('<I',new),'book-travel')
 for ident,old,sites in [('travel.meadow',0x0814D70C,[0x5256C]),('travel.choices',0x0814D710,[0x52574,0x5271C]),('travel.overwrite',0x0814D714,[0x5263C]),('travel.question',0x0814BCE4,[0x52714])]:
  at=build.allocate(ident+'-private-pointer',struct.pack('<I',by_id[ident]['offset']+0x08000000),'book-travel')
  require(struct.unpack_from('<I',build.original,old-0x08000000)[0]==by_id[ident]['source']['offset']+0x08000000,'Book/travel original indirect source differs')
  for site in sites:build.patch('book-travel-literal-'+hex(site),site,struct.pack('<I',old),struct.pack('<I',at+0x08000000),'book-travel')
 return {'entries':rows,'catalog_sha256':digest(CATALOG.read_bytes()),'scope':c['scope']}
