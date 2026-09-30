"""Private refusal text for the two actor-talk blocks in CPU08023C14."""
import json,struct
from tools.rom import ROOT,digest,require
from tools.compact_font import encode,measure
from tools.extract_shared_text import START,extract
CATALOG=ROOT/'translations/cannot-talk-review.json'
def add_cannot_talk(build):
 c=json.loads(CATALOG.read_text());row=c['entries'][0];src=next(r['source'] for r in extract()['entries'] if r['table_offset']==0x950)
 require(c['base_rom_sha256']==digest(build.original) and len(c['entries'])==1 and row['status']=='reviewed' and row['source']==src,'Talk refusal source/review differs')
 require(row['english']=="{actor}\ncan't talk.",'Unreviewed talk refusal shape')
 raw=b'%s\r'+encode("can't talk.");maximum=len(raw)+61;require(maximum<=256 and measure("can't talk.")<=216,'Talk refusal buffer/window exceeded')
 at=build.allocate(row['id'],raw,'cannot-talk');ptr=build.allocate('cannot-talk-pointer',struct.pack('<I',at+0x08000000),'cannot-talk')
 build.patch('cannot-talk-reader',0x23DA8,struct.pack('<I',START+0x950+0x08000000),struct.pack('<I',ptr+0x08000000),'cannot-talk')
 return {'entries':[row|{'offset':at,'encoded_hex':raw.hex(),'maximum_bytes':maximum,'maximum_line_widths':[186,measure("can't talk.")],'capacity':256}],'catalog_sha256':digest(CATALOG.read_bytes()),'scope':c['scope']}
