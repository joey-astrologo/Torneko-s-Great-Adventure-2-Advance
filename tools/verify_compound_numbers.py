"""Native pixels for compound numerals, with original sequence/value oracles."""
import argparse,json
from pathlib import Path
from tools.rom import ROOT,digest,require,load_base
import mgba.log
from tools.emulator import Session,Debugger
from tools.dialogue_checks import TextChecks
from tools.verify_compact_font import call_thumb
from tools.numeric_font import ALIASES,record_offset
from tools.build_compact_font import HOOK_OFFSET,HOOK_BYTES,FONT_OFFSET
from tools.review_fonts import lookup

def run(source=ROOT/'build/english'):
 mgba.log.silence();rom=(source/'torneko-2-english.gba').read_bytes();build=json.loads((source/'build.json').read_text());require(digest(rom)==build['output_sha256'],'Stale numeric prototype');base=load_base();out=source/'compound-numbers-validation';results=[];probes=[]
 for case,offset,codes in [('ordinals',0x644E8,list(range(0x876C,0x8771))),('skill-counts',0x60772,list(range(0x8771,0x8774)))]:
  raw=b''.join(c.to_bytes(2,'big') for c in codes)+b'\0';require(base[offset:offset+len(raw)]==raw,'Compound numeral source differs');pointer=0x08000000+offset
  with Session(rom,out/case) as g:
   g.frames(600);m=g.core.memory;overrides=[];draws=[];c=TextChecks(g,{pointer:{'id':case,'encoded_hex':raw.hex(),'layout':{'pages':[{}]}}})
   def callback(e):
    a,r=e['address'],e['registers']
    if a==0x080021B4 and not overrides:
     overrides.append({'event':e,'r1_after':pointer,'reason':'Controlled first title-menu string replacement with the original ordinal/count sequence.'});g.core.cpu.gprs[1]=pointer;r=list(r);r[1]=pointer;e=e|{'registers':r}
    if a==0x08001BC4 and c.active:
     w=r[0];key=(w,r[1],r[13],r[14],m.u8[w+2],m.u8[w+3])
     if not draws or draws[-1]['key']!=key:draws.append({'key':key,'code':r[1],'x':m.u8[w+2],'y':m.u8[w+3],'origin':[m.u8[w],m.u8[w+1]],'width':m.u8[w+4]*8,'foreground':m.u8[0x020000C2],'bank':m.u16[m.u32[w+12]]>>12})
    c.callback(e)
   with Debugger(g,callback,max_events=12000) as trace:
    for a in c.ADDRESSES:trace.breakpoint(a)
    g.press('START',wait=180)
   pic=g.capture('numbers');require([d['code'] for d in draws]==codes and len(c.reads)==1 and not c.active,'Missing compound numeral render');pixels=0
   for d in draws:
    glyph,_=c.glyph_record(d['code']);require(d['x']+glyph['advance']<=d['width'],'Compound numeral overflow');colour=m.u16[0x05000000+2*(16*d['bank']+d['foreground'])];rgb=tuple(((colour>>s)&31)*255//31 for s in (0,5,10))
    for y,line in enumerate(glyph['rows']):
     for x,bit in enumerate(line):require((pic.getpixel((d['origin'][0]+d['x']+x,d['origin'][1]+16*d['y']+y))==rgb)==(bit=='#'),'Compound numeral final pixels differ');pixels+=1
   if case=='ordinals':
    for code in sorted(set(ALIASES)|{c-1 for c in ALIASES}|{c+1 for c in ALIASES}|{0,0x20,0x8140,0x8750,0x8751,0x8752,0x8753,0x9ae2,0xf01f,0xf020,0xf07e,0xf07f,0x1234824f,0xffff}):
     result=call_thumb(g,0x08001A04,code);masked=code&65535;expected=record_offset(masked,HOOK_OFFSET+HOOK_BYTES) if masked in ALIASES else FONT_OFFSET+(masked-0xf020)*32 if 0xf020<=masked<=0xf07e else lookup(base,masked);require(result['r0']==0x08000000+expected,'Compound numeric lookup differs');probes.append(result)
   results.append({'case':case,'inputs':g.inputs,'overrides':overrides,'reads':c.reads,'visible_pixels_checked':pixels,'images':{'numbers.png':digest((g.output/'numbers.png').read_bytes())}})
 report={'passed':True,'rom_sha256':digest(rom),'aliases':len(ALIASES),'cases':results,'probes':probes,'scope':'Original numeral sequences passed through the native string reader in a controlled title-menu row, with exact pixels/advance and all numeric lookup/fallback ABI probes. Natural ordinal/count consumers are not claimed.'};(out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print('Compound numerals:',len(results),'render cases;',len(probes),'lookup probes')
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,default=ROOT/'build/english');run(p.parse_args().source)
