"""Owned pot-transfer refusals, withdrawals and bulk summaries; single Put preserves its floor prefix."""
import json,re,struct
from tools.rom import ROOT,digest,require,load_base
from tools.extract_shared_text import START,END,extract
from tools.extract_items import source
from tools.compact_font import encode,measure
from tools.inventory_action_text import CONTROL

CATALOG=ROOT/'translations/container-review.json'
KIND_TABLE=0x1483D0
OWNERS={0x25178:(0xB4,0x38),0x25220:(0xA24,),0x25258:(0xA28,),0x25288:(0xB0,),0x252D8:(0xB8,),
        0x2530C:(0x150,),0x25334:(0x1EC,),0x2536C:(0x80,),0x253C0:(0xB0,),0x25460:(0xB8,),
        0x25524:(0xA2C,),0x25558:(0xA30,),0x25584:(0xBC,),0x255E8:(0xBC,),0x25644:(0xC0,)}
ROLES={0x38:[],0xB4:['floor','item','pot'],0xA24:['count','kind'],0xA28:['total','count','kind'],0xB0:['pot'],0xB8:['item','pot'],
       0x150:['item'],0x1EC:['item'],0x80:['item'],0xA2C:['count','kind'],0xA30:['total','count','kind'],
       0xBC:[],0xC0:['pot','item']}

def kind_sources(original=None):
    original=load_base() if original is None else original
    return [{'index':i,'pointer_offset':KIND_TABLE+4*i,'source':source(original,struct.unpack_from('<I',original,KIND_TABLE+4*i)[0])}
            for i in range(2)]

def add_containers(build):
    catalog=json.loads(CATALOG.read_text());allowed={n for ns in OWNERS.values() for n in ns}
    require(catalog['base_rom_sha256']==digest(build.original),'Container base differs')
    require(len(catalog['entries'])==len(allowed) and {r['table_offset'] for r in catalog['entries']}==allowed,
            'Unowned container source selection')
    require(len(catalog['labels'])==2 and {r['index'] for r in catalog['labels']}=={0,1},'Container kind set differs')
    labels=[];kind_table=bytearray(build.original[KIND_TABLE:KIND_TABLE+8]);sources=kind_sources(build.original)
    for row in catalog['labels']:
        require(row['source']==sources[row['index']]['source'] and row['status']=='reviewed','Container kind source differs')
        payload=encode(row['english']);offset=build.allocate(row['id'],payload,'container-text')
        struct.pack_into('<I',kind_table,row['index']*4,offset+0x08000000)
        labels.append(row|{'offset':offset,'encoded_hex':payload.hex()})
    kind_offset=build.allocate('container-kind-table',bytes(kind_table),'container-text')
    for site in (0x250F8,0x25104):
        build.patch(f'container-kind-consumer-{site:x}',site,struct.pack('<I',KIND_TABLE+0x08000000),
                    struct.pack('<I',kind_offset+0x08000000),'container-text')
    widths={'floor':measure('Floor: '),'item':162,'pot':162,'total':12,'count':12,'kind':max(measure(r['english']) for r in labels)}
    capacities={'floor':len(encode('Floor: '))-1,'item':63,'pot':63,'total':2,'count':2,'kind':max(len(bytes.fromhex(r['encoded_hex']))-1 for r in labels)}
    sources={r['table_offset']:r['source'] for r in extract()['entries']};table=bytearray(build.original[START:END]);rows=[]
    for row in catalog['entries']:
        source_row=sources[row['table_offset']];text=row['english'];fields=re.findall(r'\{([^{}]+)\}',text)
        require(row['status']=='reviewed' and row['source']==source_row,'Container review/source differs')
        require([f for f in fields if f!='fit']==ROLES[row['table_offset']] and fields.count('fit')<=1,
                'Container argument roles/order changed')
        plain=re.sub(r'\{[^{}]+\}','',text);require(not any(c in plain for c in '{}%\n\r'),'Unowned container controls')
        pieces=re.split(r'(\{[^{}]+\})',text);payload=bytearray()
        for part in pieces:
            if part=='{fit}':payload.extend(CONTROL)
            elif part.startswith('{'):payload.extend(b'%d' if part[1:-1] in ('total','count') else b'%s')
            else:payload.extend(encode(part)[:-1])
        payload.append(0);payload=bytes(payload)
        require(re.findall(b'%[sd]',bytes.fromhex(source_row['raw_hex']))==re.findall(b'%[sd]',payload),
                'Container printf arguments changed')
        line_widths=[measure(re.sub(r'\{[^{}]+\}','',part))+sum(widths[f] for f in re.findall(r'\{([^{}]+)\}',part))
                     for part in text.split('{fit}')]
        maximum=len(payload)+sum(capacities[f]-2 for f in fields if f!='fit')
        require(max(line_widths)<=216 and maximum<=192,'Container width/native192-byte budget exceeded')
        offset=build.allocate(row['id'],payload,'container-text');struct.pack_into('<I',table,row['table_offset'],offset+0x08000000)
        rows.append(row|{'offset':offset,'encoded_hex':payload.hex(),'maximum_line_widths':line_widths,
                         'maximum_bytes':maximum,'capacity':192,'field_roles':ROLES[row['table_offset']],
                         'field_widths':widths,'field_content_bytes':capacities})
    table_offset=build.allocate('container-shared-table',bytes(table),'container-text')
    for site in OWNERS:
        build.patch(f'container-consumer-{site:x}',site,struct.pack('<I',START+0x08000000),
                    struct.pack('<I',table_offset+0x08000000),'container-text')
    return {'entries':rows,'labels':labels,'table_offset':table_offset,'kind_table_offset':kind_offset,
            'consumer_literals':list(OWNERS),'catalog_sha256':digest(CATALOG.read_bytes()),'scope':catalog['scope']}
