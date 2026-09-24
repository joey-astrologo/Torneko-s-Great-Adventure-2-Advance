"""Checked early-menu prototype: isolated labels, explicit stack capacities."""
import json
import struct
from tools.compact_font import COMPACT_ASSET, encode, load_font, measure
from tools.rom import ROOT, digest, load_base, require

OWNER='early-menus'
ACTIONS={10:'Swing',12:'Read',13:'Drink',14:'Use',15:'Put in',17:'Use',32:'Use',33:'Write',42:'View',4:'Shoot',5:'Equip',6:'Remove',7:'Drop',8:'Swap',9:'Throw',11:'Eat',18:'Take',40:'Info'}
ACTIONS.update({1: 'None', 2: 'Walk', 3: 'Attack', 16: 'Take', 19: 'Throw', 20: 'Step', 21: 'Put in', 22: 'Take', 23: 'Use', 24: 'Stairs', 25: 'Shoot', 26: 'Throw', 27: 'Swing', 28: 'Eat', 29: 'Read', 30: 'Drink', 31: 'Use', 34: 'Skills', 35: 'Spells', 41: 'Name', 43: 'Skills'})
ROOT_LABELS={0x19cac:('Items',),0x19cbc:('Items','Skills'),0x19d10:('Items','Spells'),
             0x19d18:('Stairs',),0x19d34:('Trap',),0x19d94:('Floor',),0x19d98:('Option',)}
# Original pointers are fixed independently of the current ROM read.
ROOT_POINTERS={0x19cac:0x806b5e8,0x19cbc:0x806b5f4,0x19d10:0x806b604,
               0x19d18:0x806b614,0x19d34:0x806b620,0x19d94:0x806b62c,0x19d98:0x806b638}
# Keep the three original geometry instructions; shorter labels fit stock windows.
ORIGINAL_GEOMETRY=[(0x19d72,'0522'),(0x19474,'1820'),(0x19478,'0522')]
STACK=[('action-stack',0x1918e,'a0b0','d0b0'),('action-unstack',0x1949c,'20b0','50b0'),
       ('action-scratch-disabled',0x19408,'10a8','40a8'),('action-scratch-enabled',0x19442,'10a8','40a8'),
       ('action-scratch-concat',0x1944a,'10a9','40a9'),
       ('root-stack',0x19aa2,'d0b0','e0b0'),('root-unstack',0x19e28,'50b0','60b0'),
       ('root-ground-stairs',0x19d08,'4aa8','54a8'),('root-ground-trap',0x19d28,'4aa8','54a8'),
       ('root-ground-empty',0x19d38,'4aa8','54a8'),('root-ground-concat',0x19d44,'4aa9','54a9')]


def add_menus(build, font=None):
    font=font or load_font(); original=load_base(); entries=[]
    review_path=ROOT/'translations/menus-review.json'
    review=json.loads(review_path.read_text())
    require(review['base_rom_sha256']==digest(original) and
            review['action_table_sha256']==digest(original[0x141904:0x1419b4]),'Menu source table changed')
    reviewed={r['id']:r for r in review['entries']}
    expected={f'action.{i}':text for i,text in ACTIONS.items()} | {
        f'root.{site:06x}':' / '.join(labels) for site,labels in ROOT_LABELS.items()}
    require(set(reviewed)==set(expected),'Menu review coverage differs')
    for ident,text in expected.items():
        row=reviewed[ident];raw=bytes.fromhex(row['source_hex']);start=row['source']-0x8000000
        require(row['status']=='reviewed' and row['english']==text and
                original[start:start+len(raw)]==raw and digest(raw)==row['source_sha256'],
                'Menu translation/source review is stale: '+ident)
    table=bytearray(original[0x141904:0x1419b4])
    for index,text in ACTIONS.items():
        require(measure(text,font)<=36,'Action label exceeds usable 36 pixels')
        payload=encode(text); offset=build.allocate(f'action-label-{index}',payload,OWNER)
        source=struct.unpack_from('<I',table,index*4)[0]
        struct.pack_into('<I',table,index*4,offset+0x8000000)
        entries.append({'id':f'action.{index}','english':text,'source':source,'offset':offset,
                        'encoded_hex':payload.hex(),'advance':measure(text,font),'budget':36})
    table_offset=build.allocate('action-label-table',bytes(table),OWNER)
    build.patch('action-table-consumer',0x19434,struct.pack('<I',0x08141904),struct.pack('<I',table_offset+0x8000000),OWNER)
    for site,labels in ROOT_LABELS.items():
        require(all(measure(s,font)<=34 for s in labels),'Main command exceeds usable 34 pixels')
        if site==0x19d98:payload=b'\x03\x07'+encode(labels[0])
        else:
            payload=b'\x03%c'+encode(labels[0])[:-1]+b'\r'
            if len(labels)==2:payload+=b'\x03\x07'+encode(labels[1])[:-1]+b'\r'
            payload+=b'\0'
        offset=build.allocate(f'root-format-{site:06x}',payload,OWNER)
        build.patch(f'root-format-pointer-{site:06x}',site,struct.pack('<I',ROOT_POINTERS[site]),struct.pack('<I',offset+0x8000000),OWNER)
        entries.append({'id':f'root.{site:06x}','english':' / '.join(labels),'source':ROOT_POINTERS[site],
                        'offset':offset,'encoded_hex':payload.hex(),'budget':34})
    for site,expected in ORIGINAL_GEOMETRY:
        require(original[site:site+2]==bytes.fromhex(expected),'Original menu geometry changed')
    for name,site,before,after in STACK:
        build.patch(name,site,bytes.fromhex(before),bytes.fromhex(after),OWNER)
    # Seven labels, up to 12 text bytes plus disabled colour prefix/reset/newline.
    longest=max(len(encode(s))-1 for s in ACTIONS.values())
    require(7*(longest+4)+1<=256,'Action stream can overflow its stack buffer')
    require(longest+5<=64,'Single action can overflow its scratch buffer')
    root_bound=max(sum(2*len(s)+3 for s in labels) for labels in ROOT_LABELS.values())+max(2*len(ROOT_LABELS[site][0])+3 for site in (0x19d18,0x19d34,0x19d94))+2*len(ROOT_LABELS[0x19d98][0])+3
    require(root_bound<=64,'Main stream exceeds reserved stack region')
    return {'entries':entries,'action_table_offset':table_offset,'font_asset':'compact-english',
            'action_capacity':256,'action_scratch_capacity':64,'root_capacity':64,
            'action_max_bytes_bound':7*(longest+4)+1,'root_max_bytes_bound':root_bound,
            'review_sha256':digest(review_path.read_bytes()),
            'original_other_consumers_preserved':True}


def prototype():
    from tools.build_compact_font import add_font
    from tools.rom_build import RomBuild
    build=RomBuild(load_base());font=add_font(build,COMPACT_ASSET)
    menus=add_menus(build,load_font(COMPACT_ASSET));rom,ledger=build.finish()
    out=ROOT/'build/menu-resize/prototype';out.mkdir(parents=True,exist_ok=True)
    (out/'game.gba').write_bytes(rom)
    (out/'build.json').write_text(json.dumps(ledger|{'font':font,'menus':menus},indent=2)+'\n')
    return rom,menus

if __name__=='__main__':prototype()
