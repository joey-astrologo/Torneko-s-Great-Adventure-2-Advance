"""Owned remaining dungeon effects, with a checked staff-nullification buffer."""
import json,re,struct
from tools.compact_font import encode,measure
from tools.extract_shared_text import START,END,extract
from tools.inventory_action_text import CONTROL
from tools.rom import ROOT,digest,require
CATALOG=ROOT/'translations/dungeon-leaves-review.json'
# Only these original literal consumers are redirected. Some are separate
# readers of a shared source; original pointers elsewhere remain independent.
LITERALS={0x22CD4:{0x360},0xD1A8:{0x480},0xD9DC:{0x480},0x2FCC8:{0x480},0x3510C:{0x140,0x4B0,0x144},0x3514C:{0x9C4,0xC8},0x3536C:{0x160},0x353D8:{0x164,0x4B4},0x35424:{0x168},0x35BBC:{0x104},0x34358:{0x1F4},0x3779C:{0x1F4},0x37BCC:{0x400},0x37DE8:{0x640},0x36F34:{0x48C},0xBF7C:{0x48C},0xCDD0:{0x48C},0xD738:{0x48C},0x37310:{0x358},0x35AB8:{0x104,0x1FC,0xD4}}


def add_dungeon_leaves(build):
    catalog=json.loads(CATALOG.read_text());sources={r['table_offset']:r['source'] for r in extract()['entries']}
    require(catalog['base_rom_sha256']==digest(build.original) and {r['table_offset'] for r in catalog['entries']}=={0x104,0x140,0x160,0x164,0x168,0x1F4,0x358,0x400,0x48C,0x4B0,0x4B4,0x640,0x9C4,0x480,0x360},'Dungeon leaf sources differ')
    rows=[];table=bytearray(build.original[START:END]);bounds={'actor':186,'item':162,'result':162}
    for row in catalog['entries']:
        require(row['status']=='reviewed' and row['source']==sources[row['table_offset']],'Dungeon leaf source/review differs')
        text=row['english'];fields=re.findall(r'\{(actor|item|result)\}',text)
        require(fields==row['fields'] and text.count('{fit}')==1 and not re.search(r'[{}%\n\r]',re.sub(r'\{(?:actor|item|result|fit)\}','',text)),'Dungeon leaf fields/controls differ')
        payload=b''.join(CONTROL if p=='{fit}' else b'%s' if p.startswith('{') else encode(p)[:-1] for p in re.split(r'(\{[^}]+\})',text))+b'\0'
        require(re.findall(b'%[sd]',payload)==re.findall(b'%[sd]',bytes.fromhex(row['source']['raw_hex'])),'Dungeon leaf argument order differs')
        widths=[measure(re.sub(r'\{(?:actor|item|result)\}','',part))+sum(bounds[f]*part.count('{'+f+'}') for f in bounds) for part in text.split('{fit}')]
        maximum=len(payload)+61*len(fields)
        require(max(widths)<=216 and maximum<=256,'Dungeon leaf native budget exceeded')
        at=build.allocate(row['id'],payload,'dungeon-leaves');struct.pack_into('<I',table,row['table_offset'],at+0x08000000)
        rows.append(row|{'offset':at,'encoded_hex':payload.hex(),'maximum_bytes':maximum,'maximum_segment_widths':widths,'capacity':256})
    at=build.allocate('dungeon-leaves-private-table',bytes(table),'dungeon-leaves')
    for site in LITERALS:build.patch(f'dungeon-leaves-table-{site:x}',site,struct.pack('<I',START+0x08000000),struct.pack('<I',at+0x08000000),'dungeon-leaves')
    # CPU37D80..38434 uses only SP+0 for an outgoing fifth argument and SP+4
    # for this text. The complete linear listing contains no caller-stack reads.
    # Grow output64->256 while keeping every existing local offset unchanged.
    build.patch('staff-nullification-frame',0x37D86,bytes.fromhex('91b0'),bytes.fromhex('c1b0'),'dungeon-leaves')
    build.patch('staff-nullification-unframe',0x38428,bytes.fromhex('11b0'),bytes.fromhex('41b0'),'dungeon-leaves')
    return {'entries':rows,'table_offset':at,'literals':{str(k):sorted(v) for k,v in LITERALS.items()},'catalog_sha256':digest(CATALOG.read_bytes()),'staff_output_capacity':256,'scope':catalog['scope']}
