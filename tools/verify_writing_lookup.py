import json
import mgba.log
from tools.rom import ROOT,require,digest
from tools.emulator import Session
from tools.name_entry import EDIT,IDS
from tools.verify_compact_font import call_thumb
import argparse
from pathlib import Path

def run(out=ROOT/'build/english'):
 mgba.log.silence();rom=(out/'torneko-2-english.gba').read_bytes();b=json.loads((out/'build.json').read_text());results=[]
 with Session(rom,out/'writing-lookup-validation') as g:
  g.frames(600);m=g.core.memory;glyphs=bytes(m[b['name_entry']['glyph_table']:b['name_entry']['glyph_table']+512]);ids={glyphs[i*2:i*2+2]:i for i in range(2,185)}
  cases=[]
  for r in b['writing_input']['entries']:
   for text in sorted({r['english'],r['english'].lower(),r['english'].upper(),r['english'].swapcase()}):
    cases.append((r['family'],text,bytes(IDS[c] for c in text),r['target']))
  for table in b['writing_input']['tables']:
   for row in table['original_entries']:
    raw=bytes.fromhex(row['source']['raw_hex'])[:-1];require(len(raw)%2==0,'Japanese lookup not whole glyphs');indexed=bytes(ids[raw[i:i+2]] for i in range(0,len(raw),2));cases.append((table['family'],row['source']['japanese'],indexed,row['target']))
  for family in ('scroll','spell'):
   for text in ('No such name','Lightning Stor','WWWWWWWWWWWWWWW'):
    cases.append((family,text,bytes(IDS[c] for c in text),0))
  for family,text,indexed,target in cases:
   require(len(indexed)<=15,'Lookup input too long');value=indexed+b'\1'*(15-len(indexed))+b'\0'
   before=bytes(m[EDIT-4:EDIT]);after=bytes(m[EDIT+16:EDIT+24])
   for i,v in enumerate(value):m.u8[EDIT+i]=v
   result=call_thumb(g,0x08035458 if family=='scroll' else 0x0803EF48,0,EDIT)
   expected=target+(10 if family=='spell' and target else 0)
   require(result['r0']==expected,'Lookup differs: '+repr((family,text,target,result)))
   require(bytes(m[EDIT:EDIT+16])==value and bytes(m[EDIT-4:EDIT])==before and bytes(m[EDIT+16:EDIT+24])==after,'Lookup changed input/guards')
   results.append({'family':family,'text':text,'indexed_hex':value.hex(),'expected':expected,'result':result,'input_guard_preserved':True})
  (out/'writing-lookup-validation/report.json').write_text(json.dumps({'passed':True,'rom_sha256':digest(rom),'cases':results,'inputs':g.inputs,'scope':'Controlled original lookup function calls with exact English/kana indexed input, native candidate loop and target return; saved snapshot restored after each call. Input/ABI guards checked. Editor/navigation and writing outcomes are separate.'},ensure_ascii=False,indent=2)+'\n')
 print('Lookup cases',len(results),'passed')

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,default=ROOT/'build/english');run(p.parse_args().source)
