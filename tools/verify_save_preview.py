"""Cold-load save previews, original selectors and maximum native fields."""
import argparse,json,struct
from pathlib import Path
import mgba.log
from tools.rom import ROOT,digest,require
from tools.compact_font import encode
from tools.emulator import Session,Debugger
from tools.dialogue_checks import TextChecks,player_layout_cases
from tools.name_entry import HERO,STORED,indexed
from tools.verify_result_ui import native_format

def run(source,only=None):
 out=source/'save-preview-validation';mgba.log.silence();rom=(source/'torneko-2-english.gba').read_bytes();build=json.loads((source/'build.json').read_text());require(digest(rom)==build['output_sha256'],'Stale save-preview ROM')
 town=(ROOT/'build/english/books-validation/save-continue.sav').read_bytes();dungeon=(ROOT/'build/english/name-entry-validation/english-save/native-save.sav').read_bytes()
 rows={r['offset']+0x08000000:r for r in build['save_preview']['entries']};formats={p:r for p,r in rows.items() if r.get('table_offset') in (0x5C8,0x5CC,0xA0C)};locations={r['location_id']:r for r in rows.values() if 'location_id' in r}
 jp=dict(player_layout_cases())['widest-Japanese'];glyph=jp[:2];table=build['name_entry']['glyph_table']-0x08000000;index=next(i for i in range(0xB9) if rom[table+2*i:table+2*i+2]==glyph)
 profiles={'ordinary':(indexed('Torneko'),encode('Torneko'),6,5,29,35,1),'wide-English':(indexed('WWWWWWWW',8),encode('WWWWWWW'),32767,32767,32767,32767,32767),'wide-Japanese':(bytes([index])*8+bytes(8),jp,32767,32767,32767,32767,32767)}
 cases=[('native-town',None,None,town),('native-dungeon',None,None,dungeon)]+[(f'{kind}-{profile}',kind,profile,town) for kind in tuple(range(13))+('town-0','town-1','town-2','town-3','completed') for profile in profiles]
 results=[]
 for case,kind,profile,battery in cases:
  if only and case!=only:continue
  print('Save preview:',case,flush=True)
  with Session(rom,out/case,initial_save=battery) as g:
   m=g.core.memory;c=TextChecks(g,{});overrides=[];pending={};calls=[];draws=[];images={};pixels=0;ready=[];creates=[];source_fields=[];owner=[];returns=[]
   def write(at,data):
    overrides.append({'address':at,'before':bytes(m[at:at+len(data)]).hex(),'after':data.hex()})
    for i,v in enumerate(data):m.u8[at+i]=v
   def callback(e):
    nonlocal pending
    a,r=e['address'],e['registers']
    if a==0x08014780:owner.append(e|{'guard':bytes(m[r[13]:r[13]+32]).hex()})
    if a==0x0801486E and profile:
     stored,hero_name,floor,level,hp,maxhp,attempt=profiles[profile];hero=m.u32[0x02001624];write(STORED,stored);write(HERO,hero_name.ljust(16,b'\0'));write(0x02003B44,struct.pack('<h',attempt))
     write(0x02005674,struct.pack('<h',0x379 if kind=='completed' else 0x378 if isinstance(kind,str) else floor))
     write(0x02003B6C,struct.pack('<I',kind if isinstance(kind,int) else 0))
     if isinstance(kind,str) and kind.startswith('town-'):write(0x020096B0,struct.pack('<h',int(kind[-1])))
     write(hero+0x88,struct.pack('<h',level));write(hero+0x84,struct.pack('<hh',hp,maxhp))
    if a==0x08001798:creates.append(e)
    if a==0x08000FB8 and r[1] in formats:
     row=formats[r[1]];require(r[0]==r[13]+0x14 and r[2]==r[13]+0x114,'Save-preview native output/name frame differs');count=3 if row['table_offset']==0x5CC else 7;args=r[2:4]+[m.u32[r[13]+4*i] for i in range(count-2)]
     require(r[14] in (0x080149B3,0x08014A13,0x08014A77),'Save-preview formatter reader differs')
     raw=native_format(bytes.fromhex(row['encoded_hex']),args,m);require(len(raw)<=row['maximum_bytes']<=256,'Save-preview output exceeds original buffer')
     if profile:
      village=encode('Torneko') if profile=='ordinary' else encode('WWWWWWWW') if profile=='wide-English' else glyph*8+b'\0'
      require(bytes(m[args[0]:args[0]+len(village)])==village,'Native indexed save name decoding differs')
     field=rows.get(args[-1] if count==3 else args[4]);require(field is not None,'Save-preview location remained unowned')
     if profile:
      expected_slot=0x5CC if isinstance(kind,str) else 0xA0C if kind==12 else 0x5C8;require(row['table_offset']==expected_slot,'Save-preview native format selector differs')
      if kind=='completed':require(field['table_offset']==0x944,'Completion label selector differs')
      elif isinstance(kind,str):require(field['location_id']==min(int(kind[-1]),2),'Town location/fallback selector differs')
      else:require(field['table_offset']==0x5D0+4*kind,'Dungeon location selector differs')
     source_fields.append(field['id']);pending={'row':row,'r':r,'raw':raw,'guard':bytes(m[r[0]+256:r[0]+256+36]),'args':args}
    if pending and a==(pending['r'][14]&~1):
     p=pending;old=p['r'];at=old[0];require(bytes(m[at:at+len(p['raw'])])==p['raw'] and bytes(m[at+256:at+292])==p['guard'] and r[4:12]==old[4:12] and r[13]==old[13],'Save-preview output/name/saved-locals guard/ABI differs')
     c.resources[at]=p['row']|{'encoded_hex':p['raw'].hex(),'layout':{'pages':[[p['row']['id']]]}};calls.append({'id':p['row']['id'],'hex':p['raw'].hex(),'bytes':len(p['raw']),'args':p['args'],'formatter_guard_abi_preserved':True});pending={}
    if a==0x08001BC4 and c.active:
     w=r[0];key=(w,r[1],r[13],r[14],m.u8[w+2],m.u8[w+3]);require(m.u8[w+3]<3,'Save-preview exceeded three native rows')
     if not draws or draws[-1]['key']!=key:draws.append({'key':key,'window':w,'code':r[1],'x':m.u8[w+2],'y':m.u8[w+3],'origin':[m.u8[w],m.u8[w+1]],'foreground':m.u8[0x020000C2],'bank':m.u16[m.u32[w+12]]>>12})
    if a in c.ADDRESSES:c.callback(e)
    if a==0x08014A80 and calls:ready.append(e)
    if a==0x08014E58 and owner:
     old=owner[0]['registers'];require(r[4:12]==old[4:12] and r[13]==old[13] and r[1]==old[14] and bytes(m[r[13]:r[13]+32]).hex()==owner[0]['guard'],'Native save preview owner ABI differs');returns.append(e)
   with Debugger(g,callback,max_events=150000) as debug:
    for a in set(c.ADDRESSES)|{0x08014780,0x0801486E,0x08000FB8,0x080149B2,0x08014A12,0x08014A76,0x08014A80,0x08014E58,0x08001798}:debug.breakpoint(a)
    g.frames(600);g.press('START',wait=180);pic=g.capture('preview');images['preview.png']=digest((g.output/'preview.png').read_bytes());require(len(calls)==1 and len(c.reads)==1 and not c.active and ready and not pending,'Save preview rendering incomplete')
    require(any(e['registers'][:4]==[1,13,28,3] for e in creates),'Save preview geometry differs')
    for d in draws:
     record,_=c.glyph_record(d['code']);colour=m.u16[0x05000000+2*(16*d['bank']+d['foreground'])];rgb=tuple(((colour>>s)&31)*255//31 for s in (0,5,10))
     for y,line in enumerate(record['rows']):
      for x,bit in enumerate(line):
       px=d['origin'][0]+d['x']+x;py=d['origin'][1]+d['y']*16+y;require((pic.getpixel((px,py))==rgb)==(bit=='#'),'Save-preview pixels differ: '+repr((case,px,py,hex(d['code']))));pixels+=1
    require(g.snapshot().battery==battery,'Save preview wrote battery')
    if profile is None:
     hero_before=bytes(m[HERO:HERO+16]);stored_before=bytes(m[STORED:STORED+16]);c.resources.clear()
     for _ in range(8):
      g.press('A',wait=600)
      if returns:break
     g.capture('resumed');images['resumed.png']=digest((g.output/'resumed.png').read_bytes());require(len(returns)==1 and bytes(m[HERO:HERO+16])==hero_before and bytes(m[STORED:STORED+16])==stored_before,'Native save preview resume/name preservation differs')
   results.append({'case':case,'kind':kind,'profile':profile,'source_save_sha256':digest(battery),'native_resume':profile is None,'formats':calls,'source_fields':source_fields,'reads':c.reads,'inputs':g.inputs,'overrides':overrides,'visible_pixels_checked':pixels,'images':images,'returns':returns})
 report={'passed':True,'rom_sha256':digest(rom),'cases':results,'scope':'Cold native town/dungeon save previews and actual Continue preserve both names and caller ABI.54 controlled RAM profiles cover13 destination selectors, three town labels plus original fallback and completion, ordinary/eight-wide-English/eight-wide-Japanese village names, seven-character player control, and32767 nonnegative signed16-bit stats/floor/attempts. Native indexed decoding,256-byte output, following name/locals guard, all three224px rows and pixels pass. Controlled profiles stop at preview; fake-state resumption, natural later progression and title artwork are excluded.'}
 (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print('Save preview:',len(results),'passed',flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,default=ROOT/'build/english');p.add_argument('--only');a=p.parse_args();run(a.source,a.only)
