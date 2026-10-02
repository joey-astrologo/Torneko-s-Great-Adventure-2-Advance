"""Private late-bound callers, timed narration and native item-name producers."""
import json
import re
import struct
from collections import defaultdict

from tools.compact_font import encode, measure
from tools.dialogue_layout import compile_dialogue
from tools.extract_items import source, DEFINITIONS
from tools.inventory_action_text import CONTROL
from tools.rom import ROOT, digest, require
from tools.text_codec import tokenize

CATALOG=ROOT/'translations/remaining-callers-review.json'
COMMAND=re.compile(r'@w@|@W@|\{center\}|\{color:6\}|\{player\}|\{village\}')
CONTROLS={'{center}':b'\x14','{color:6}':b'\x03\x06','{player}':b'\x7e','{village}':b'\x1f',
          '@w@':b'@w@','@W@':b'@W@'}


def compile_row(row):
    text=row['english'];raw=bytes.fromhex(row['source']['raw_hex']);tokens=tokenize(raw)[0]
    if row['kind']=='dialogue':return compile_dialogue(text,tokens)
    if row['kind']=='fixed-pages':
        commands=[bytes.fromhex(t['raw_hex']) for t in tokens if t['kind']=='command' and t.get('name')!='newline']
        require([CONTROLS[c] for c in COMMAND.findall(text)]==commands,'Fixed-page command sequence differs')
        require(not any(c in COMMAND.sub('',text) for c in '{}@%'),'Unknown fixed-page syntax')
        pages=[p.split('\n') for p in text.split('\n\n')]
        widths=[[measure(COMMAND.sub('',line))+98*line.count('{player}')+112*line.count('{village}')
                 for line in page] for page in pages]
        require(all(1<=len(p)<=2 for p in pages) and max(max(p) for p in widths)<=216,'Fixed page exceeds native bounds')
        payload=b''
        for n,page in enumerate(pages):
            joined='\n'.join(page)
            payload+=b''.join(CONTROLS[p] if p in CONTROLS else encode(p)[:-1]
                              for p in re.split('('+COMMAND.pattern+')',joined))
            if n+1<len(pages):payload+=b'\r'*(3-len(page))
        payload+=b'\0'
        return payload,dict(pages=pages,line_widths=widths,maximum_width=216,native_width=224,
                            commands=[c.hex() for c in commands],encoded_bytes=len(payload))
    require(row['kind']=='format','Unknown continuation text kind')
    fields=re.findall(r'\{(item|actor)\}',text)
    require(fields==row['fields'] and not any(c in re.sub(r'\{(?:item|actor|fit)\}','',text) for c in '{}%@'),
            'Continuation format fields differ')
    payload=b''.join(b'%s' if p in ('{item}','{actor}') else CONTROL if p=='{fit}' else encode(p)[:-1]
                     for p in re.split(r'(\{[^}]+\})',text))+b'\0'
    require(re.findall(b'%[sd]',payload)==re.findall(b'%[sd]',raw),'Native formatter signature differs')
    widths=[measure(re.sub(r'\{(?:item|actor)\}','',line))+162*line.count('{item}')+186*line.count('{actor}')
            for line in re.split(r'\{fit\}|\n',text)]
    maximum=len(payload)+61*len(fields)
    require(max(widths)<=216 and maximum<=row['capacity'],'Continuation formatter exceeds native capacity')
    return payload,dict(pages=[re.split(r'\{fit\}|\n',text)],line_widths=[widths],maximum_width=216,
                        maximum_bytes=maximum,encoded_bytes=len(payload),conditional_join='{fit}' in text)


def add_remaining_callers(build, results):
    catalog=json.loads(CATALOG.read_text())
    require(catalog['base_rom_sha256']==digest(build.original),'Remaining caller base differs')
    rows=[]
    for e in catalog['entries']:
        require(e['status']=='reviewed' and source(build.original,e['source']['offset']+0x08000000)==e['source'],
                'Remaining caller source/review differs')
        raw,layout=compile_row(e)
        old=next((a for a in build.allocations if a['end_exclusive']-a['start']==len(raw)
                  and build.data[a['start']:a['end_exclusive']]==raw),None)
        at=old['start'] if old else build.allocate(e['id'],raw,'remaining-callers')
        rows.append(e|dict(offset=at,encoded_hex=raw.hex(),layout=layout,reused_payload=bool(old)))
    by_source={r['source']['offset']:r for r in rows};groups=defaultdict(list)
    for b in catalog['bindings']:
        at=b['call_context_offset'];expected=bytes.fromhex(b['call_context_hex'])
        require(build.original[at:at+len(expected)]==expected,'Remaining caller instructions differ')
        groups[b['literal_offset']].append(b)
    bindings=[];tables=[]
    for literal,group in groups.items():
        b=group[0];base,end=b['table_start'],b['table_end_exclusive']
        if base is None:pointer=by_source[b['source_offset']]['offset']+0x08000000
        else:
            require(all((x['table_start'],x['table_end_exclusive'],x['inherit_results'])==
                        (base,end,b['inherit_results']) for x in group),'Inconsistent table ownership')
            inherited=results.get('shared_table',base) if b['inherit_results'] else base
            # Preserve already translated sibling slots in original-region tables
            # and the previously allocated result table; neither is rewritten.
            original=bytes(build.data[inherited:inherited+end-base]);table=bytearray(original)
            for x in group:
                slot=x['table_slot'];src=x['source_offset']
                require(struct.unpack_from('<I',table,slot)[0]==src+0x08000000,'Remaining caller slot differs')
                struct.pack_into('<I',table,slot,by_source[src]['offset']+0x08000000)
            at=build.allocate(f'remaining-private-table-{literal:x}',bytes(table),'remaining-callers')
            pointer=at+0x08000000
            tables.append(dict(literal=literal,offset=at,source_start=inherited,size=end-base,
                               inherited_sha256=digest(original),changed_slots=[x['table_slot'] for x in group]))
        build.patch(f'remaining-caller-binding-{literal:x}',literal,struct.pack('<I',b['expected_literal']),
                    struct.pack('<I',pointer),'remaining-callers')
        bindings.extend(x|dict(compiled_literal=pointer,compiled_source=by_source[x['source_offset']]['offset']+0x08000000)
                        for x in group)
    item_table=next(a['start'] for a in build.allocations if a['id']=='item-definitions')
    for binding in catalog.get('item_definition_bindings',[]):
        at=binding['call_context_offset'];raw=bytes.fromhex(binding['call_context_hex'])
        require(build.original[at:at+len(raw)]==raw,'Native item-name producer differs')
    for literal in catalog['item_definition_literals']:
        build.patch(f'caller-item-definitions-{literal:x}',literal,struct.pack('<I',DEFINITIONS+0x08000000),
                    struct.pack('<I',item_table+0x08000000),'remaining-callers')
    return dict(entries=rows,bindings=bindings,tables=tables,item_definition_literals=catalog['item_definition_literals'],
                item_definition_table=item_table,item_definition_bindings=catalog.get('item_definition_bindings',[]),
                new_source_count=sum(r['new_source'] for r in rows),
                catalog_sha256=digest(CATALOG.read_bytes()),scope=catalog['scope'])
