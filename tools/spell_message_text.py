"""Private spell casting/acquisition messages and name-table consumers."""
import json,re,struct
from tools.compact_font import encode,measure
from tools.extract_shared_text import START,END,extract
from tools.extract_spells import DEFINITIONS,COUNT
from tools.inventory_action_text import CONTROL
from tools.rom import ROOT,digest,require
CATALOG=ROOT/'translations/spell-messages-review.json'
LITERALS={0x41070:{0x920},0x411E0:{0x860,0x86C},0x3EF3C:{0x848},0x41B8C:{0x91C}}
DEFINITION_LITERALS=(0x41074,0x411E4,0x3EF38,0x41B94)


def add_spell_messages(build,spells):
    catalog=json.loads(CATALOG.read_text());sources={r['table_offset']:r['source'] for r in extract()['entries']}
    require(catalog['base_rom_sha256']==digest(build.original) and {r['table_offset'] for r in catalog['entries']}==set.union(*LITERALS.values()),'Spell message cohort differs')
    names=[r for r in spells['entries'] if r['kind']=='name'];require(len(names)==COUNT,'Spell message names incomplete')
    table=bytearray(build.original[START:END]);rows=[]
    for row in catalog['entries']:
        slot=row['table_offset'];text=row['english'];src=sources[slot];tokens=re.findall(r'\{[^}]+\}',text)
        expected=[] if slot==0x86C else ['{player}','{fit}','{spell}'] if slot==0x848 else ['{spell}']
        require(row['source']==src and row['status']=='reviewed' and tokens==expected,'Spell message review/arguments differ')
        require(bytes.fromhex(src['raw_hex']).count(b'%s')==tokens.count('{spell}'),'Spell message source arguments differ')
        payload=(b'\x14' if slot==0x91C else b'')+b''.join({'{player}':b'\x7e','{fit}':CONTROL,'{spell}':b'%s'}.get(p,encode(p)[:-1]) for p in re.split(r'(\{[^}]+\})',text))+b'\0'
        widths=[measure(p.replace('{player}','').replace('{spell}',''))+98*p.count('{player}')+max(measure(r['english']) for r in names)*p.count('{spell}') for p in text.split('{fit}')]
        maximum=len(payload)+max(len(bytes.fromhex(r['encoded_hex']))-3 for r in names)*tokens.count('{spell}')
        require(max(widths)<=216 and maximum<=256,'Spell message bounds exceeded')
        at=build.allocate(row['id'],payload,'spell-message-text');struct.pack_into('<I',table,slot,at+0x08000000)
        rows.append(row|{'offset':at,'encoded_hex':payload.hex(),'maximum_bytes':maximum,'maximum_segment_widths':widths,'capacity':256})
    at=build.allocate('spell-messages-private-table',bytes(table),'spell-message-text')
    definition=next(r for r in spells['copies'] if r['id']=='definitions');require(definition['size']==12*COUNT,'Spell message mechanics table differs')
    for site in LITERALS:build.patch(f'spell-message-table-{site:x}',site,struct.pack('<I',START+0x08000000),struct.pack('<I',at+0x08000000),'spell-message-text')
    for site in DEFINITION_LITERALS:build.patch(f'spell-message-definitions-{site:x}',site,struct.pack('<I',DEFINITIONS+0x08000000),struct.pack('<I',definition['offset']+0x08000000),'spell-message-text')
    return {'entries':rows,'table_offset':at,'definition_copy_offset':definition['offset'],'catalog_sha256':digest(CATALOG.read_bytes()),'scope':catalog['scope']}
