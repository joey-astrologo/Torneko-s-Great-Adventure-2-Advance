"""The non-displaying monster identity format in original owner29EB8."""
import json,struct
from tools.rom import ROOT,digest,require
from tools.extract_shared_text import START,END,extract
from tools.compact_font import encode,measure
CATALOG=ROOT/'translations/monster-identity-review.json'
def add_monster_identity(build):
 c=json.loads(CATALOG.read_text());require(c['base_rom_sha256']==digest(build.original) and len(c['entries'])==1,'Monster identity catalog differs');e=c['entries'][0];src=next(r['source'] for r in extract()['entries'] if r['table_offset']==0x910);require(e['source']==src and e['status']=='reviewed' and e['english']=='This monster is\n{actor}.','Monster identity source/review differs');require(bytes.fromhex(src['raw_hex']).count(b'%s')==1,'Monster identity field differs');raw=encode('This monster is\n')[:-1]+b'%s'+encode('.');maximum=len(raw)+61;require(maximum<=256 and max(measure('This monster is'),186+measure('.'))<=216,'Monster identity capacity differs');at=build.allocate(e['id'],raw,'monster-identity');table=bytearray(build.original[START:END]);struct.pack_into('<I',table,0x910,at+0x08000000);private=build.allocate('monster-identity-table',bytes(table),'monster-identity');build.patch('monster-identity-reader',0x29F00,struct.pack('<I',START+0x08000000),struct.pack('<I',private+0x08000000),'monster-identity');return dict(entries=[e|dict(offset=at,encoded_hex=raw.hex(),capacity=256,field_capacity=64,maximum_bytes=maximum)],table_offset=private,catalog_sha256=digest(CATALOG.read_bytes()),scope=c['scope'])
