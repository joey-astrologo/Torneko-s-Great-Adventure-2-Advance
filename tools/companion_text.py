"""Private, floor-selected baker companion conversations in the priest dispatcher."""
import json
import struct
from tools.dialogue_layout import compile_dialogue
from tools.extract_shared_text import START,END,extract
from tools.rom import ROOT,digest,require
from tools.text_codec import tokenize

CATALOG=ROOT/'translations/companion-review.json'
SLOTS=set(range(0x780,0x798,4))


def add_companion(build):
    catalog=json.loads(CATALOG.read_text());sources={r['table_offset']:r['source'] for r in extract()['entries']}
    require(catalog['base_rom_sha256']==digest(build.original) and {r['table_offset'] for r in catalog['entries']}==SLOTS,'Companion source cohort differs')
    require(struct.unpack_from('<II',build.original,0x1AB40)==(0x02005674,0x1DF),'Companion floor selector changed')
    table=bytearray(build.original[START:END]);entries=[]
    for row in catalog['entries']:
        require(row['status']=='reviewed' and row['source']==sources[row['table_offset']],'Companion source/review differs')
        payload,layout=compile_dialogue(row['english'],tokenize(bytes.fromhex(row['source']['raw_hex']))[0])
        offset=build.allocate(row['id'],payload,'companion-text');struct.pack_into('<I',table,row['table_offset'],offset+0x08000000)
        entries.append(row|{'offset':offset,'encoded_hex':payload.hex(),'layout':layout,'floor':(row['table_offset']-0x77C)//4})
    offset=build.allocate('companion-private-shared-table',bytes(table),'companion-text')
    build.patch('companion-table',0x1AB3C,struct.pack('<I',START+0x08000000),struct.pack('<I',offset+0x08000000),'companion-text')
    return {'entries':entries,'table_offset':offset,'catalog_sha256':digest(CATALOG.read_bytes()),'consumer_literals':[0x1AB3C],'scope':catalog['scope']}
