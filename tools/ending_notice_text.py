import json,struct
from tools.rom import ROOT,digest,require
from tools.extract_items import source
from tools.compact_font import encode,measure
CATALOG=ROOT/'translations/ending-notice-review.json'
def add_ending_notice(build):
 c=json.loads(CATALOG.read_text());require(c['base_rom_sha256']==digest(build.original) and len(c['entries'])==1,'Ending notice cohort differs');e=c['entries'][0];require(e['status']=='reviewed' and e['source']==source(build.original,0x0806CF38),'Ending notice source differs');text=e['english'];require(not any(x in text for x in '\n{}%@') and measure(text)<=216,'Ending notice native line budget exceeded');raw=encode(text);at=build.allocate(e['id'],raw,'ending-notice');build.patch('ending-notice-reader',0x54F1C,struct.pack('<I',0x0806CF38),struct.pack('<I',at+0x08000000),'ending-notice')
 return {'entries':[e|{'offset':at,'encoded_hex':raw.hex(),'layout':{'pages':[[text]],'line_widths':[[measure(text)]],'maximum_width':216}}],'catalog_sha256':digest(CATALOG.read_bytes()),'scope':c['scope']}
