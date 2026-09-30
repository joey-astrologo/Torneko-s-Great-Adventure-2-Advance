"""Private Blank-scroll and Spellbook writing success/refusal messages."""
import json,re,struct
from tools.compact_font import encode,measure
from tools.extract_shared_text import START,END,extract
from tools.extract_items import DEFINITIONS as ITEMS
from tools.extract_spells import DEFINITIONS as SPELLS
from tools.inventory_action_text import CONTROL
from tools.rom import ROOT,digest,require
CATALOG=ROOT/'translations/writing-review.json'
LITERALS={0x26A64:{0x440},0x26ABC:{0x444},0x26ADC:{0x6E8},0x26B04:{0x854},0x26B50:{0x858},0x26B88:{0x85C}}

def add_writing(build,items,spells):
    catalog=json.loads(CATALOG.read_text());sources={r['table_offset']:r['source'] for r in extract()['entries']}
    require(catalog['base_rom_sha256']==digest(build.original) and {r['table_offset'] for r in catalog['entries']}==set.union(*LITERALS.values()),'Writing cohort differs')
    names={'item':[r for r in items['entries'] if r['id'].startswith('item.name.') and 116<=int(r['id'].rsplit('.',1)[1])<=152], 'spell':[r for r in spells['entries'] if r['id'].startswith('spell.name.')]}
    bounds={k:(max(measure(r['english']) for r in v),max(len(bytes.fromhex(r['encoded_hex']))-1 for r in v)) for k,v in names.items()}
    rows=[];table=bytearray(build.original[START:END])
    for row in catalog['entries']:
        text=row['english'];fields=row['fields'];tokens=re.findall(r'\{([^}]+)\}',text)
        require(row['status']=='reviewed' and row['source']==sources[row['table_offset']] and [t for t in tokens if t!='fit']==fields,'Writing source/review/fields differ')
        payload=b''.join(CONTROL if p=='{fit}' else b'%s' if p.startswith('{') else encode(p)[:-1] for p in re.split(r'(\{[^}]+\})',text))+b'\0'
        maximum=len(payload)+sum(bounds[f][1]-2 for f in fields)
        widths=[measure(re.sub(r'\{[^}]+\}','',p))+sum(bounds[f][0]*p.count('{'+f+'}') for f in fields) for p in re.split(r'\{fit\}|\n',text)]
        require(re.findall(b'%[sd]',bytes.fromhex(row['source']['raw_hex']))==[b'%s']*len(fields) and maximum<=256 and max(widths)<=216,'Writing pixel/byte bounds exceeded')
        at=build.allocate(row['id'],payload,'writing-text');struct.pack_into('<I',table,row['table_offset'],at+0x08000000);rows.append(row|{'offset':at,'encoded_hex':payload.hex(),'maximum_bytes':maximum,'maximum_segment_widths':widths,'capacity':256})
    at=build.allocate('writing-private-table',bytes(table),'writing-text')
    for site in LITERALS:build.patch(f'writing-table-{site:x}',site,struct.pack('<I',START+0x08000000),struct.pack('<I',at+0x08000000),'writing-text')
    item_copy=next(r for r in build.allocations if r['id']=='item-definitions')['start'];spell_copy=next(r for r in spells['copies'] if r['id']=='definitions')['offset']
    for site,old,new in [(0x26AC4,ITEMS,item_copy),(0x26B58,SPELLS,spell_copy)]:build.patch(f'writing-name-definitions-{site:x}',site,struct.pack('<I',old+0x08000000),struct.pack('<I',new+0x08000000),'writing-text')
    return {'entries':rows,'table_offset':at,'item_copy_offset':item_copy,'spell_copy_offset':spell_copy,'catalog_sha256':digest(CATALOG.read_bytes()),'field_bounds':bounds,'scope':catalog['scope']}
