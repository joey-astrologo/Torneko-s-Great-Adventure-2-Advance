"""Fifteen story announcements whose sole at-command is the native A jingle."""
import json,re,struct
from tools.rom import ROOT,digest,require
from tools.opening_text import BANK_RAM,banks
from tools.event_text import table_entries
from tools.dialogue_layout import compile_dialogue
from tools.lz77 import pack_literals,decompress

CATALOG=ROOT/'translations/story-commands-review.json'

def add_commands(build,bank_data=None,changed_by_bank=None):
    catalog=json.loads(CATALOG.read_text());resources=banks();standalone=bank_data is None
    require(catalog['base_rom_sha256']==digest(build.original),'Story-command base differs')
    if standalone:
        bank_data={b['id']:bytearray(b['data']) for b in resources}
        changed_by_bank={b['id']:[] for b in resources}
    sources={e['id']:(b,e) for b in resources for e in table_entries(b)};rows=[]
    require(len(catalog['entries'])==15 and len({r['id'] for r in catalog['entries']})==15,
            'Story-command review set differs')
    for row in catalog['entries']:
        bank,entry=sources[row['id']];raw=bank['data'][entry['start']:entry['end_exclusive']]
        require(row['status']=='reviewed' and row['prose_review'] and raw.hex()==row['source_hex']
                and digest(raw)==row['source_sha256'],'Story-command source/review differs')
        require(re.findall(rb'@[ABC]@',raw)==[b'@A@'] and not re.search(rb'%[-0-9]*l?[dsc]',raw),
                'Story-command consumer is not a single-jingle direct stream')
        payload,layout=compile_dialogue(row['english'],entry['tokens'])
        require(re.findall(rb'@[ABC]@',payload)==[b'@A@'],'Story jingle command changed')
        offset=build.allocate(row['id'],payload,'story-commands')
        relative=(offset+0x08000000-(BANK_RAM+entry['strings_offset']+entry['group_offset']))&0xFFFFFFFF
        data=bank_data[bank['id']];slot=entry['slot']
        require(slot not in changed_by_bank[bank['id']] and struct.unpack_from('<I',data,slot)[0]==entry['relative'],
                'Story-command slot already owned')
        struct.pack_into('<I',data,slot,relative);changed_by_bank[bank['id']].append(slot)
        rows.append(row|{'bank':bank['id'],'group':entry['group'],'index':entry['index'],
                         'slot':slot,'rom_offset':offset,'encoded_hex':payload.hex(),'layout':layout,
                         'language_status':'reviewed','batch':'story-commands',
                         'slots':[{'slot':slot,'group':entry['group'],'index':entry['index'],
                                   'relative':entry['relative'],'replacement':relative}]})
    reports=[]
    if standalone:
        for bank in resources:
            if not changed_by_bank[bank['id']]:continue
            data=bank_data[bank['id']];restored=bytearray(data)
            for slot in changed_by_bank[bank['id']]:restored[slot:slot+4]=bank['data'][slot:slot+4]
            require(restored==bank['data'],'Unowned story-command bank change')
            packed=pack_literals(data);require(decompress(packed)==(bytes(data),len(packed)),'Story-command bank round trip differs')
            offset=build.allocate('commands-'+bank['id'],packed,'story-commands')
            build.patch('commands-'+bank['id']+'-pointer',bank['pointer_offset'],
                        struct.pack('<I',bank['rom_offset']+0x08000000),struct.pack('<I',offset+0x08000000),'story-commands')
            reports.append({'id':bank['id'],'offset':offset,'decoded_bytes':len(data),'changed_slots':changed_by_bank[bank['id']]})
    return {'entries':rows,'banks':reports,'catalog_sha256':digest(CATALOG.read_bytes()),
            'scope':'Fifteen direct story streams with a single @A@. Native callback 08051664 only requests the original jingle for A; B/C transitions and printf/custom consumers are excluded. Bank scripts/other data stay unchanged. Gift/unlock progression outside the display callback is separate.'}
