"""Bounded actor-name sources in the raw table and relocated dungeon resource."""
import json,struct
from tools.rom import ROOT,load_base,digest,require
from tools.lz77 import decompress
from tools.extract_items import source
TABLE=0x144c38
COUNT=141
RESOURCE=0x477700
LINK_BASE=0x8019c000
RAM=0x020129a8
DEFINITIONS=0x989c

def extract():
 rom=load_base();data,end=decompress(rom,RESOURCE)
 require(len(data)==64668 and end==0x47ce7d,'Dungeon resource boundaries changed')
 require(struct.unpack_from('<I',data,0x30)[0]==LINK_BASE+DEFINITIONS,'Monster definition table moved')
 require(DEFINITIONS+COUNT*28==0xa808,'Monster records do not end at first name')
 require(struct.unpack_from('<I',rom,TABLE+COUNT*4)[0]==0,'Raw actor table boundary differs')
 rows=[]
 for i in range(COUNT):
  ptr=struct.unpack_from('<I',rom,TABLE+4*i)[0];raw=source(rom,ptr)
  linked=struct.unpack_from('<I',data,DEFINITIONS+28*i)[0];offset=linked-LINK_BASE
  require(0xa808<=offset<0xaea8,'Monster name outside owned string region')
  finish=data.index(0,offset)+1;payload=data[offset:finish]
  battle={'offset':offset,'end_exclusive':finish,'raw_hex':payload.hex(),'sha256':digest(payload),'japanese':payload[:-1].decode('cp932')}
  require((raw['japanese'],battle['japanese'])=={0:('何者か','トルネコ'),131:('にせ神父','幻覚')}.get(i,(raw['japanese'],raw['japanese'])),'Actor table identities differ')
  rows.append({'id':i,'raw_table':raw,'dungeon':battle,'definition_offset':DEFINITIONS+28*i})
 return {'source_rom_sha256':digest(rom),'entries':rows,'dungeon_resource':{'offset':RESOURCE,'end_exclusive':end,'decoded_bytes':len(data),'decoded_sha256':digest(data),'compressed_sha256':digest(rom[RESOURCE:end]),'linked_base':LINK_BASE,'ram':RAM},'scope':'141 bounded actor IDs; raw table index zero is Someone, dungeon index zero is Torneko. Index 131 is False priest / Hallucination respectively. Names only; descriptions and other name consumers remain separate.'}

def run():
 out=ROOT/'build/monster-extraction';out.mkdir(parents=True,exist_ok=True);catalog=extract();(out/'catalog.json').write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n');print('Actor-name IDs:',len(catalog['entries']))
if __name__=='__main__':run()
