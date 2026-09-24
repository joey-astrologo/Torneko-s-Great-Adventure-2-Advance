"""Isolated floor-progress prose through an owned 288-byte stack buffer."""
import json,struct
from tools.rom import ROOT,digest,require
from tools.compact_font import encode,measure
from tools.dialogue_layout import compile_dialogue
from tools.text_codec import tokenize
from tools.opening_text import banks,BANK_RAM
from tools.event_text import table_entries
from tools.lz77 import pack_literals,decompress

CATALOG=ROOT/'translations/floor-progress-review.json'
CAPACITY=288

def compile_progress(row):
    raw=bytes.fromhex(row['source_hex']);text=row['english']
    count=raw.count(b'%d')
    require(count==text.count('{floor}') and count in (0,1),'Floor substitution count differs')
    # Reserve 24px during wrapping for the native 3-digit maximum (21px).
    # The sentinel is removed from the final byte stream. Event/name controls
    # still pass the ordinary compiler's exact source-order validation.
    sentinel='WWWW'
    require(sentinel not in text,'Floor width sentinel collides with prose')
    payload,layout=compile_dialogue(text.replace('{floor}',sentinel),tokenize(raw.replace(b'%d',b''))[0])
    encoded=encode(sentinel)[:-1]
    require(payload.count(encoded)==count,'Floor placeholder split during wrapping')
    payload=payload.replace(encoded,b'%d')
    pages=layout['pages']
    widths=[[width-(measure(sentinel)-21)*line.count(sentinel) for line,width in zip(page,line_widths)]
            for page,line_widths in zip(pages,layout['line_widths'])]
    maximum=len(payload)+count
    require(maximum<=CAPACITY,'Floor prose exceeds owned stack capacity')
    layout=layout|{'pages':[[line.replace(sentinel,'{floor}') for line in page] for page in pages],
                   'line_widths':widths,'encoded_bytes':len(payload),'maximum_formatted_bytes':maximum,
                   'capacity':CAPACITY,'floor_range':[0,255]}
    return payload,layout

def add_progress(build,bank_data=None,changed_by_bank=None):
    catalog=json.loads(CATALOG.read_text());bank=banks()[5]
    data=bytearray(bank['data']) if bank_data is None else bank_data[bank['id']]
    require(catalog['base_rom_sha256']==digest(build.original),'Floor-progress base differs')
    sources={e['id']:e for e in table_entries(bank)}
    require({r['id'] for r in catalog['entries']}=={'event-bank-5.25d2','event-bank-5.2649','event-bank-5.26c4','event-bank-5.2747'},'Unowned floor-progress selection')
    rows=[];slots=[]
    for row in catalog['entries']:
        require(row['status']=='reviewed' and row['prose_review'],'Floor prose lacks bilingual review')
        src=sources[row['id']];raw=bank['data'][src['start']:src['end_exclusive']]
        require(raw.hex()==row['source_hex'] and digest(raw)==row['source_sha256'],'Floor source changed')
        require(src['group']==7 and src['index'] in (5,6,7,8),'Floor native selector changed')
        payload,layout=compile_progress(row);offset=build.allocate('floor-progress-'+row['id'],payload,'floor-progress-prototype')
        relative=(offset+0x08000000-(BANK_RAM+src['strings_offset']+src['group_offset']))&0xFFFFFFFF
        require(struct.unpack_from('<I',data,src['slot'])[0]==src['relative'],'Floor slot already owned')
        struct.pack_into('<I',data,src['slot'],relative);slots.append(src['slot'])
        rows.append(row|{'offset':offset,'encoded_hex':payload.hex(),'layout':layout,'group':7,'index':src['index']})
    offset=None
    if bank_data is None:
        restored=bytearray(data)
        for slot in slots:restored[slot:slot+4]=bank['data'][slot:slot+4]
        require(restored==bank['data'],'Unowned floor-progress bank change')
        packed=pack_literals(data);require(decompress(packed)==(bytes(data),len(packed)),'Floor bank packing differs')
        offset=build.allocate('floor-progress-bank',packed,'floor-progress-prototype')
        build.patch('floor-progress-bank-pointer',bank['pointer_offset'],struct.pack('<I',bank['rom_offset']+0x08000000),struct.pack('<I',offset+0x08000000),'floor-progress-prototype')
    else:
        require(changed_by_bank is not None,'Shared floor bank needs its slot ledger')
        changed_by_bank[bank['id']].extend(slots)
    # Existing [SP,SP+8) retains the two outgoing arguments. [SP+8,SP+296)
    # becomes message storage; saved r4/r5/LR remain above the expanded frame.
    for ident,site,before,after in [('frame-enter',0x501DE,'82b0','cab0'),('output-address',0x50210,'114c','02ac'),('frame-leave',0x5024E,'02b0','4ab0')]:
        build.patch('floor-progress-'+ident,site,bytes.fromhex(before),bytes.fromhex(after),'floor-progress-prototype')
    return {'entries':rows,'bank_rom_offset':offset,'decoded_bytes':len(data),'changed_slots':slots,
            'capacity':CAPACITY,'extra_stack_bytes':288,'catalog_sha256':digest(CATALOG.read_bytes())}
