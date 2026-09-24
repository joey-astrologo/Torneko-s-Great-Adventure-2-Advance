"""Reviewed ordinary event prose; custom format/command consumers stay separate."""
import json,re,struct
from tools.rom import ROOT,digest,require
from tools.opening_text import BANK_RAM,banks
from tools.event_text import table_entries
from tools.dialogue_layout import compile_dialogue
from tools.lz77 import pack_literals,decompress

CATALOG=ROOT/'translations/event-prose-review.json'
STATIC_FORMAT_SOURCES = {'event-bank-5.2747', 'event-bank-6.465b'}

def add_prose(build, bank_data, changed_by_bank):
    catalog=json.loads(CATALOG.read_text())
    require(catalog['base_rom_sha256']==digest(build.original),'Event prose base differs')
    sources={entry['id']:(bank,entry) for bank in banks() for entry in table_entries(bank)}
    require(len({r['id'] for r in catalog['entries']})==len(catalog['entries']),'Duplicate prose identity')
    excluded={r['id'] for r in catalog['excluded']}
    require(not excluded & {r['id'] for r in catalog['entries']},'Excluded special consumer selected')
    result=[]
    for row in catalog['entries']:
        require(row['status']=='reviewed' and row['prose_review'],'Event prose lacks bilingual review')
        bank,entry=sources[row['id']];raw=bank['data'][entry['start']:entry['end_exclusive']]
        require(raw.hex()==row['source_hex'] and digest(raw)==row['source_sha256'],'Event prose source differs')
        require(row['id'] not in STATIC_FORMAT_SOURCES and not re.search(rb'%[-0-9]*l?[dsc]',raw), 'Special formatter requires separate insertion')
        require(not any(command in row['english'] for command in ('@A@','@B@','@C@')), 'Event command requires separate branch validation')
        payload,layout=compile_dialogue(row['english'],entry['tokens'])
        offset=build.allocate(row['id'],payload,'event-prose')
        relative=(offset+0x08000000-(BANK_RAM+entry['strings_offset']+entry['group_offset']))&0xFFFFFFFF
        data=bank_data[bank['id']];slot=entry['slot']
        require(struct.unpack_from('<I',data,slot)[0]==entry['relative'],'Event prose slot already owned')
        struct.pack_into('<I',data,slot,relative);changed_by_bank[bank['id']].append(slot)
        result.append({'id':row['id'],'rom_offset':offset,'source_sha256':row['source_sha256'],'encoded_hex':payload.hex(),
                       'layout':layout,'language_status':'reviewed','batch':'event-prose','bank':bank['id'],
                       'slots':[{'group':entry['group'],'index':entry['index'],'slot':slot,'relative':entry['relative'],'replacement':relative}]})
    return result,digest(CATALOG.read_bytes())

def add_prototype(build):
    resources=banks();data={b['id']:bytearray(b['data']) for b in resources};changed={b['id']:[] for b in resources}
    rows,review=add_prose(build,data,changed);reports=[]
    for bank in resources:
        blob=data[bank['id']];restored=bytearray(blob)
        for slot in changed[bank['id']]:restored[slot:slot+4]=bank['data'][slot:slot+4]
        require(restored==bank['data'],'Unowned event prose bank change')
        packed=pack_literals(blob);require(decompress(packed)==(bytes(blob),len(packed)),'Event prose packing differs')
        offset=build.allocate('prose-'+bank['id'],packed,'event-prose')
        build.patch('prose-'+bank['id']+'-pointer',bank['pointer_offset'],struct.pack('<I',bank['rom_offset']+0x08000000),struct.pack('<I',offset+0x08000000),'event-prose')
        reports.append({'id':bank['id'],'bank_rom_offset':offset,'decoded_bytes':len(blob),'changed_slots':changed[bank['id']],
                        'original_decoded_bytes_except_slots_preserved':True,'new_ram_bytes':0})
    return {'entries':rows,'banks':reports,'review_sha256':review}
