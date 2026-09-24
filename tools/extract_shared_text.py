"""Enumerate the bounded shared system/combat/menu text pointer run."""
import json,struct
from tools.rom import ROOT,load_base,digest,require
from tools.extract_items import source
from tools.text_codec import tokenize,source_bytes

START=0x140d68
END=0x1417a0
COUNT=(END-START)//4

def extract():
 rom=load_base();rows=[]
 require(COUNT==654 and struct.unpack_from('<I',rom,END)[0]==0,'Shared pointer-run boundary changed')
 for i in range(COUNT):
  pointer=struct.unpack_from('<I',rom,START+i*4)[0]
  require(0x0805fe00<=pointer<0x0806d000,'Shared text pointer outside verified source region')
  src=source(rom,pointer);raw=bytes.fromhex(src['raw_hex'])
  require(source_bytes(tokenize(raw)[0])==raw,'Shared source does not round trip')
  rows.append({'index':i,'table_offset':i*4,'pointer_offset':START+i*4,'source':src})
 return {'source_rom_sha256':digest(rom),'start':START,'end_exclusive':END,'pointer_count':COUNT,'entries':rows,
         'scope':'654 consecutive original text pointers ending before the zero/numeric data at 001417A0. Mixed combat, system, menu, fragment and input text. Exact source-byte extraction; untraced consumers and token semantics remain open. This does not authorize blanket replacement or establish whole-game coverage.'}

def run():
 data=extract();out=ROOT/'build/shared-text';out.mkdir(parents=True,exist_ok=True)
 (out/'catalog.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
 print('Shared text pointers:',COUNT);return data

if __name__=='__main__':run()
