"""Owned spell selection/action menus, sharing the reviewed Info names/targets."""
import json,re,struct
from tools.compact_font import encode,measure,load_font
from tools.extract_spells import DEFINITIONS,COUNT
from tools.extract_shared_text import START,END
from tools.extract_items import source
from tools.rom import ROOT,digest,require

CATALOG=ROOT/'translations/spell-menu-review.json'


def add_spell_menu(build,info):
    catalog=json.loads(CATALOG.read_text());rom=build.original;font=load_font()
    require(catalog['base_rom_sha256']==digest(rom),'Spell menu base differs')
    source_rows={r['id']:r for r in info['entries']}
    # The original lookup bounds its search at128, although only61 records are
    # spell definitions. Preserve the exact adjacent bytes in this private read
    # window; never invent further records or call the original tail free space.
    definitions=bytearray(rom[DEFINITIONS:DEFINITIONS+128*12])
    table=bytearray(rom[START:END]);entries=[]
    for row in info['entries']:
        if row['kind']=='name':struct.pack_into('<I',definitions,row['spell_id']*12,row['offset']+0x08000000)
        elif row['kind']=='target':struct.pack_into('<I',table,int(row['id'].split('.')[-1],16),row['offset']+0x08000000)
    for row in catalog['entries']:
        text=row['english'];src=row['source'];slot=row.get('table_offset')
        require(row['status']=='reviewed' and source(rom,src['offset']+0x08000000)==src,'Spell menu source/review differs')
        if slot is not None:require(struct.unpack_from('<I',rom,START+slot)[0]==src['offset']+0x08000000,'Spell menu slot differs')
        tokens={'{colour}':b'\x03%c','{grey}':b'\x03\x02','{reset}':b'\x05','{marker}':b'%s','{spell}':b'%s','{target}':b'%s'}
        require(not set(re.findall(r'\{[^}]+\}',text))-tokens.keys(),'Unknown spell menu control')
        payload=b''.join(tokens[p] if p in tokens else encode(p)[:-1] for p in re.split(r'(\{[^}]+\})',text))+b'\0'
        require(re.findall(b'%[csd]',payload)==re.findall(b'%[csd]',bytes.fromhex(src['raw_hex'])),'Spell menu argument order differs')
        if slot in (0x83C,0x844):
            widths=[measure(re.sub(r'\{[^}]+\}','',line),font) for line in text.split('\n')]
            require(len(widths)==3 and max(widths)<=34 and len(payload)<=256,'Spell action rows exceed original budgets')
            extra={'capacity':256,'line_widths':widths,'kind':'action'}
        elif slot==0x74C:
            require(measure(text,font)<=156 and len(payload)<=64,'Unlearned spell label exceeds row')
            extra={'kind':'unlearned'}
        else:
            bounds=[]
            for definition in info['definitions']:
                name=definition['name'];target=source_rows[f"spell-info.{0x8BC+4*definition['target_kind']:03x}"]['english']
                display=name+(' ['+target+']' if row['id'].endswith('.available') else '')
                # Native marker field is at most one two-byte marker glyph.
                width=14+measure(display,font);size=len(payload)+2+len(encode(name))-3
                if row['id'].endswith('.available'):size+=len(encode(target))-3
                require(width<=156 and size<=64,'Spell list row exceeds original text/buffer region')
                bounds.append({'spell':definition['id'],'width':width,'bytes':size})
            extra={'capacity':64,'kind':'list-format','bounds':bounds}
        offset=build.allocate(row['id'],payload,'spell-menu');entries.append(row|{'offset':offset,'encoded_hex':payload.hex(),**extra})
        if slot is not None:struct.pack_into('<I',table,slot,offset+0x08000000)
    table_at=build.allocate('spell-menu-private-table',bytes(table),'spell-menu')
    definitions_at=build.allocate('spell-menu-private-lookup',bytes(definitions),'spell-menu')
    for site in (0x225C8,0x22600):build.patch(f'spell-menu-definitions-{site:x}',site,struct.pack('<I',DEFINITIONS+0x08000000),struct.pack('<I',definitions_at+0x08000000),'spell-menu')
    for site,inner in ((0x225D8,0),(0x2261C,0x74C),(0x226DC,0),(0x22760,0)):
        build.patch(f'spell-menu-table-{site:x}',site,struct.pack('<I',START+inner+0x08000000),struct.pack('<I',table_at+inner+0x08000000),'spell-menu')
    for site,ident in ((0x225E0,'available'),(0x22604,'unavailable'),(0x22620,'unavailable')):
        row=next(r for r in entries if r['id']=='spell-menu.'+ident)
        build.patch(f'spell-menu-format-{site:x}',site,struct.pack('<I',row['source']['offset']+0x08000000),struct.pack('<I',row['offset']+0x08000000),'spell-menu')
    return {'entries':entries,'table_offset':table_at,'definition_copy_offset':definitions_at,'definition_count':COUNT,'lookup_preserved_bytes':len(definitions),'catalog_sha256':digest(CATALOG.read_bytes()),'scope':catalog['scope']}
