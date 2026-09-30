"""Spell Info's owned table copies; mechanics and other consumers stay original."""
import json,re,struct
from tools.compact_font import encode,measure,load_font
from tools.extract_spells import extract,DEFINITIONS,DESCRIPTIONS,COUNT
from tools.extract_shared_text import START,END
from tools.extract_items import source
from tools.item_text import compile_description
from tools.rom import ROOT,digest,require

CATALOG=ROOT/'translations/spells-review.json'


def add_spell_info(build):
    catalog=json.loads(CATALOG.read_text());original=build.original
    sources=extract();require(catalog['base_rom_sha256']==digest(original) and
                             [r['id'] for r in catalog['entries']]==list(range(COUNT)),'Spell source cohort differs')
    definitions=bytearray(original[DEFINITIONS:DESCRIPTIONS])
    descriptions=bytearray(original[DESCRIPTIONS:DESCRIPTIONS+4*COUNT])
    table=bytearray(original[START:END]);entries=[];font=load_font()
    def allocate(ident,english,src,payload,**extra):
        require(source(original,src['offset']+0x08000000)==src,'Spell source bytes differ')
        offset=build.allocate(ident,payload,'spell-info')
        entries.append({'id':ident,'english':english,'source':src,'offset':offset,'encoded_hex':payload.hex(),**extra})
        return offset+0x08000000
    for row,expected in zip(catalog['entries'],sources['entries']):
        require(row['status']=='reviewed' and all(row[k]==v for k,v in expected.items()),'Spell definition/review differs')
        i=row['id'];name=encode(row['name'])
        require(measure(row['name'],font)<=90 and len(name)<=41,'Spell Info name reserve exceeded')
        pointer=allocate(f'spell.name.{i}',row['name'],row['name_source'],name,spell_id=i,kind='name')
        struct.pack_into('<I',definitions,12*i,pointer)
        payload=compile_description(row['description'],row['description_source'])
        pointer=allocate(f'spell.description.{i}',row['description'],row['description_source'],payload,spell_id=i,kind='description')
        struct.pack_into('<I',descriptions,4*i,pointer)
    require({r['table_offset'] for r in catalog['ui_entries']}=={0x840}|set(range(0x8BC,0x8E0,4)),'Spell Info UI cohort differs')
    for row in catalog['ui_entries']:
        slot=row['table_offset'];text=row['english'];src=row['source']
        require(row['status']=='reviewed' and src==source(original,struct.unpack_from('<I',table,slot)[0]),'Spell Info UI source differs')
        if slot==0x840:
            require(re.findall(r'\{[^}]+\}',text)==['{spell}','{cost}','{target}'] and
                    re.findall(b'%[sd]',bytes.fromhex(src['raw_hex']))==[b'%s',b'%d',b'%s'],'Spell header arguments differ')
            payload=b''.join({'{spell}':b'%s','{cost}':b'%d','{target}':b'%s'}.get(p,encode(p)[:-1]) for p in re.split(r'(\{spell\}|\{cost\}|\{target\})',text))+b'\0'
            widths=[];sizes=[]
            targets={r['table_offset']:r['english'] for r in catalog['ui_entries']}
            for spell in catalog['entries']:
                line=text.replace('{spell}',spell['name']).replace('{cost}',str(spell['hp_cost'])).replace('{target}',targets[0x8BC+4*spell['target_kind']])
                widths.append(measure(line,font));sizes.append(len(encode(line)))
            require(max(widths)<=216 and max(sizes)<=256,'Native spell Info header exceeds line/buffer')
            extra={'kind':'format','maximum_width':max(widths),'maximum_bytes':max(sizes),'capacity':256}
        else:
            payload=encode(text);require(measure(text,font)<=48 and len(payload)<=21,'Spell target label exceeds reserve');extra={'kind':'target'}
        pointer=allocate(row['id'],text,src,payload,**extra);struct.pack_into('<I',table,slot,pointer)
    copies=[]
    for ident,data,base,site in [('definitions',definitions,DEFINITIONS,0x228D0),('descriptions',descriptions,DESCRIPTIONS,0x228D8),('ui',table,START,0x228CC)]:
        offset=build.allocate('spell-info-'+ident,bytes(data),'spell-info')
        build.patch('spell-info-'+ident+'-consumer',site,struct.pack('<I',base+0x08000000),struct.pack('<I',offset+0x08000000),'spell-info')
        copies.append({'id':ident,'offset':offset,'source':base,'size':len(data),'literal':site})
    return {'entries':entries,'definitions':catalog['entries'],'catalog_sha256':digest(CATALOG.read_bytes()),'copies':copies,'scope':catalog['scope']}
