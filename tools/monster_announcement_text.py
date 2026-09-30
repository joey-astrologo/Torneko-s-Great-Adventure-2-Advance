"""Owned species-indexed special-action announcements in CPU0802A998."""
import json,re,struct
from tools.compact_font import encode,measure
from tools.extract_monsters import RESOURCE,DEFINITIONS,COUNT
from tools.extract_shared_text import START,END,extract
from tools.inventory_action_text import CONTROL
from tools.lz77 import decompress
from tools.rom import ROOT,digest,require
CATALOG=ROOT/'translations/monster-announcements-review.json'


def selectors(rom):
    data,_=decompress(rom,RESOURCE)
    return {i:struct.unpack_from('<h',data,DEFINITIONS+28*i+20)[0]*4 for i in range(COUNT)
            if struct.unpack_from('<h',data,DEFINITIONS+28*i+20)[0]}


def add_monster_announcements(build):
    catalog=json.loads(CATALOG.read_text());selected=selectors(build.original)
    sources={r['table_offset']:r['source'] for r in extract()['entries']}
    require(catalog['base_rom_sha256']==digest(build.original) and len(selected)==45 and len(set(selected.values()))==24 and
            {r['table_offset'] for r in catalog['entries']}==set(selected.values()),'Monster announcement selector/review cohort differs')
    table=bytearray(build.original[START:END]);entries=[]
    for row in catalog['entries']:
        require(row['status']=='reviewed' and row['source']==sources[row['table_offset']],'Monster announcement review/source differs')
        text=row['english'];parts=text.split('{fit}')
        require(len(parts)==2 and parts[0]=='{actor}' and parts[1].startswith(' ') and not any(c in parts[1] for c in '{}%\r\n'),'Unowned monster announcement shape')
        require(re.findall(b'%[sd]',bytes.fromhex(row['source']['raw_hex']))==[b'%s'],'Monster announcement arguments differ')
        payload=b'%s'+CONTROL+encode(parts[1]);widths=[186,measure(parts[1])];maximum=len(payload)+61
        require(max(widths)<=216 and maximum<=256,'Monster announcement exceeds native budgets')
        address=build.allocate(row['id'],payload,'monster-announcements');struct.pack_into('<I',table,row['table_offset'],address+0x08000000)
        entries.append(row|{'offset':address,'encoded_hex':payload.hex(),'maximum_line_widths':widths,'maximum_bytes':maximum,'capacity':256,'actor_capacity':64,'actor_ids':[i for i,s in selected.items() if s==row['table_offset']]})
    offset=build.allocate('monster-announcement-private-table',bytes(table),'monster-announcements')
    build.patch('monster-announcement-table',0x2AA54,struct.pack('<I',START+0x08000000),struct.pack('<I',offset+0x08000000),'monster-announcements')
    return {'entries':entries,'table_offset':offset,'catalog_sha256':digest(CATALOG.read_bytes()),'selectors':selected,'scope':catalog['scope']}
