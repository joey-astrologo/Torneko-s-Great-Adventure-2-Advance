"""Enumerate the bounded Torneko 2 item definitions and Info description tables."""
import json,struct,csv
from tools.rom import ROOT,load_base,digest,require
from tools.text_codec import tokenize,readable
DEFINITIONS=0x141b9c
COUNT=221
DESCRIPTIONS=0x143f50
CATEGORY_DESCRIPTIONS=0x143f18

def source(rom,pointer):
 if not pointer:return None
 offset=pointer-0x8000000;tokens,end=tokenize(rom,offset)
 return {'offset':offset,'end_exclusive':end,'raw_hex':rom[offset:end].hex(),'sha256':digest(rom[offset:end]),'japanese':readable(tokens)}
def extract():
 rom=load_base();rows=[]
 for i in range(COUNT):
  start=DEFINITIONS+i*24;record=rom[start:start+24];category=record[20]
  require(category<14,'Item category outside table')
  name=source(rom,struct.unpack_from('<I',record)[0]);description=source(rom,struct.unpack_from('<I',rom,DESCRIPTIONS+i*4)[0]);common=source(rom,struct.unpack_from('<I',rom,CATEGORY_DESCRIPTIONS+category*4)[0])
  rows.append({'id':i,'record_offset':start,'record_hex':record.hex(),'category':category,'name':name,'description':description,'category_description':common})
 return {'source_rom_sha256':digest(rom),'definitions_start':DEFINITIONS,'definitions_end_exclusive':DEFINITIONS+COUNT*24,'items':rows,
         'special_description_221':source(rom,struct.unpack_from('<I',rom,DESCRIPTIONS+221*4)[0]),
         'scope':'221 definition records and their category/specific Info descriptions; description 221 is an invisible-item fallback, not a definition. Enumeration is not natural-use coverage. Neighboring unidentified-name tables are separate.'}
def run():
 out=ROOT/'build/item-extraction';out.mkdir(exist_ok=True);data=extract();(out/'catalog.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
 with (out/'items.csv').open('w',newline='') as f:
  w=csv.writer(f);w.writerow(['id','category','Japanese name','category description','specific description'])
  for r in data['items']:w.writerow([r['id'],r['category'],r['name']['japanese'],(r['category_description'] or {}).get('japanese',''),(r['description'] or {}).get('japanese','')])
 print('Extracted',len(data['items']),'item definitions')
if __name__=='__main__':run()
