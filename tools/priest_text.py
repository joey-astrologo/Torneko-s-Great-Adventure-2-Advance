"""Private dungeon-priest dialogue/services, preserving prices and original panels."""
import json,re,struct
from tools.compact_font import encode,measure
from tools.dialogue_layout import compile_dialogue
from tools.extract_shared_text import START,END,extract
from tools.rom import ROOT,digest,require
from tools.text_codec import tokenize
CATALOG=ROOT/'translations/priest-review.json'
SLOTS={0x4C8,0x4CC,0x4D0,0x4D8,0x4DC,0x4E4,0x4E8,0x4EC,0x4F0,0x4F4,0x4F8,0x4FC,0x500,0x504,0x508,0x510,0x514,0x518,0x51C,0x520,0x9E4,0x9E8,0x9EC,0x9F0,0x9F4}
# The companion branch's separate1AB3C literal remains original.
LITERALS=(0x1AB8C,0x1AC30,0x1ADBC,0x1AE08,0x1AE94,0x1AF90,0x1B154,0x1B278,0x2467C,0x246B0,0x246F0)


def add_priest(build):
    catalog=json.loads(CATALOG.read_text());sources={r['table_offset']:r['source'] for r in extract()['entries']}
    require(catalog['base_rom_sha256']==digest(build.original) and {r['table_offset'] for r in catalog['entries']}==SLOTS,'Priest source cohort differs')
    table=bytearray(build.original[START:END]);entries=[]
    for row in catalog['entries']:
        slot=row['table_offset'];require(row['status']=='reviewed' and row['source']==sources[slot],'Priest review differs')
        source=bytes.fromhex(row['source']['raw_hex']);text=row['english']
        if slot==0x4DC:
            labels=text.split('\n');prices=(1200,300,500,50)
            require(len(labels)==4 and max(map(measure,labels))<=108,'Priest label overlaps price/cursor')
            require([struct.unpack_from('<h',build.original,a)[0] for a in (0x144B2A,0x144B26,0x144B28,0x144B24)]==list(prices),'Priest menu prices differ from native costs')
            payload=b'\r'.join(b'\x06\x0C'+encode(label)[:-1]+b'\x06\x80\x03\x05'+str(cost).encode()+b'\x05G' for label,cost in zip(labels,prices))+b'\0'
            layout={'pages':[labels],'line_widths':[list(map(measure,labels))],'native_width':184,'native_rows':4,'label_x':12,'label_budget':108,'price_x':128,'prices':list(prices),'direct_rom_stream':True}
        else:
            kinds=re.findall(b'%[sd]',source)
            require(kinds==([b'%d'] if '{amount}' in text else []),'Priest fields differ')
            require('99999' not in text,'Priest bound marker collision')
            payload,layout=compile_dialogue(text.replace('{amount}','99999'),tokenize(source.replace(b'%d',b'99999'))[0])
            if kinds:
                require(payload.count(encode('99999')[:-1])==1,'Priest field marker missing')
                payload=payload.replace(encode('99999')[:-1],b'%d')
                maximum=len(payload)+3
                require(maximum<=256,'Priest output exceeds original256bytes')
                layout|={'maximum_formatted_bytes':maximum,'capacity':256,'direct_rom_stream':False,'amount_bound':32767}
            else:layout['direct_rom_stream']=True
        offset=build.allocate(row['id'],payload,'priest-text');struct.pack_into('<I',table,slot,offset+0x08000000)
        entries.append(row|{'offset':offset,'encoded_hex':payload.hex(),'layout':layout})
    offset=build.allocate('priest-private-shared-table',bytes(table),'priest-text')
    for literal in LITERALS:build.patch(f'priest-table-{literal:x}',literal,struct.pack('<I',START+0x08000000),struct.pack('<I',offset+0x08000000),'priest-text')
    return {'entries':entries,'table_offset':offset,'catalog_sha256':digest(CATALOG.read_bytes()),'consumer_literals':list(LITERALS),'scope':catalog['scope']}
