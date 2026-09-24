"""Compare original and English dungeon loads, including untouched records/guards."""
import json,struct,mgba.log,argparse
from tools.rom import ROOT,load_base,digest,require
from tools.emulator import Session,Debugger
from tools.extract_monsters import RESOURCE,RAM,LINK_BASE,DEFINITIONS
from tools.lz77 import decompress
from tools.verify_service_ui import cstring
OUT=ROOT/'build/combat-prototype/monster-validation'

def run(cumulative=False):
 global OUT
 if cumulative:OUT=ROOT/'build/english/monster-validation'
 mgba.log.silence();root=OUT.parent;original=load_base();rom=(root/('torneko-2-english.gba' if cumulative else 'game.gba')).read_bytes();build=json.loads((root/'build.json').read_text());decoded=decompress(original,RESOURCE)[0];samples=[]
 for label,data in [('original',original),('english',rom)]:
  with Session(data,OUT/label,initial_save=(ROOT/'build/mansion/native/floor-five-native.sav').read_bytes()) as g:
   observed=[]
   def cb(e):
    m=g.core.memory;actual=bytes(m[RAM:RAM+65536]);expected=bytearray(decoded)
    for at in range(0,len(expected)-3,4):
     value=struct.unpack_from('<I',expected,at)[0];offset=(value-LINK_BASE)&0xffffffff
     if offset<=0xffff:struct.pack_into('<I',expected,at,RAM+offset)
    if label=='english':
     for row in build['monsters']['entries']:struct.pack_into('<I',expected,DEFINITIONS+row['id']*28,row['offset']+0x8000000)
    require(actual[:len(expected)]==expected,'Native dungeon loader changed unexpected bytes')
    for row in build['monsters']['entries']:
     pointer=m.u32[RAM+DEFINITIONS+row['id']*28]
     raw=bytes.fromhex(row['encoded_hex'] if label=='english' else row['source']['raw_hex'])
     require(cstring(m,pointer)+b'\0'==raw,'Native actor name pointer/content differs')
    observed.append({'decoded_sha256':digest(actual[:len(expected)]),'tail_hex':actual[len(expected):].hex(),'names':141,'unchanged_non_name_bytes':True})
   with Debugger(g,cb,max_events=100) as d:
    d.breakpoint(0x0803a214);g.frames(600);g.press('START',wait=180);g.frames(204)
    for _ in range(8):g.press('A',wait=120)
   require(len(observed)==1,'Expected one dungeon data load');samples.append({'case':label,'rom_sha256':digest(data),'loads':observed,'inputs':g.inputs})
 require(samples[0]['loads'][0]['tail_hex']==samples[1]['loads'][0]['tail_hex'],'Dungeon relocation tail differs')
 report={'passed':True,'rom_sha256':digest(rom),'cases':samples,'scope':'Native original/prototype dungeon loader, all 141 name pointers/contents, complete relocated data and unchanged tail through original 64KiB scan. No RAM growth or attribute changes. Raw result/history names remain outside insertion.'}
 OUT.mkdir(exist_ok=True);(OUT/'report.json').write_text(json.dumps(report,indent=2)+'\n');print('Monster resource: 141 pointers; complete original/English native loads passed')
if __name__=='__main__':
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--cumulative',action='store_true');run(parser.parse_args().cumulative)
