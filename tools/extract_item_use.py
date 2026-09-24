"""The fourteen category slots and five native item-use announcements."""
import json,struct
from tools.rom import ROOT,load_base,digest,require
from tools.extract_items import source

START,END = 0x1419B8,0x1419F0
SOURCE_OFFSETS = {0x649B0,0x649C4,0x649D8,0x649EC,0x64A00}

def extract():
    rom=load_base()
    require(struct.unpack_from('<I',rom,0x258D0)[0]==0x08000000+START,'Item-use consumer changed')
    slots=[{'category':i,'pointer_offset':START+i*4,
            'source':source(rom,struct.unpack_from('<I',rom,START+i*4)[0])} for i in range(14)]
    require({r['source']['offset'] for r in slots}==SOURCE_OFFSETS,'Item-use source set differs')
    return {'source_rom_sha256':digest(rom),'start':START,'end_exclusive':END,'entries':slots,
            'scope':'Five distinct sources in fourteen category slots. Native consumer 080257F8 uses the player name plus a separate 64-byte item name and formats into its 256-byte stack message. Native use reachability is separately validated.'}

def run():
    out=ROOT/'build/item-use-extraction';out.mkdir(parents=True,exist_ok=True)
    report=extract();(out/'catalog.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print('Item-use announcements: 5 sources, 14 category slots')

if __name__=='__main__':run()
