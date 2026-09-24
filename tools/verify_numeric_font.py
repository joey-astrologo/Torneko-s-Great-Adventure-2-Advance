"""Controlled lookup/ABI checks for every numeric alias and fallback boundaries."""
import json,mgba.log
from tools.build_english import build_rom
from tools.build_compact_font import FONT_OFFSET,HOOK_OFFSET,HOOK_BYTES
from tools.numeric_font import ALIASES,record_offset
from tools.review_fonts import lookup
from tools.emulator import Session
from tools.verify_compact_font import call_thumb
from tools.rom import ROOT,load_base,digest,require

def run():
 mgba.log.silence();rom,build=build_rom();out=ROOT/'build/english/numeric-validation';rows=[]
 with Session(rom,out) as g:
  g.frames(600)
  codes=set(ALIASES)|{c-1 for c in ALIASES}|{c+1 for c in ALIASES}|{0,0x20,0x8140,0x8750,0x8751,0x8752,0x8753,0x9ae2,0xf01f,0xf020,0xf07e,0xf07f,0x1234824f,0xffff}
  for code in sorted(codes):
   result=call_thumb(g,0x08001a04,code);masked=code&65535
   expected=(record_offset(masked,HOOK_OFFSET+HOOK_BYTES) if masked in ALIASES else
             FONT_OFFSET+(masked-0xf020)*32 if 0xf020<=masked<=0xf07e else lookup(load_base(),masked))
   require(result['r0']==0x08000000+expected,'Numeric/fallback lookup differs');rows.append(result)
 report={'passed':True,'rom_sha256':digest(rom),'aliases':len(ALIASES),'probes':rows,
         'scope':'Controlled native function calls; every numeric alias, adjacent icon/fallback codes, English boundaries and upper-bit masking. Callee-saved registers/SP preserved.'}
 (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print('Numeric aliases:',len(ALIASES),'; lookup probes:',len(rows))
if __name__=='__main__':run()
