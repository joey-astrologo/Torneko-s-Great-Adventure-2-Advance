"""Bound the 61 native spell definitions and their separate Info descriptions."""
import json,struct
from tools.extract_items import source
from tools.rom import ROOT,load_base,digest,require

DEFINITIONS=0x146DF4
DESCRIPTIONS=0x1470D0
COUNT=61


def extract():
    rom=load_base()
    require(DEFINITIONS+COUNT*12==DESCRIPTIONS,'Spell table bounds differ')
    # Both halves of the native menu enumeration include index60, then stop.
    require(rom[0x222D2:0x222D6]==bytes.fromhex('3c2bf1dd') and
            rom[0x22306:0x2230A]==bytes.fromhex('3c2bf0dd'),'Spell enumeration changed')
    entries=[]
    for i in range(COUNT):
        at=DEFINITIONS+12*i;record=rom[at:at+12]
        name=source(rom,struct.unpack_from('<I',record)[0])
        description=source(rom,struct.unpack_from('<I',rom,DESCRIPTIONS+4*i)[0])
        require(record[6]<=8 and name and description,'Unexpected spell definition')
        entries.append({'id':i,'record_offset':at,'record_hex':record.hex(),
                        'name_source':name,'description_source':description,
                        'hp_cost':struct.unpack_from('<h',record,4)[0],
                        'target_kind':record[6],'menu_order':record[8],
                        'menu_eligible':record[8]!=99})
    return {'base_rom_sha256':digest(rom),'entries':entries,
            'scope':'61 records bounded by two original native menu loops, and61 corresponding Info pointers. Menu order99 is excluded by those loops; this does not prove every other consumer unreachable.'}


def run():
    report=extract();out=ROOT/'build/spell-extraction';out.mkdir(parents=True,exist_ok=True)
    (out/'catalog.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print('Extracted',len(report['entries']),'spell definitions')


if __name__=='__main__':run()
