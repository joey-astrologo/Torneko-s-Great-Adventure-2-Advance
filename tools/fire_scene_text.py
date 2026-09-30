"""Owned fixed-stride fire-scene dialogue with preserved native index/count dispatch."""
import json,struct
from tools.rom import ROOT,digest,require
from tools.extract_items import source
from tools.dialogue_layout import compile_dialogue
from tools.text_codec import tokenize
CATALOG=ROOT/'translations/fire-scene-review.json'
BASE=0x150470
COUNT=43
EMPTY={10,11,20}
STRIDE=512

def add_fire_scene(build):
 c=json.loads(CATALOG.read_text());require(c['base_rom_sha256']==digest(build.original),'Fire scene base differs');require([e['index'] for e in c['entries']]==[i for i in range(COUNT) if i not in EMPTY],'Fire scene source cohort differs');blob=bytearray(COUNT*STRIDE);rows=[]
 for i in EMPTY:require(build.original[BASE+i*256]==0,'Fire scene empty record differs')
 for e in c['entries']:
  src=source(build.original,BASE+256*e['index']+0x08000000);require(e['source']==src and e['status']=='reviewed' and src['end_exclusive']<=BASE+256*(e['index']+1),'Fire scene source/review differs');raw,layout=compile_dialogue(e['english'],tokenize(bytes.fromhex(src['raw_hex']))[0]);require(len(raw)<=STRIDE,'Fire scene record exceeds private stride');at=e['index']*STRIDE;blob[at:at+len(raw)]=raw;rows.append(e|dict(relative_offset=at,encoded_hex=raw.hex(),layout=layout))
 at=build.allocate('fire-scene-private-records',bytes(blob),'fire-scene')
 build.patch('fire-scene-reader',0x52E34,struct.pack('<I',BASE+0x08000000),struct.pack('<I',at+0x08000000),'fire-scene')
 build.patch('fire-scene-stride',0x52DF4,bytes.fromhex('2802'),bytes.fromhex('6802'),'fire-scene')
 for e in rows:e['offset']=at+e.pop('relative_offset')
 return dict(entries=rows,table_offset=at,stride=STRIDE,empty_indices=sorted(EMPTY),record_count=COUNT,catalog_sha256=digest(CATALOG.read_bytes()),scope=c['scope'])
