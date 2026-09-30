"""Representative item rows, descriptions and native formatter guard checks."""
from pathlib import Path
import json,struct,argparse
import mgba.log
from tools.numeric_checks import NumericChecks
from tools.rom import ROOT,require,digest
from tools.emulator import Session,Debugger
from tools.service_fixtures import dungeon
from tools.dialogue_checks import TextChecks,rendered_codes
from tools.dialogue_checks import player_layout_cases
from tools.name_entry import HERO
from tools.audit_menu_layouts import Observer,parent_image
from tools.compact_font import encode
from tools.numeric_font import ALIASES
from tools.verify_service_ui import materialize,cstring

OUT=ROOT/'build/english/items-validation'
STATES=('identified','equipped','cursed','unidentified','priced','maximum-fields',
        'priced-maximum','priced-equipped-maximum','priced-cursed-maximum')

def states_for(ident):
 # Spellbook2 has the native alias sentinel999, outside the155-record
 # appearance table. Clearing its known flag invents an invalid name lookup.
 # All other row states and its separate spell Info route remain required.
 return tuple(state for state in STATES if not (ident==153 and state=='unidentified'))

def required_case_names(build):
 names=[f'natural-{slot}' for slot in range(4)]
 for row in build['items']['entries']:
  if row['id'].startswith('item.name.'):
   names.extend(f"{row['id'].split('.')[-1]}-{state}" for state in states_for(int(row['id'].split('.')[-1])))
  elif row['id'].startswith('item.description.') and '{player}' in row['english']:
   names.extend(f"{row['id'].split('.')[-1]}-name-{label}" for label,_ in player_layout_cases())
 for ident,state in ((38,'ability-present'),(135,'invisible-visible')):
  if any(r['id']==f'item.name.{ident}' for r in build['items']['entries']):names.append(f'{ident}-{state}')
 return set(names)
class ItemChecks(TextChecks):
 ADDRESSES=TextChecks.ADDRESSES+(0x0800ef30,0x0800f1e8,0x0800f244,0x0800f3ac,0x0800f67e,0x08000fb8,0x08017e04,0x08017e5c,0x0805cf54,0x08017e7c,0x08017e8c,0x08022828)
 def __init__(self,g,build):
  super().__init__(g,{})
  self.names={int(r['id'].split('.')[-1]):r for r in build['items']['entries'] if r['id'].startswith('item.name.')}
  self.descriptions={r['offset']+0x8000000:r for r in build['items']['entries'] if not r['id'].startswith('item.name.')}
  self.stack=[];self.materialized={};self.formats=[];self.description_pending=None;self.item_events=[];self.repeated_item_observations=0;self.last_item_observation=None
  self.description_indices=[];self.spell_indices=[]
  self.invisible_visible=None
 def callback(self,e):
  a,r=e['address'],e['registers'];m=self.game.core.memory
  if a==0x08017e04:self.description_indices.append(r[5])
  if a==0x08022828:self.spell_indices.append(r[0])
  if a==0x0800f3ac:self.invisible_visible=bool(r[0])
  if a in (0x0800ef30,0x0800f244,0x0800f1e8,0x0800f67e):
   observation=(a,tuple(r))
   if observation==self.last_item_observation:
    self.repeated_item_observations+=1
    return  # IRQ resumed at the same pre-instruction hardware breakpoint.
   self.last_item_observation=observation
   self.item_events.append({'address':hex(a),'regs':[hex(v) for v in r],'depth':len(self.stack),'frame':e['frame']})
   self.item_events=self.item_events[-24:]
  if a in (0x0800ef30,0x0800f244):
   item=r[0];ident=m.u8[0x020013d0+m.u8[item+8]]
   if ident in self.names:
    category=__import__('tools.rom',fromlist=['load_base']).load_base()[0x141b9c+ident*24+20]
    known=bool(m.u32[0x02003bac+ident*20]&0x40000000) or category in (3,6)
    self.stack.append((a,r[1],ident,known,bytes(m[r[1]+64:r[1]+80]),r[4:12],r[13],m.u8[item+4],category,bool(m.u32[item]&0x40000000),bool(m.u32[item]&0x400000)))
   else:self.stack.append(None)
  if a in (0x0800f1e8,0x0800f67e):
   saved=self.stack.pop()
   if saved:
    entry,dest,ident,known,guard,regs,sp,amount,category,enhancement_known,inscribed=saved;raw=cstring(m,dest,256)+b'\0'
    require(len(raw)<=64 and bytes(m[dest+64:dest+80])==guard,'Item output exceeds 64-byte list allowance')
    if r[4:12]!=regs or r[13]!=sp:(self.game.output/'formatter-failure.json').write_text(json.dumps(self.item_events,indent=2)+'\n')
    require(r[4:12]==regs and r[13]==sp,'Item formatter changed stack/registers: '+repr((ident,hex(entry),hex(dest),regs,r[4:12],hex(sp),hex(r[13]))))
    if ident==135 and known and not inscribed:
     require(self.invisible_visible is not None,'Missing native invisible-item visibility result')
     if not self.invisible_visible:
      require(b'\x81\x40'*7 in raw,'Invisible item must retain its seven native blank glyphs')
      known=False
    if known:
     require(encode(self.names[ident]['english'])[:-1] in raw,'Item name was truncated or replaced')
     require(b'\x1c' not in raw and b'\x1d' not in raw,'English item row was condensed')
     visible=''.join(chr(code&255) if 0xf020<=code<=0xf07e else ALIASES.get(code,chr(code) if 32<=code<=126 else '?') for code in rendered_codes(raw))
     if category==8:require(str(amount)+' x '+self.names[ident]['english'] in visible,'Rendered arrow quantity differs from the item record')
     if category==2 and enhancement_known:
      require(self.names[ident]['english']+'['+str(amount)+']' in visible,'Rendered staff charges differ from the item record')
     if category in (3,6) and enhancement_known and amount:
      signed=amount if amount<128 else amount-256
      require(self.names[ident]['english']+('+' if signed>0 else '')+str(signed) in visible,'Rendered enhancement differs from the item record')
    self.materialized[dest]={'id':f'item-row.{ident}','encoded_hex':raw.hex(),'layout':{'pages':[[str(ident)]]}}
    self.formats.append({'item':ident,'entry':entry,'bytes':len(raw),'known_name':known,'hex':raw.hex(),'guard_preserved':True,'native_amount_byte':amount,'numeric_value_checked':known and (category==8 or (category in (2,3,6) and enhancement_known))})
  if a==0x0805cf54 and r[1] in self.descriptions:
   row=self.descriptions[r[1]];raw=bytes.fromhex(row['encoded_hex'])
   self.description_pending=(r[14]&~1,r[0],raw,row['id'],bytes(m[r[0]+256:r[0]+272]))
  if a==0x08000fb8 and (r[14]&~1)==0x08017e5c:
   args=r[2:4]+[m.u32[r[13]+i*4] for i in range(4)];template=cstring(m,r[1])+b'\0'
   raw=materialize(template,args,m)
   self.description_pending=(0x08017e5c,r[0],raw,'item-description-combined',bytes(m[r[0]+256:r[0]+272]))
  if self.description_pending and a==self.description_pending[0]:
   _,dest,raw,ident,guard=self.description_pending
   require(len(raw)<=256 and bytes(m[dest:dest+len(raw)])==raw and bytes(m[dest+256:dest+272])==guard,'Item description exceeds source/guard bounds')
   self.materialized[dest]={'id':ident,'encoded_hex':raw.hex(),'layout':{'pages':[[ident]]}};self.description_pending=None
  if a==0x080021b4 and self.active is None:
   row=self.materialized.get(r[1]);self.resources.pop(r[1],None)
   if row:
    raw=bytes.fromhex(row['encoded_hex'])
    if bytes(m[r[1]:r[1]+len(raw)])==raw:self.resources[r[1]]=row
  if a in TextChecks.ADDRESSES:super().callback(e)

def run(only=None,output=None):
 global OUT
 if output is not None:OUT=Path(output).resolve()
 elif only:OUT=ROOT/'build/english/item-probes'
 from tools.build_english import build_rom
 mgba.log.silence();rom,build=build_rom();fixture=dungeon(rom,build);rows=[]
 # Keep completed cases across interrupted runs, pinned to the ROM, fixture,
 # verifier dependencies and every capture. A failed case is never cached.
 dependencies=['verify_items','dialogue_checks','numeric_checks','verify_service_ui','emulator',
               'audit_menu_layouts','review_fonts','compact_font','service_fixtures','name_entry','numeric_font']
 cache_key=digest(json.dumps({'rom':digest(rom),'state':digest(fixture.state),'save':digest(fixture.battery),
  'tools':{name:digest((ROOT/f'tools/{name}.py').read_bytes()) for name in dependencies},
  'font':digest((ROOT/'assets/fonts/compact-english.json').read_bytes())},sort_keys=True).encode())
 cohort=[int(r['id'].split('.')[-1]) for r in build['items']['entries'] if r['id'].startswith('item.name.')]
 if only:cohort=[i for i in cohort if i in only]
 name_cases={f'name-{label}':value for label,value in player_layout_cases()}
 player_items={int(r['id'].split('.')[-1]) for r in build['items']['entries'] if r['id'].startswith('item.description.') and '{player}' in r['english']}
 cases=[(f'natural-{slot}',None,None,slot) for slot in range(4)]+[(f'{i}-{state}',i,state,0) for i in cohort for state in states_for(i)]
 if 153 in cohort:
  from tools.rom import load_base
  require(struct.unpack_from('<H',load_base(),0x141B9C+153*24+10)[0]==999,'Special spellbook alias sentinel changed')
 cases.extend((f'{i}-{state}',i,state,0) for i in cohort if i in player_items for state in name_cases)
 cases.extend((f'{i}-{state}',i,state,0) for i,state in ((38,'ability-present'),(135,'invisible-visible')) if i in cohort)
 for name,ident,state,selection in cases:
  cache_path=OUT/name/'case-report.json'
  if not only and cache_path.exists():
   cached=json.loads(cache_path.read_text())
   if cached['cache_key']==cache_key and all((ROOT/p).exists() and digest((ROOT/p).read_bytes())==h for p,h in cached['captures'].items()):
    require(cached['case']['case']==name,'Wrong cached item case')
    rows.append(cached['case']);print('Item cached',name,flush=True);continue
  with Session(rom,OUT/name) as g:
   print('Item',name,flush=True);g.restore(fixture);m=g.core.memory
   if ident is not None:
    p=0x0200df28;mapping=bytes(m[0x020013d0:0x020014d0]);item=bytearray(bytes(m[p:p+120]));flags=0xc8000000
    if 'equipped' in state:flags|=0x800000
    if 'cursed' in state:flags|=0x04000000|0x800000
    if 'priced' in state:flags|=0x100000
    if state=='unidentified':flags=0x80000000
    if state=='ability-present':flags|=0x20
    if state=='invisible-visible':m.u32[m.u32[0x02001624]+8]|=0x100000
    struct.pack_into('<I',item,0,flags);item[8]=mapping.index(ident);item[4]=99 if 'maximum' in state else 1;item[5]=1;item[24:]=bytes(96)
    # Spellbook2 uses this byte as a spell ID, not a quantity/charge count.
    if ident==153:item[4]=60 if 'maximum' in state else 1
    for n,v in enumerate(item):m.u8[p+n]=v
    type_flags=m.u32[0x02003bac+ident*20];m.u32[0x02003bac+ident*20]=(type_flags&~0x40000000) if state=='unidentified' else (type_flags|0x40000000)
    if state in name_cases:
     for n,v in enumerate(name_cases[state].ljust(16,b'\0')):m.u8[HERO+n]=v
   c=ItemChecks(g,build);o=Observer(g);numbers=NumericChecks(g)
   def cb(e):o.callback(e);c.callback(e);numbers.callback(e)
   with Debugger(g,cb,max_events=80000) as d:
    for a in set(c.ADDRESSES+o.ADDRESSES):d.breakpoint(a)
    g.press('B',hold=8,wait=120);g.press('A',wait=120)
    for _ in range(selection):g.press('DOWN',wait=20)
    g.capture('inventory');before=parent_image(g);g.press('A',wait=120);g.capture('actions')
    g.press('B',wait=120);require(parent_image(g)==before,'Item action panel did not restore its parent')
    g.press('A',wait=120)
    ids=[]
    for i in range(7):
     v=m.u16[0x0200cdd0+i*2]
     if not v:break
     ids.append(v&127)
    info_selected=40 in ids
    if info_selected:
     for _ in range(ids.index(40)):g.press('DOWN',wait=20)
     g.press('A',wait=120);g.capture('info');g.press('B',wait=120)
    g.press('B',wait=120)
   require(c.formats and c.reads and not c.active and not c.stack,'Incomplete item formatter checks')
   expected_index=1 if ident==38 and state!='ability-present' else 221 if ident==135 and state!='invisible-visible' else ident
   # Native 08019208..08019220 replaces Info with Write for these two
   # scrolls. Their descriptions exist, but this action route cannot show them.
   write_instead_of_info=ident in (124,151)
   spell_instead_of_description=ident==153
   if spell_instead_of_description:
    require(info_selected and not c.description_indices and c.spell_indices==[60 if 'maximum' in state else 1],'Native spell Info selection differs: '+name)
   elif write_instead_of_info:
    expected_action=41 if state=='unidentified' else 33
    require(not info_selected and expected_action in ids and not c.description_indices,'Native Write/Info action replacement differs: '+name)
   elif ident is not None and state!='unidentified':require(c.description_indices and set(c.description_indices)=={expected_index},'Native Info selected an unexpected description: '+name)
   description=next((row for row in build['items']['entries'] if row['id']==f'item.description.{expected_index}'),None)
   description_checked=False
   if description and state!='unidentified' and not write_instead_of_info and not spell_instead_of_description:
    expected=rendered_codes(bytes.fromhex(description['encoded_hex']),bytes(m[HERO:HERO+16]))
    require(info_selected and any(any(read['glyphs'][i:i+len(expected)]==expected for i in range(len(read['glyphs'])-len(expected)+1)) for read in c.reads),'Complete item description was not rendered: '+name)
    description_checked=True
   budgets=[]
   for read in o.reads:
    if read['window_width']!=168 or not any(encode(r['english'])[:-1].hex() in read['raw_hex'] for r in c.names.values()):continue
    colors=rendered_codes(bytes.fromhex(read['raw_hex']),foreground=15,saved=15)
    require(len(colors)==len(read['glyph_positions']),'Item glyph/budget trace differs')
    ink=[];price=[];price_cells=[]
    for (code,color),glyph in zip(colors,read['glyph_positions']):
     record,_=c.glyph_record(code);edge=max((x+1 for line in record['rows'] for x,pixel in enumerate(line) if pixel=='#'),default=0)
     if color==12:price_cells.append(glyph['x'])
     if edge:(price if color==12 else ink).append((glyph['x'],glyph['x']+edge))
    right=max((end for _,end in ink+price),default=0)
    require(right<=168,'Complete item row exceeds its window')
    if price_cells:require(max((end for _,end in ink),default=0)<=min(price_cells),'Item name overlaps price background')
    budgets.append({'ink_right':right,'text_budget':162,'name_price_separate':True,'priced':bool(price),'raw_hex':read['raw_hex']})
   rows.append({'case':name,'controlled':ident is not None,'item_id':ident,'state':state,'formats':c.formats,'reads':c.reads,'glyph_checks':c.glyph_checks,'native':o.reads,'inputs':g.inputs})
   rows[-1].update(budgets=budgets,parent_restored=True,numeric_checks=numbers.samples,repeated_item_observations=c.repeated_item_observations,info_selected=info_selected,description_indices=c.description_indices,spell_indices=c.spell_indices,complete_specific_description_checked=description_checked,description_route_exclusion='Native spell Info replaces the ordinary item description; complete spell sources have separate validation.' if spell_instead_of_description else 'Native Write action replaces Info; description consumer remains unvalidated.' if write_instead_of_info else None)
   captures={str(p.relative_to(ROOT)):digest(p.read_bytes()) for p in (OUT/name).glob('*.png')}
   require(captures,'Missing item captures')
   temporary=cache_path.with_suffix('.tmp')
   temporary.write_text(json.dumps({'cache_key':cache_key,'captures':captures,'case':rows[-1]},ensure_ascii=False)+'\n');temporary.replace(cache_path)
 report={'passed':True,'rom_sha256':digest(rom),'cases':rows,'excluded_states':[{'item_id':153,'state':'unidentified','reason':'Original definition assigns alias999, beyond the155-record table. Clearing the known flag creates an invalid pointer lookup; it is not a supported unidentified appearance.'}] if 153 in cohort else [],'scope':f'Four naturally carried items and {len(rows)-4} controlled item/state cases. Unidentified appearances have separate native source coverage. Synthetic equipped/cursed/priced combinations are format stress tests, not proof of natural acquisition. Item153 selects spell Info using its field as a valid spell ID; its invalid alias999 unidentified state is excluded explicitly. Descriptions behind Write and special replacement paths remain explicitly recorded.'}
 if not only:require({r['case'] for r in rows}==required_case_names(build),'Required item/state/name cases missing')
 (OUT/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print('Item checks:',len(rows));return report
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--item',type=int,action='append');p.add_argument('--output',type=Path);args=p.parse_args();run(args.item,args.output)
