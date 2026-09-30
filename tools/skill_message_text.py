"""Owned skill acquisition and attack announcements using complete English names."""
import json,re,struct
from tools.compact_font import encode,measure
from tools.extract_skills import DEFINITIONS,COUNT,STRIDE
from tools.extract_shared_text import START,END,extract
from tools.rom import ROOT,digest,require
CATALOG=ROOT/'translations/skill-messages-review.json'
TABLE_SITES={0x3BF64:0,0x3BF70:0x754,0x3DB18:0,0x3DC04:0x764,0x3DF9C:0x774}
NAME_SITES=(0x3BF74,0x3DB20,0x3DC08,0x3DFA0)


def add_skill_messages(build,skills):
    catalog=json.loads(CATALOG.read_text());sources={r['table_offset']:r['source'] for r in extract()['entries']}
    require(catalog['base_rom_sha256']==digest(build.original) and {r['table_offset'] for r in catalog['entries']}=={0x754,0x764,0x774,0x7E8,0x7EC,0x7F0},'Skill message source cohort differs')
    names=[r for r in skills['entries'] if r['kind']=='name'];require(len(names)==COUNT,'Skill message names incomplete')
    table=bytearray(build.original[START:END]);rows=[]
    for row in catalog['entries']:
        slot=row['table_offset'];text=row['english'];tokens=re.findall(r'\{[^}]+\}',text)
        require(row['source']==sources[slot] and row['status']=='reviewed' and tokens==(['{player}','{skill}'] if slot==0x754 else ['{skill}'] if slot in (0x764,0x774) else []),'Skill message review/fields differ')
        source=bytes.fromhex(row['source']['raw_hex']);require(source.count(b'%s')==tokens.count('{skill}') and (b'\x7e' in source)==(slot==0x754),'Skill message source arguments differ')
        payload=b''.join({'{player}':b'\x7e','\n':b'\r','{skill}':b'%s'}.get(p,encode(p)[:-1]) for p in re.split(r'(\n|\{[^}]+\})',text))
        if slot==0x754:
            require(source.endswith(b'\x09\0'),'Skill acquisition trailing control differs');payload+=b'\x09'
        payload+=b'\0'
        widths=[measure(p.replace('{player}','').replace('{skill}',''))+98*p.count('{player}')+max(measure(r['english']) for r in names)*p.count('{skill}') for p in text.split('\n')]
        maximum=len(payload)+max(len(bytes.fromhex(r['encoded_hex']))-3 for r in names)*tokens.count('{skill}')
        require(max(widths)<=216 and maximum<=256,'Skill message native budget exceeded')
        at=build.allocate(row['id'],payload,'skill-message-text');struct.pack_into('<I',table,slot,at+0x08000000)
        rows.append(row|{'offset':at,'encoded_hex':payload.hex(),'maximum_bytes':maximum,'maximum_segment_widths':widths,'capacity':256,'fields':['skill']*tokens.count('{skill}')})
    at=build.allocate('skill-messages-private-table',bytes(table),'skill-message-text')
    definitions=next(r for r in skills['copies'] if r['id']=='definitions');require(definitions['size']==COUNT*STRIDE,'Skill message definition copy differs')
    for site,shift in TABLE_SITES.items():build.patch(f'skill-message-table-{site:x}',site,struct.pack('<I',START+shift+0x08000000),struct.pack('<I',at+shift+0x08000000),'skill-message-text')
    for site in NAME_SITES:build.patch(f'skill-message-names-{site:x}',site,struct.pack('<I',DEFINITIONS+0x08000000),struct.pack('<I',definitions['offset']+0x08000000),'skill-message-text')
    return {'entries':rows,'table_offset':at,'definition_copy_offset':definitions['offset'],'catalog_sha256':digest(CATALOG.read_bytes()),'scope':catalog['scope']}
