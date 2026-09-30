"""Translate the inscribed spellbook name without altering spell gameplay data."""
import json,struct
from tools.compact_font import encode,measure
from tools.extract_shared_text import START,END,extract
from tools.extract_spells import DEFINITIONS,COUNT
from tools.extract_items import source
from tools.rom import ROOT,digest,require
CATALOG=ROOT/'translations/spell-item-review.json'


def add_spell_item(build,spells):
    catalog=json.loads(CATALOG.read_text());original=build.original
    require(catalog['base_rom_sha256']==digest(original) and len(catalog['entries'])==2,'Spell item cohort differs')
    rows=[];table=bytearray(original[START:END])
    label,fmt=catalog['entries']
    require(label['table_offset']==0x84C and label['source']==next(r['source'] for r in extract()['entries'] if r['table_offset']==0x84C),'Spell item label source differs')
    require(fmt['source']==source(original,struct.unpack_from('<I',original,0xF2E8)[0]),'Spell item format source differs')
    require(all(r['status']=='reviewed' for r in catalog['entries']) and label['english']=='Sp.' and fmt['english']=='{kind} {spell}','Spell item review/argument ordering differs')
    for row,payload in [(label,encode(label['english'])),(fmt,b'\x03\x04%s'+encode(' ')[:-1]+b'%s\x05\0')]:
        at=build.allocate(row['id'],payload,'spell-item-text');rows.append(row|{'offset':at,'encoded_hex':payload.hex()})
    struct.pack_into('<I',table,0x84C,rows[0]['offset']+0x08000000)
    table_at=build.allocate('spell-item-private-table',bytes(table),'spell-item-text')
    definition=next(r for r in spells['copies'] if r['id']=='definitions');require(definition['size']==12*COUNT,'Spell item definition copy differs')
    names=[r for r in spells['entries'] if r['id'].startswith('spell.name.')]
    require({r['spell_id'] for r in names}==set(range(COUNT)),'Spell item name set incomplete')
    widths=[measure('Sp. '+r['english']) for r in names];sizes=[len(encode('Sp. '+r['english']))+3 for r in names]
    require(max(widths)<=116 and max(sizes)+21<=64,'Inscribed spell name exceeds base row reserve')
    for site,old,new in [(0xF2EC,START,table_at),(0xF2F4,DEFINITIONS,definition['offset']),(0xF2E8,fmt['source']['offset'],rows[1]['offset'])]:
        build.patch(f'spell-item-consumer-{site:x}',site,struct.pack('<I',old+0x08000000),struct.pack('<I',new+0x08000000),'spell-item-text')
    return {'entries':rows,'table_offset':table_at,'definition_copy_offset':definition['offset'],'catalog_sha256':digest(CATALOG.read_bytes()),'maximum_base_width':max(widths),'maximum_base_bytes':max(sizes),'maximum_complete_row_bytes':max(sizes)+21,'scope':catalog['scope']}
