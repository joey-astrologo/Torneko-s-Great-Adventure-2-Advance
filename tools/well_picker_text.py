"""Own the well picker literals and reuse the measured English level template."""
import json,struct
from tools.rom import ROOT,digest,require
from tools.text_codec import tokenize
from tools.dialogue_layout import compile_dialogue

CATALOG=ROOT/'translations/well-picker-review.json'


def add_well_picker(build,remi):
    catalog=json.loads(CATALOG.read_text());require(catalog['base_rom_sha256']==digest(build.original),'Well picker base differs')
    require({r['id'] for r in catalog['entries']}=={'well-picker.prompt','well-picker.level'},'Well picker review selection differs')
    rows=[];template=next(r for r in remi['entries'] if r['index']==129)
    for row in catalog['entries']:
        source=row['source'];raw=bytes.fromhex(source['raw_hex'])
        require(row['status']=='reviewed' and row['prose_review'] and build.original[source['offset']:source['end_exclusive']]==raw and digest(raw)==source['sha256'],'Well picker source/review differs')
        if row['id']=='well-picker.prompt':
            payload,layout=compile_dialogue(row['english'],tokenize(raw)[0]);offset=build.allocate(row['id'],payload,'well-picker-text');site=0x512DC
            layout['direct_rom_stream']=True
        else:
            require(row['english']==template['english']=='Level {number}' and raw.count(b'%s')==1,'Well level template meaning/conversion differs')
            offset=template['offset'];payload=bytes.fromhex(template['encoded_hex']);layout=template['layout'];site=0x512E0
            require(offset+0x08000000 in remi['picker_width']['format_pointers'],'Well shared template lacks proportional-width ownership')
        build.patch(row['id']+'-literal',site,struct.pack('<I',source['offset']+0x08000000),struct.pack('<I',offset+0x08000000),'well-picker-text')
        rows.append(row|{'offset':offset,'encoded_hex':payload.hex(),'layout':layout,'literal_offset':site})
    return {'entries':rows,'reused_level_template':template['id'],'reused_proportional_helper':remi['picker_width']['offset'],'catalog_sha256':digest(CATALOG.read_bytes()),'scope':catalog['scope']}
