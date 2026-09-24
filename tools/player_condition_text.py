"""Private player sleep, immobility and poison messages with bounded strength loss."""
import json,re,struct
from tools.rom import ROOT,digest,require
from tools.extract_shared_text import START,END,extract
from tools.compact_font import encode,measure
from tools.dialogue_layout import PLAYER_WIDTH

CATALOG=ROOT/'translations/player-conditions-review.json'
OWNERS={0xB3A0:(0x11C,),0xB3C0:(0xF0,),0xB3F4:(0x4A8,),0xB434:(0x1F0,0x88C),
        0xB264:(0x204,),0xB280:(0x2FC,),0xB2EC:(0x298,),0xB36C:(0xDC,)}

def add_conditions(build):
    catalog=json.loads(CATALOG.read_text());allowed={n for ns in OWNERS.values() for n in ns}
    require(catalog['base_rom_sha256']==digest(build.original),'Player-condition base differs')
    require(len(catalog['entries'])==len(allowed) and {r['table_offset'] for r in catalog['entries']}==allowed,
            'Unowned player-condition selection')
    sources={r['table_offset']:r['source'] for r in extract()['entries']};table=bytearray(build.original[START:END]);rows=[]
    for row in catalog['entries']:
        source=sources[row['table_offset']];text=row['english']
        require(row['status']=='reviewed' and row['source']==source,'Player-condition source/review differs')
        plain=text.replace('{player}','').replace('{value}','')
        require(not any(c in plain for c in '{}%\n\r'),'Unowned player-condition format')
        require(text.count('{value}')==(1 if row['table_offset']==0xDC else 0),'Unowned numeric condition')
        payload=b''.join(b'%s' if p=='{player}' else b'%d' if p=='{value}' else encode(p)[:-1]
                         for p in re.split(r'(\{player\}|\{value\})',text))+b'\0'
        require(re.findall(b'%[sd]',bytes.fromhex(source['raw_hex']))==re.findall(b'%[sd]',payload),
                'Player-condition arguments changed')
        width=measure(plain)+text.count('{player}')*PLAYER_WIDTH+text.count('{value}')*6
        maximum=len(payload)+text.count('{player}')*12-text.count('{value}')
        require(width<=216 and maximum<=256,'Player condition exceeds single-line/native buffer budget')
        offset=build.allocate(row['id'],payload,'player-conditions')
        struct.pack_into('<I',table,row['table_offset'],offset+0x08000000)
        rows.append(row|{'offset':offset,'encoded_hex':payload.hex(),'maximum_width':width,
                         'maximum_bytes':maximum,'capacity':256,'numeric_bound':[1,3] if '{value}' in text else None})
    offset=build.allocate('player-conditions-table',bytes(table),'player-conditions')
    for site in OWNERS:
        build.patch(f'player-condition-consumer-{site:x}',site,struct.pack('<I',START+0x08000000),
                    struct.pack('<I',offset+0x08000000),'player-conditions')
    return {'entries':rows,'table_offset':offset,'consumer_literals':list(OWNERS),'catalog_sha256':digest(CATALOG.read_bytes()),
            'scope':'Private player reads in B374/B3C4/B3F8/B240. Existing 256-byte buffers. Strength loss is native before-minus-after: one or three with zero clamp, hence 1..3 for valid positive signed16 strength. No shared/global source replacement; controlled consumer proof required.'}
