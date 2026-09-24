"""Extract the unidentified-item records and their explicit end-marker row."""
import json,struct
from tools.rom import ROOT,load_base,digest,require
from tools.extract_items import source
START=0x143058
END=0x143ee0
COUNT=(END-START)//24

def extract():
 rom=load_base();require(COUNT==155 and START+COUNT*24==END,'Alias table bounds changed')
 for site in (0xf628,0xf64c,0xf684):
  require(struct.unpack_from('<I',rom,site)[0]==START+0x8000000,'Unidentified-name consumer changed')
 rows=[]
 for i in range(COUNT):
  offset=START+i*24;raw=rom[offset:offset+24];name=source(rom,struct.unpack_from('<I',raw)[0])
  require(name and raw[20]<14,'Alias definition shape changed')
  rows.append({'id':i,'record_offset':offset,'record_hex':raw.hex(),'category':raw[20],'name':name,'disposition':'end-marker' if i==154 else 'unidentified-item-name'})
 require(rows[-1]['name']['japanese']=='エンドマーク' and struct.unpack_from('<h',rom,START+154*24+8)[0]==1,'Alias assignment sentinel changed')
 require(all(struct.unpack_from('<h',rom,START+i*24+8)[0]==0 for i in range(154)),'Unexpected early assignment sentinel')
 labels=[{'category':i,'pointer_offset':END+i*4,'source':source(rom,struct.unpack_from('<I',rom,END+i*4)[0])} for i in range(14)]
 return {'source_rom_sha256':digest(rom),'start':START,'end_exclusive':END,'record_bytes':24,'count':COUNT,'entries':rows,
         'category_labels':labels,'assignment_function':0x08009e68,'assignment_sentinel_offset':8,
         'scope':'154 appearance-name records followed by one explicit End Mark record, separately from identified items. Native unidentified-name branches at F5F8, F62C and F650 use this table. Assignment function 08009E68 stops before the nonzero signed halfword at record +8; End Mark is excluded from that assignment loop. The adjacent 14 category-label pointers start at 143EE0. Other reachability and native English insertion require separate verification.'}

def run():
 out=ROOT/'build/item-aliases';out.mkdir(parents=True,exist_ok=True);data=extract();(out/'catalog.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n');print('Unidentified item aliases:',COUNT)
if __name__=='__main__':run()
