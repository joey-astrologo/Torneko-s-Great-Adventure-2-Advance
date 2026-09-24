"""Owned two/three-row records menu, retaining its original64px window."""
import json,struct
from tools.compact_font import encode,measure
from tools.extract_items import source
from tools.rom import ROOT,digest,require
CATALOG=ROOT/'translations/history-menu-review.json'


def add_history_menu(build):
    catalog=json.loads(CATALOG.read_text());rows=[]
    require(catalog['base_rom_sha256']==digest(build.original),'History menu base differs')
    require({r['literal'] for r in catalog['entries']}=={0x56CA0,0x56D54},'History menu owners differ')
    for row in catalog['entries']:
        ptr=struct.unpack_from('<I',build.original,row['literal'])[0]
        require(row['status']=='reviewed' and row['source']==source(build.original,ptr),'History menu source differs')
        lines=row['english'].split('\n');expected=3 if row['literal']==0x56CA0 else 2
        require(len(lines)==expected and all(lines) and max(map(measure,lines))<=58,'History menu geometry exceeded')
        payload=b'\r'.join(encode(line)[:-1] for line in lines)+b'\0'
        offset=build.allocate(row['id'],payload,'history-menu')
        build.patch(row['id']+'-literal',row['literal'],struct.pack('<I',ptr),struct.pack('<I',offset+0x08000000),'history-menu')
        rows.append(row|{'offset':offset,'encoded_hex':payload.hex(),'line_widths':list(map(measure,lines)),
                         'window_width':64,'text_budget':58,'rows':expected})
    return {'entries':rows,'review_sha256':digest(CATALOG.read_bytes()),'scope':catalog['scope']}
