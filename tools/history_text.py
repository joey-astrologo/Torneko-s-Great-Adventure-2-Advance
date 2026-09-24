"""Owned high-score labels and record-stat formats; original windows and records."""
import json,re,struct
from tools.compact_font import encode,measure
from tools.extract_items import source
from tools.rom import ROOT,digest,require
CATALOG=ROOT/'translations/history-review.json'
LITERALS={0x56E80,0x56F5C,0x56F68,0x56F6C,0x56F70,0x56FE0,0x571B8,0x571BC,0x571C4}


def add_history(build):
    catalog=json.loads(CATALOG.read_text());rows=[]
    require(catalog['base_rom_sha256']==digest(build.original) and {r['literal'] for r in catalog['entries']}==LITERALS,'History review coverage/base differs')
    bounds={'rank':50,'score':2147483647,'floor':32767,'hp':32767,'level':255,'strength':255,
            'exp':2147483647,'gold':2147483647,'trip':32767,'hours':2147483647//216000,'minutes':59}
    for row in catalog['entries']:
        original=struct.unpack_from('<I',build.original,row['literal'])[0]
        require(row['status']=='reviewed' and row['source']==source(build.original,original),'History literal source differs')
        original_fields=re.findall(rb'%[-0-9]*l?d',bytes.fromhex(row['source']['raw_hex']))
        require(len(original_fields)==len(row['fields']),'History argument count differs')
        payload,expanded,display,seen=bytearray(),bytearray(),'',[]
        for part in re.split(r'(\{[^{}]+\}|\n)',row['english']):
            if part in ('{white}','{cyan}'):
                value=b'\x03\x07' if part=='{white}' else b'\x03\x05'
                payload.extend(value);expanded.extend(value)
            elif part=='\n':payload.append(13);expanded.append(13)
            elif part.startswith('{'):
                field=part[1:-1];require(field in bounds,'Unknown history field');seen.append(field)
                value=str(bounds[field]);payload.extend(b'%d');expanded.extend(value.encode());display+=value
            else:
                require(not any(c in part for c in '{}%\r'),'Unexpected history control')
                encoded=encode(part)[:-1];payload.extend(encoded);expanded.extend(encoded);display+=part
        payload.append(0);expanded.append(0)
        require(seen==row['fields'] and len(expanded)<=128 and measure(display)<=row['budget'],'History field order/byte/pixel budget exceeded')
        offset=build.allocate(row['id'],bytes(payload),'history-text')
        build.patch(row['id']+'-literal',row['literal'],struct.pack('<I',original),struct.pack('<I',offset+0x08000000),'history-text')
        rows.append(row|{'offset':offset,'encoded_hex':payload.hex(),'maximum_bytes':len(expanded),
                         'maximum_width':measure(display),'capacity':128,'printf_kinds':'d'*len(seen)})
    return {'entries':rows,'review_sha256':digest(CATALOG.read_bytes()),'scope':catalog['scope']}
