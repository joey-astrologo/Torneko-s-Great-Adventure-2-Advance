"""Three original travel confirmation owners, save-name substitution and Yes/No/B."""
import argparse,json
from pathlib import Path
import mgba.log
from tools.rom import ROOT,digest,require
from tools.emulator import Session,Debugger,ffi
from tools.bakery_playtest import service_ready
from tools.dialogue_checks import TextChecks,rendered_codes
from tools.saved_village_checks import SavedVillageChecks
from tools.name_entry import indexed,HERO
OWNERS=[('map',0x4B8AC,0x4B8B8,0x4BAE6,0x4BB16,0x4BC2E,0x4BC3C,9),('destination',0x4C980,0x4C984,0x4C9E0,0x4CA0E,0x4CA12,0x4CA18,6),('picker',0x52044,0x52050,0x5227C,0x5229C,0x522F4,0x52302,None)]
def run(source,only=None):
 out=source/'travel-confirm-validation';rom=(source/'torneko-2-english.gba').read_bytes();b=json.loads((source/'build.json').read_text());require(digest(rom)==b['output_sha256'],'Travel confirmation ROM differs');mgba.log.silence();fixture=service_ready(rom,out);rows={e['id'].split('.')[-1]:e for e in b['travel_confirm']['entries']};table=b['name_entry']['glyph_table']-0x08000000;japanese=next(i for i in range(1,185) if rom[table+i*2:table+i*2+2]==b'\x82\xb0');results=[]
 for owner,entry,prologue,start,stop,epilogue,end,layoutreg in OWNERS:
  for key,profiles in [('enter',[('ordinary',None)]),('overwrite',[('native-save',None),('required-English',indexed('Torneko')[:8]),('eight-English',indexed('W'*8,maximum=8)[:8]),('eight-Japanese',bytes([japanese])*8),('empty',b'\x01'*8),('read-failure',b'\x01'*8)])]:
   for profile,ids in profiles:
    for layout in ((0,2) if layoutreg is not None else (2,)):
     for choice in ('yes','no','cancel'):
      case=f'{owner}-{key}-{profile}-{layout}-{choice}'
      if only and not case.startswith(only):continue
      print('Travel confirmation:',case,flush=True)
      row=rows[key];address=row['offset']+0x08000000;expected_name=b'\0'
      if ids:
       expected_name=b''.join(rom[table+v*2:table+v*2+2] for v in ids.split(b'\x01',1)[0])+b'\0'
      with Session(rom,out/case) as g:
       g.restore(fixture);m=g.core.memory;resources={address:row};c=SavedVillageChecks(g,resources,address,expected_name) if key=='overwrite' else TextChecks(g,resources);initial=[];returns=[];modals=[];modal_returns=[];overrides=[];produced=[];headers=[];draws=[];images={};pixels=0;inventory=bytes(m[0x0200DF28:0x0200E888]);hero=m.u32[0x02001624];gold=m.u32[hero+0x60];nameguard=bytes(m[0x0200CEFC:0x0200CF0C])
       def reg(e,i,v,why):overrides.append(dict(event=e,register=i,after=v,reason=why));g.core.cpu.gprs[i]=v if v<0x80000000 else v-0x100000000
       def jump(e,at,why):overrides.append(dict(event=e,pc_after=at+0x08000000,reason=why));require(g.core._core.writeRegister(g.core._core,b'pc',ffi.new('uint32_t*',at+0x08000000)),'Travel confirmation redirect failed')
       def cb(e):
        nonlocal expected_name
        a,r=e['address'],e['registers']
        if a==0x0801DFAC and not initial:initial.append(e|dict(guard=bytes(m[r[13]:r[13]+32]).hex()));jump(e,entry,'Controlled bank call into original travel-owner frame.');return
        if not initial or returns:return
        if a==prologue+0x08000000:
         reg(e,0,0 if key=='enter' else 0x10000,'Controlled original item-limit predicate result after its native16-bit shift.');
         if layoutreg is not None:reg(e,layoutreg,layout,'Original display-layout selector result.')
         jump(e,start,'Original literal selection and native confirmation; route/gate effects excluded.')
        if a==0x08015A34:require(r[0]==address and r[2]==1,'Travel confirmation native source/choice differs');modals.append(e)
        if key=='overwrite' and a==0x0801FAC8:
         before=bytes(m[r[13]+20:r[13]+28]);headers.append(dict(event=e,ids_hex=before.hex()))
         if profile=='native-save':
          require(r[0]==0,'Native saved-village header unavailable');native=before.split(b'\x01',1)[0];expected_name=b''.join(rom[table+v*2:table+v*2+2] for v in native)+b'\0';c.name=expected_name
          if c.active:
           expanded=bytes.fromhex(row['encoded_hex']).replace(b'\x1f',expected_name[:-1]);c.active['expected']=rendered_codes(expanded,bytes(m[HERO:HERO+16]));c.active['expected_colors']=rendered_codes(expanded,bytes(m[HERO:HERO+16]),m.u8[0x020000C2],m.u8[0x020000C3])
         else:
          if profile=='read-failure':reg(e,0,0xffffffff,'Controlled saved-header read failure; native empty-name fallback executes.')
          else:
           require(r[0]==0,'Native saved-header read unexpectedly failed');overrides.append(dict(address=r[13]+20,before=before.hex(),after=ids.hex(),reason='Controlled decoded saved-header name cells; no battery writes.'))
           for i,v in enumerate(ids):m.u8[r[13]+20+i]=v
        if key=='overwrite' and a==0x0801FB12:
         require(r[0]==(0 if profile=='read-failure' else 0x0200CEE8) and bytes(m[0x0200CEE8:0x0200CEFC])==expected_name.ljust(20,b'\0') and bytes(m[0x0200CEFC:0x0200CF0C])==nameguard,'Travel saved-name output/pointer/guard differs');produced.append(e)
        if a==stop+0x08000000:
         old=modals[-1]['registers'];require(r[4:12]==old[4:12] and r[13]==old[13] and r[0]==int(choice=='yes'),'Travel confirmation modal ABI/answer differs');modal_returns.append(e);jump(e,epilogue,'Native question answered; dungeon/save/progression effects excluded.')
        if a==end+0x08000000:
         old=initial[0]['registers'];require(r[4:12]==old[4:12] and r[13]==old[13] and r[1]==old[14] and bytes(m[r[13]:r[13]+32]).hex()==initial[0]['guard'],'Travel confirmation caller ABI/guard differs');returns.append(e)
        if a in (0x08001750,0x08001888):draws[:]=[d for d in draws if d['window']!=r[0]]
        if a==0x080021B4 and r[1]==address:require(bytes(m[r[0]+4:r[0]+6])==bytes((28,2)),'Travel confirmation original panel differs')
        if a==0x08001BC4 and c.active:
         w=r[0];drawkey=(w,r[1],r[13],r[14],m.u8[w+2],m.u8[w+3])
         if not draws or draws[-1]['key']!=drawkey:draws.append(dict(key=drawkey,window=w,code=r[1],x=m.u8[w+2],y=m.u8[w+3],origin=[m.u8[w],m.u8[w+1]],foreground=m.u8[0x020000C2],bank=m.u16[m.u32[w+12]]>>12))
        if a in c.ADDRESSES:c.callback(e)
       def capture(tag):
        nonlocal pixels
        g.frames(8);pic=g.capture(tag);images[tag+'.png']=digest((g.output/(tag+'.png')).read_bytes());require(draws,'Travel confirmation missing visible text')
        for d in draws:
         glyph,_=c.glyph_record(d['code']);colour=m.u16[0x05000000+2*(16*d['bank']+d['foreground'])];rgb=tuple(((colour>>s)&31)*255//31 for s in (0,5,10))
         for y,line in enumerate(glyph['rows']):
          for x,bit in enumerate(line):require((pic.getpixel((d['origin'][0]+d['x']+x,d['origin'][1]+16*d['y']+y))==rgb)==(bit=='#'),'Travel confirmation final pixels differ');pixels+=1
       with Debugger(g,cb,max_events=200000) as d:
        for a in set(c.ADDRESSES)|{0x0801DFAC,prologue+0x08000000,0x08015A34,stop+0x08000000,end+0x08000000,0x0801FAC8,0x0801FB12,0x08001750,0x08001888}:d.breakpoint(a)
        g.press('A',hold=1,wait=0);handled=False
        for tick in range(1500):
         if returns:break
         if c.reads and not c.active and not handled:
          capture('prompt');handled=True
          if choice=='no':g.press('RIGHT',wait=20);capture('no-selected')
          g.press('B' if choice=='cancel' else 'A',hold=1,wait=0)
         else:g.frames(1)
        require(handled and len(initial)==len(returns)==len(modals)==len(modal_returns)==len(c.reads)==1 and not c.active and bool(produced)==(key=='overwrite'),'Travel confirmation route incomplete')
       require(bytes(m[0x0200DF28:0x0200E888])==inventory and m.u32[hero+0x60]==gold and g.snapshot().battery==fixture.battery,'Travel confirmation changed inventory/gold/battery');results.append(dict(case=case,owner=owner,key=key,profile=profile,layout=layout,choice=choice,inputs=g.inputs,overrides=overrides,reads=c.reads,headers=headers,produced=produced,expected_name_hex=expected_name.hex(),modals=modals,modal_returns=modal_returns,returns=returns,caller_guard_abi_preserved=True,visible_pixels_checked=pixels,images=images));(out/'partial.json').write_text(json.dumps(results,indent=2)+'\n')
 report=dict(passed=True,rom_sha256=digest(rom),cases=results,scope='Three original owner frames/literal selection and native Yes/No/B modal blocks; original layouts, actual native saved header plus controlled eight-cell boundary/empty/read-failure profiles, full glyphs/centering/pixels, saved-name20-byte scratch guard and reader/modal/caller ABI. Route/gate setup and post-answer dungeon/save/progression effects explicitly skipped; no battery writes, inventory/gold unchanged.');(out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print('Travel confirmation:',len(results),'passed')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--source',type=Path,default=ROOT/'build/english');p.add_argument('--only');a=p.parse_args();run(a.source,a.only)
