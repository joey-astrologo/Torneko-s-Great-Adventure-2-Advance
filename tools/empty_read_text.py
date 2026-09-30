import struct,json
from tools.compact_font import encode,measure
from tools.extract_items import source
from tools.rom import ROOT,digest,require
CATALOG=ROOT/'translations/empty-read-review.json'
def add_empty_read(build):
 c=json.loads(CATALOG.read_text());require(c['base_rom_sha256']==digest(build.original) and len(c['entries'])==1,'Empty-read catalog/base differs');row=c['entries'][0];english=row['english'];original=source(build.original,0x0806B550);require(row['status']=='reviewed' and row['source']==original and not any(c in english for c in '\n{}%'),'Empty-read source/format changed')
 raw=encode(english);require(measure(english)<=216,'Empty-read line exceeds window');at=build.allocate('empty-read',raw,'empty-read');build.patch('empty-read-owned-literal',0x17648,struct.pack('<I',0x0806B550),struct.pack('<I',at+0x08000000),'empty-read')
 return {'entries':[row|{'offset':at,'encoded_hex':raw.hex(),'layout':{'pages':[[english]]}}],'catalog_sha256':digest(CATALOG.read_bytes()),'scope':c['scope']}
