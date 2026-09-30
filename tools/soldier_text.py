"""Private messages for the seven wounded-soldier object selectors."""
import json,struct
from tools.dialogue_layout import compile_dialogue
from tools.extract_shared_text import START,END,extract
from tools.rom import ROOT,digest,require
from tools.text_codec import tokenize
CATALOG=ROOT/'translations/soldier-review.json'
SLOTS=set(range(0x800,0x81C,4))


def add_soldiers(build):
    catalog=json.loads(CATALOG.read_text());sources={r['table_offset']:r['source'] for r in extract()['entries']}
    require(catalog['base_rom_sha256']==digest(build.original) and {r['table_offset'] for r in catalog['entries']}==SLOTS,'Soldier source cohort differs')
    table=bytearray(build.original[START:END]);entries=[]
    for row in catalog['entries']:
        require(row['status']=='reviewed' and row['source']==sources[row['table_offset']],'Soldier source/review differs')
        payload,layout=compile_dialogue(row['english'],tokenize(bytes.fromhex(row['source']['raw_hex']))[0])
        offset=build.allocate(row['id'],payload,'soldier-text');struct.pack_into('<I',table,row['table_offset'],offset+0x08000000)
        entries.append(row|{'offset':offset,'encoded_hex':payload.hex(),'layout':layout,'selector':(row['table_offset']-0x800)//4})
    offset=build.allocate('soldier-private-table',bytes(table),'soldier-text')
    build.patch('soldier-table',0x24378,struct.pack('<I',START+0x08000000),struct.pack('<I',offset+0x08000000),'soldier-text')
    return {'entries':entries,'table_offset':offset,'catalog_sha256':digest(CATALOG.read_bytes()),'consumer_literals':[0x24378],'scope':catalog['scope']}
