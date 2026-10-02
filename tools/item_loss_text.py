"""Private item loss, pot breakage and explosion announcements."""
import json,re,struct
from tools.compact_font import encode,measure
from tools.extract_shared_text import START,END,extract
from tools.inventory_action_text import CONTROL
from tools.rom import ROOT,digest,require
CATALOG=ROOT/'translations/item-loss-review.json'
LITERALS={0xC468:{0x1E0},0x14338:{0x1E0},0x28864:{0x1E0},0x3E260:{0x1E0},0x3E81C:{0x1E0},0x3EA80:{0x1E0},0x3891C:{0x1D8},0x38D08:{0x34C}}

def add_item_loss(build, defer_literals=()):
    catalog=json.loads(CATALOG.read_text());sources={r['table_offset']:r['source'] for r in extract()['entries']}
    require(catalog['base_rom_sha256']==digest(build.original) and {r['table_offset'] for r in catalog['entries']}==set.union(*LITERALS.values()),'Item loss cohort differs')
    rows=[];table=bytearray(build.original[START:END]);widths={'actor':186,'player':98,'item':162};sizes={'actor':63,'player':14,'item':63}
    for row in catalog['entries']:
        text=row['english'];fields=row['fields'];tokens=re.findall(r'\{([^}]+)\}',text)
        require(row['source']==sources[row['table_offset']] and row['status']=='reviewed' and [p for p in tokens if p!='fit']==fields and text.count('{fit}')<=2,'Item loss source/review/fields differ')
        payload=b''.join(CONTROL if p=='{fit}' else b'%s' if p.startswith('{') else encode(p)[:-1] for p in re.split(r'(\{[^}]+\})',text))+b'\0'
        maximum=len(payload)+sum(sizes[f]-2 for f in fields)
        segments=[measure(re.sub(r'\{[^}]+\}','',p))+sum(widths[f]*p.count('{'+f+'}') for f in fields) for p in text.split('{fit}')]
        require(re.findall(b'%[sd]',bytes.fromhex(row['source']['raw_hex']))==[b'%s']*len(fields) and maximum<=256 and max(segments)<=216,'Item loss byte/pixel bounds exceeded')
        at=build.allocate(row['id'],payload,'item-loss-text');struct.pack_into('<I',table,row['table_offset'],at+0x08000000);rows.append(row|{'offset':at,'encoded_hex':payload.hex(),'maximum_bytes':maximum,'maximum_segment_widths':segments,'capacity':256})
    at=build.allocate('item-losss-private-table',bytes(table),'item-loss-text')
    require(set(defer_literals) <= set(LITERALS), 'Unowned deferred item-loss literal')
    for site in LITERALS:
        if site not in defer_literals:
            build.patch(f'item-loss-consumer-{site:x}',site,struct.pack('<I',START+0x08000000),struct.pack('<I',at+0x08000000),'item-loss-text')
    return {'entries':rows,'table_offset':at,'catalog_sha256':digest(CATALOG.read_bytes()),'scope':catalog['scope']}
