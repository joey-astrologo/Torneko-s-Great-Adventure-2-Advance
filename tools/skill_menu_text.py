"""Private warrior selection, equipped-skill previews and Set confirmation."""
import json,re,struct
from tools.compact_font import encode,measure,load_font
from tools.extract_shared_text import START,END
from tools.extract_skills import DEFINITIONS
from tools.extract_items import source,DEFINITIONS as ITEMS
from tools.rom import ROOT,digest,require
CATALOG=ROOT/'translations/skill-menu-review.json'
DEFINITION_SITES=(0x21134,0x213B8,0x2155C,0x21598,0x215F0,0x21B18,0x21D60,0x21DF4,0x21E18)
TABLE_SITES=(0x2105C,0x21288,0x213B0,0x21508,0x2159C,0x215F8,0x216D4,0x21D64,0x21DEC)


def add_skill_menu(build,info):
    catalog=json.loads(CATALOG.read_text());rom=build.original;font=load_font()
    require(catalog['base_rom_sha256']==digest(rom),'Skill menu base differs')
    require({r['table_offset'] for r in catalog['entries'] if r['table_offset'] is not None}=={0x914,0x89C,0x8A0,0x8A4,0x8A8,0x8AC,0x8B0,0x74C,0x730,0x734,0x738,0x7C4,0x7C0,0x7CC,0x92C,0x960} and len(catalog['entries'])==19,'Skill menu source cohort differs')
    table=bytearray(rom[START:END]);entries=[]
    tokens={'{colour}':b'\x03%c','{grey}':b'\x03\x02','{reset}':b'\x05','{marker}':b'%s','{skill}':b'%s','{item}':b'%s','{cost}':b'%d'}
    for row in catalog['entries']:
        text=row['english'];src=row['source'];slot=row['table_offset'];kind=row['kind']
        require(row['status']=='reviewed' and source(rom,src['offset']+0x08000000)==src,'Skill menu source/review differs')
        require(not set(re.findall(r'\{[^}]+\}',text))-tokens.keys(),'Unknown skill menu field')
        payload=b''.join(tokens[p] if p in tokens else encode(p)[:-1] for p in re.split(r'(\{[^}]+\})',text))+b'\0'
        require(re.findall(b'%[csd]',payload)==re.findall(b'%[csd]',bytes.fromhex(src['raw_hex'])),'Skill menu argument order differs')
        if kind in ('list-row','equipment-row'):
            cap=64 if kind=='list-row' else 256;budget=156 if kind=='list-row' else 148
            bounds=[]
            for definition in info['definitions']:
                if slot==0x7C0 and not definition['hunger_cost']:continue
                if slot==0x7CC and definition['hunger_cost']:continue
                display=text.replace('{skill}',definition['name']).replace('{cost}',str(definition['hunger_cost']))
                width=measure(re.sub(r'\{[^}]+\}','',display),font)+(14 if '{marker}' in text else 0)
                size=len(payload)+len(encode(definition['name']))-3
                if '{marker}' in text:size+=0 # two-byte marker replaces two-byte%s
                if '{colour}' in text:size-=1
                if '{cost}' in text:size+=len(str(definition['hunger_cost']))-2
                require(width<=budget and size<=cap,'Skill list name/cost exceeds original region')
                bounds.append({'skill':definition['id'],'width':width,'bytes':size})
            extra={'capacity':cap,'text_budget':budget,'bounds':bounds}
        else:
            cap=256
            replacements={'{skill}':'','{item}':'','{cost}':'765','{grey}':'','{reset}':''}
            lines=text.split('\n');widths=[]
            for line in lines:
                base=line
                for token,value in replacements.items():base=base.replace(token,value)
                widths.append(measure(base,font)+112*line.count('{skill}')+80*line.count('{item}'))
            budget=42 if kind=='selector' else 34 if kind=='action' else 216 if kind in ('confirmation','message') else 156
            require(max(widths)<=budget,'Skill selector/header/action exceeds native width')
            require(len(payload)+(49-2)*text.count('{skill}')+(31-2)*text.count('{item}')+text.count('{cost}')<=cap,'Skill menu output exceeds native bytes')
            extra={'capacity':cap,'text_budget':budget,'line_widths':widths}
        offset=build.allocate(row['id'],payload,'skill-menu');entries.append(row|{'offset':offset,'encoded_hex':payload.hex(),**extra})
        if slot is not None:
            require(struct.unpack_from('<I',table,slot)[0]==src['offset']+0x08000000,'Skill menu pointer selection differs')
            struct.pack_into('<I',table,slot,offset+0x08000000)
    table_at=build.allocate('skill-menu-private-table',bytes(table),'skill-menu')
    copies={r['id']:r['offset'] for r in info['copies']}
    for site in DEFINITION_SITES:build.patch(f'skill-menu-definitions-{site:x}',site,struct.pack('<I',DEFINITIONS+0x08000000),struct.pack('<I',copies['definitions']+0x08000000),'skill-menu')
    for site in TABLE_SITES:build.patch(f'skill-menu-table-{site:x}',site,struct.pack('<I',START+0x08000000),struct.pack('<I',table_at+0x08000000),'skill-menu')
    build.patch('skill-menu-confirm-equipment',0x213BC,struct.pack('<I',ITEMS+0x08000000),struct.pack('<I',copies['equipment']+0x08000000),'skill-menu')
    for site,ident in ((0x21DF8,'available'),(0x21E1C,'disabled'),(0x21E38,'disabled'),(0x21E58,'disabled'),(0x215F4,'equipment-disabled')):
        row=next(r for r in entries if r['id']=='skill-menu.'+ident)
        build.patch(f'skill-menu-format-{site:x}',site,struct.pack('<I',row['source']['offset']+0x08000000),struct.pack('<I',row['offset']+0x08000000),'skill-menu')
    return {'entries':entries,'table_offset':table_at,'definition_copy_offset':copies['definitions'],'catalog_sha256':digest(CATALOG.read_bytes()),'scope':catalog['scope']}
