"""Owned adventure-record rows and ranks with original right-aligned number fields."""
import json,re,struct
from tools.compact_font import encode,measure
from tools.extract_items import source
from tools.rom import ROOT,digest,require
CATALOG=ROOT/'translations/records-review.json'
TABLE=0x154520
RANKS=0x1545E0
LITERALS=(0x57754,0x57770,0x57788,0x577A0,0x577B8,0x577D0,0x577EC,0x57804,0x57814,0x57824,0x57834,0x57844,0x57854,0x57864,0x57884,0x57894,0x578A4,0x578BC,0x578D8)


def add_records(build):
    catalog=json.loads(CATALOG.read_text());entries=[]
    require(catalog['base_rom_sha256']==digest(build.original),'Records base differs')
    require({r['index'] for r in catalog['entries'] if r['kind']=='record'}==set(range(48)) and {r['index'] for r in catalog['entries'] if r['kind']=='rank'}==set(range(11)) and {r['literal'] for r in catalog['entries'] if r['kind']=='literal'}=={0x5744C,0x574F8,0x57500,0x575D0,0x57758},'Records cohort differs')
    table=bytearray(build.original[TABLE:TABLE+48*4]);ranks=bytearray(build.original[RANKS:RANKS+11*4])
    fields={'number':('d','32767'),'value':('s','2147483647G'),'level':('d','11'),'rank':('s',max((r['english'] for r in catalog['entries'] if r['kind']=='rank'),key=measure)),'hours':('d',str(2147483647//216000)),'minutes':('d','59')}
    for row in catalog['entries']:
        pointer=struct.unpack_from('<I',build.original,(TABLE if row['kind']=='record' else RANKS)+row['index']*4 if row['kind'] in ('record','rank') else row['literal'])[0]
        require(row['status']=='reviewed' and row['source']==source(build.original,pointer),'Records source/review differs')
        payload=bytearray();display='';size=1;kinds=''
        for part in re.split(r'(\{[^{}]+\})',row['english']):
            if part in ('{cyan}','{white}'):
                payload.extend(b'\x03\x05' if part=='{cyan}' else b'\x03\x07');size+=2
            elif part.startswith('{'):
                require(part[1:-1] in fields,'Unknown records field');kind,bound=fields[part[1:-1]];kinds+=kind
                payload.extend(b'%'+kind.encode());display+=bound;size+=len(bound)*(2 if kind=='s' and part!='{value}' else 1)
            else:
                require(not any(c in part for c in '{}%\r\n'),'Unexpected records control');value=encode(part)[:-1];payload.extend(value);display+=part;size+=len(value)
        source_kinds=b''.join(re.findall(rb'%l?([sd])',bytes.fromhex(row['source']['raw_hex']))).decode()
        require(source_kinds==kinds,'Records argument kinds differ')
        right_aligned=row['kind']=='record' and row['index']<8
        if right_aligned:
            # The native helper keeps numeric output against x224. Leave a
            # full glyph gap after the label at the widest native integer/G.
            require(measure(row['english'].replace('{value}',''))+6<=224-measure('2147483647G'),'Record label overlaps right-aligned value')
            size+=2 # preserved absolute-X control inside the value
        require(measure(display)<=224 and size<=128,'Records width/output capacity exceeded: '+row['id'])
        payload.append(0);offset=build.allocate(row['id'],bytes(payload),'records-text')
        if row['kind']=='record':struct.pack_into('<I',table,row['index']*4,offset+0x08000000)
        elif row['kind']=='rank':struct.pack_into('<I',ranks,row['index']*4,offset+0x08000000)
        else:build.patch(row['id']+'-literal',row['literal'],struct.pack('<I',pointer),struct.pack('<I',offset+0x08000000),'records-text')
        entries.append(row|{'offset':offset,'encoded_hex':payload.hex(),'maximum_width':224 if right_aligned else measure(display),'maximum_bytes':size,'capacity':128,'printf_kinds':kinds,'right_aligned':right_aligned})
    for name,data,literals,old in [('records-rows',table,LITERALS,TABLE),('records-ranks',ranks,(0x57450,0x574FC),RANKS)]:
        offset=build.allocate(name,bytes(data),'records-text')
        for literal in literals:build.patch(name+'-'+hex(literal),literal,struct.pack('<I',old+0x08000000),struct.pack('<I',offset+0x08000000),'records-text')
    return {'entries':entries,'review_sha256':digest(CATALOG.read_bytes()),'scope':catalog['scope']}
