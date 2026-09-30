"""Owned skill Info sources, preserving skill mechanics and its native frame."""
import json,re,struct
from tools.compact_font import encode,measure,load_font
from tools.extract_skills import extract,DEFINITIONS,DESCRIPTIONS,COUNT,STRIDE
from tools.extract_shared_text import START,END
from tools.extract_items import source,DEFINITIONS as ITEMS
from tools.item_text import compile_description
from tools.rom import ROOT,digest,require

CATALOG=ROOT/'translations/skills-review.json'


def add_skill_info(build,items):
    catalog=json.loads(CATALOG.read_text());original=build.original;expected=extract()
    require(catalog['base_rom_sha256']==digest(original) and [r['id'] for r in catalog['entries']]==list(range(COUNT)),'Skill Info cohort differs')
    definitions=bytearray(original[DEFINITIONS:DEFINITIONS+COUNT*STRIDE]);descriptions=bytearray(original[DESCRIPTIONS:DESCRIPTIONS+4*COUNT]);table=bytearray(original[START:END]);entries=[];font=load_font()
    def allocate(ident,english,src,payload,**extra):
        require(source(original,src['offset']+0x08000000)==src,'Skill Info source bytes differ')
        offset=build.allocate(ident,payload,'skill-info');entries.append({'id':ident,'english':english,'source':src,'offset':offset,'encoded_hex':payload.hex(),**extra});return offset+0x08000000
    for row,src in zip(catalog['entries'],expected['entries']):
        require(row['status']=='reviewed' and row['bilingual_review'] and all(row[k]==v for k,v in src.items()),'Skill review/source definition differs')
        ident=row['id'];require(measure(row['name'],font)<=112 and len(encode(row['name']))<=49,'Skill name exceeds header reserve')
        name=allocate(f'skill.name.{ident}',row['name'],row['name_source'],encode(row['name']),skill_id=ident,kind='name')
        struct.pack_into('<I',definitions,ident*STRIDE,name)
        # The native body/footer inset is6px; leave the established8px right
        # margin within the224px window, giving210px for the body itself.
        require(len(row['description'].split('\n'))<=3 and all(measure(line,font)<=210 for line in row['description'].split('\n')),'Skill Info description exceeds inset region or overlaps assignment footer')
        text=compile_description(row['description'],row['description_source'])
        desc=allocate(f'skill.description.{ident}',row['description'],row['description_source'],text,skill_id=ident,kind='description')
        struct.pack_into('<I',descriptions,ident*4,desc)
    require({r['table_offset'] for r in catalog['ui_entries']}=={0x7B0,0x7C8,0x7B4,0x7B8,0x7BC,0x894,0x924,0x928},'Skill Info UI selection differs')
    labels={r['table_offset']:r['english'] for r in catalog['ui_entries']}
    for row in catalog['ui_entries']:
        slot=row['table_offset'];src=row['source'];text=row['english'];fields=re.findall(r'\{[^}]+\}',text)
        require(row['status']=='reviewed' and src==source(original,struct.unpack_from('<I',table,slot)[0]),'Skill Info UI source differs')
        payload=b''.join(b'%d' if p=='{cost}' else b'%s' if p in ('{skill}','{kind}','{item}') else encode(p)[:-1] for p in re.split(r'(\{[^}]+\})',text))+b'\0'
        require(re.findall(b'%[sd]',payload)==re.findall(b'%[sd]',bytes.fromhex(src['raw_hex'])),'Skill Info printf order differs')
        if slot in (0x7B0,0x7C8):
            require(fields==(['{skill}','{kind}','{cost}'] if slot==0x7B0 else ['{skill}','{kind}']),'Skill header fields differ')
            lines=[text.format(skill=r['name'],kind=labels[(0x7B4,0x7B8,0x7BC,0x894)[r['kind']]],cost=r['hunger_cost']) for r in catalog['entries'] if bool(r['hunger_cost'])==(slot==0x7B0)]
            widths=[measure(line,font) for line in lines];sizes=[len(encode(line)) for line in lines]
            extra={'kind':'header','maximum_width':max(widths),'maximum_bytes':max(sizes),'capacity':256}
        elif slot==0x924:
            require(fields==['{item}'],'Skill footer fields differ')
            extra={'kind':'footer','maximum_width':measure(text.replace('{item}',''),font)+80,'maximum_bytes':len(payload)+61,'capacity':256}
        else:
            require(not fields,'Unexpected skill label field');extra={'kind':'type' if slot!=0x928 else 'footer-label','maximum_width':measure(text,font),'maximum_bytes':len(payload),'capacity':256}
        require(extra['maximum_width']<=(216 if slot in (0x7B0,0x7C8) else 210) and extra['maximum_bytes']<=256,'Skill header/footer exceeds original output')
        pointer=allocate(row['id'],text,src,payload,table_offset=slot,**extra);struct.pack_into('<I',table,slot,pointer)
    literals={}
    for row in catalog['literal_entries']:
        require(row['status']=='reviewed','Skill literal unreviewed');payload=encode(row['english'])
        require(measure(row['english'],font)<=(80 if row['id']=='skill-info.multiple' else 216) and len(payload)<=64,'Skill literal exceeds assignment/footer budget')
        literals[row['id']]=allocate(row['id'],row['english'],row['source'],payload,kind='assignment-label')
    # The footer scans exactly48 equipment definitions. Reuse the already owned
    # English names in a private copy, without changing those original records.
    item_copy=bytearray(original[ITEMS:ITEMS+48*24]);names={int(r['id'].split('.')[-1]):r for r in items['entries'] if r['id'].startswith('item.name.')}
    require(set(range(48))<=names.keys(),'Skill footer equipment names incomplete')
    for ident in range(48):struct.pack_into('<I',item_copy,24*ident,names[ident]['offset']+0x08000000)
    copies=[]
    for ident,data,base,sites in [('definitions',definitions,DEFINITIONS,(0x2184C,)),('descriptions',descriptions,DESCRIPTIONS,(0x21854,)),('ui',table,START,(0x21850,0x21888)),('equipment',item_copy,ITEMS,(0x2185C,))]:
        offset=build.allocate('skill-info-'+ident,bytes(data),'skill-info')
        for site in sites:build.patch(f'skill-info-{ident}-{site:x}',site,struct.pack('<I',base+0x08000000),struct.pack('<I',offset+0x08000000),'skill-info')
        copies.append({'id':ident,'offset':offset,'source':base,'size':len(data),'literals':list(sites)})
    for site,ident in ((0x21864,'skill-info.multiple'),(0x218E4,'skill-info.unset-shield')):
        row=next(r for r in catalog['literal_entries'] if r['id']==ident)
        build.patch(ident+'-consumer',site,struct.pack('<I',row['source']['offset']+0x08000000),struct.pack('<I',literals[ident]),'skill-info')
    # Replace the fixed9-byte Japanese literal copy with the original strcpy.
    # Existing dest/src registers and64-byte scratch suffice; no frame growth.
    site=0x2182E;delta=0x5CF54-(site+4)
    call=struct.pack('<HH',0xF000|((delta>>12)&0x7FF),0xF800|((delta>>1)&0x7FF))
    build.patch('skill-info-multiple-complete-copy',site,bytes.fromhex('28c928c009780170'),call+bytes.fromhex('c046c046'),'skill-info')
    return {'entries':entries,'definitions':catalog['entries'],'copies':copies,'catalog_sha256':digest(CATALOG.read_bytes()),'scope':catalog['scope']}
