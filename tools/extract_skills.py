"""Bound128 native skill definitions and their indexed Info descriptions."""
import json,struct
from tools.extract_items import source
from tools.rom import ROOT,load_base,digest,require

DEFINITIONS=0x1457EC
DESCRIPTIONS=0x146BF4
COUNT=128
STRIDE=36


def extract():
    rom=load_base()
    # Four original learned/unlearned/type passes bound the same definition
    # array to IDs0..127. The separate Info reader indexes descriptions by ID.
    for site,expected in ((0x21A0A,'7f2aeedd'),(0x21A42,'7f2aeddd'),(0x21A7A,'7f2aeddd'),(0x21AB2,'7f2aeddd')):
        require(rom[site:site+4]==bytes.fromhex(expected),'Skill enumeration changed')
    require(struct.unpack_from('<I',rom,0x2184C)[0]==DEFINITIONS+0x08000000 and
            struct.unpack_from('<I',rom,0x21854)[0]==DESCRIPTIONS+0x08000000,'Skill Info source literals changed')
    entries=[]
    for ident in range(COUNT):
        at=DEFINITIONS+STRIDE*ident;record=rom[at:at+STRIDE]
        name=source(rom,struct.unpack_from('<I',record)[0]);description=source(rom,struct.unpack_from('<I',rom,DESCRIPTIONS+ident*4)[0])
        require(name and description and record[26]<=3,'Unexpected skill definition/Info pointer')
        entries.append({'id':ident,'record_offset':at,'record_hex':record.hex(),
                        'name_source':name,'description_source':description,
                        'hunger_cost':record[23],'menu_order':record[25],
                        'kind':record[26],'menu_eligible':record[25]!=0xF0})
    return {'base_rom_sha256':digest(rom),'entries':entries,
            'scope':'128 skill records bounded by four native enumeration loops;128 separate Info pointers. Menu orderF0 is excluded by those loops, not proof of global unreachability or free space.'}


def run():
    report=extract();out=ROOT/'build/skill-extraction';out.mkdir(parents=True,exist_ok=True)
    (out/'catalog.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print('Extracted',len(report['entries']),'skill definitions')


if __name__=='__main__':run()
