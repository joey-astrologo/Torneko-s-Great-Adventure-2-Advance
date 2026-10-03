"""Join bounded source families without confusing discovery with translation coverage."""
import json
from collections import Counter
from tools.rom import ROOT,digest,load_base,require
from tools.opening_text import banks
from tools.event_text import table_entries
from tools.town_text import entries as town_entries,resource
from tools.extract_items import extract
from tools.extract_monsters import extract as extract_monsters
from tools.extract_item_aliases import extract as extract_aliases
from tools.extract_shared_text import extract as extract_shared
from tools.extract_item_use import extract as extract_item_use
from tools.text_codec import readable,source_bytes
OUT=ROOT/'build/text-inventory'

def run():
 rom=load_base();master=json.loads((ROOT/'translations/master.json').read_text());known={r['id']:r for r in master['entries']};rows={}
 def retain(ident,family,raw,japanese,reference):
  row=rows.setdefault(ident,{'id':ident,'family':family,'source_sha256':digest(raw),'raw_hex':raw.hex(),'japanese':japanese,'references':[],'english':None,'language_status':'untranslated','native_observed':False})
  require(row['raw_hex']==raw.hex(),'Conflicting source identity');row['references'].append(reference)
  if ident in known:
   k=known[ident];require(k['raw_hex']==raw.hex(),'Native source identity differs')
   row.update(english=k['english'],language_status=k['language_status'],native_observed=True)
  return row
 for bank in banks():
  for t in table_entries(bank):
   raw=source_bytes(t['tokens']);require(raw==bank['data'][t['start']:t['end_exclusive']],'Event round trip differs')
   retain(t['id'],'event',raw,readable(t['tokens']),{k:t[k] for k in ['slot','group','index']}|{'bank':bank['id']})
 for t in town_entries():
  raw=source_bytes(t['tokens']);require(raw==resource()['data'][t['start']:t['end_exclusive']],'Town round trip differs')
  retain(t['id'],'town',raw,readable(t['tokens']),{'slot':t['slot'],'index':t['index']})
 item_catalog=extract();review=json.loads((ROOT/'translations/items-review.json').read_text())
 extra_items=json.loads((ROOT/'translations/special-items-review.json').read_text())
 require(extra_items['base_rom_sha256']==digest(rom),'Special item base differs')
 items={r['id']:r for r in review['entries']+extra_items['entries']}
 for item in item_catalog['items']:
  for kind in ('name','description','category_description'):
   src=item[kind]
   if not src:continue
   row=retain(f"rom.{src['offset']:08x}",'item',bytes.fromhex(src['raw_hex']),src['japanese'],{'item':item['id'],'kind':kind,'category':item['category']})
   reviewed_item=items.get(item['id'],{})
   if reviewed_item:require(reviewed_item['name_source']==item['name'] and reviewed_item['description_source']==item['description'],'Item inventory review/source differs')
   translated=reviewed_item.get(kind) if kind!='category_description' else review['category_descriptions'].get(str(item['category']))
   if translated:row.update(english=translated,language_status='reviewed')
 special=item_catalog['special_description_221']
 if special:
  row=retain(f"rom.{special['offset']:08x}",'item',bytes.fromhex(special['raw_hex']),special['japanese'],{'kind':'invisible-item-fallback','description_index':221})
  reviewed=next((r for r in review.get('special_descriptions',[]) if r['id']==221),None)
  if reviewed:
   require(reviewed['source']==special,'Special description review differs')
   row.update(english=reviewed['english'],language_status=reviewed['status'])
 aliases=extract_aliases()
 for alias in aliases['entries']:
  src=alias['name']
  retain(f"rom.{src['offset']:08x}",'item-appearance',bytes.fromhex(src['raw_hex']),src['japanese'],{'alias':alias['id'],'category':alias['category'],'disposition':alias['disposition']})
 for label in aliases['category_labels']:
  src=label['source']
  retain(f"rom.{src['offset']:08x}",'item-category-label',bytes.fromhex(src['raw_hex']),src['japanese'],{'category':label['category'],'pointer_offset':label['pointer_offset']})
 custom=json.loads((ROOT/'translations/custom-items-review.json').read_text())
 require(custom['base_rom_sha256']==digest(rom),'Custom item inventory base differs')
 for reviewed in custom['labels']+custom['entries']:
  src=reviewed['source'];raw=bytes.fromhex(src['raw_hex'])
  require(rom[src['offset']:src['offset']+len(raw)]==raw and digest(raw)==src['sha256'],'Custom item inventory source differs')
  row=retain(f"rom.{src['offset']:08x}",'custom-item-format',raw,src['japanese'],{'review':'custom-items-review.json','resource':reviewed['id']})
  row.update(english=reviewed['english'],language_status=reviewed['status'])
  row.setdefault('reviewed_variants',[]).append({'resource':reviewed['id'],'english':reviewed['english'],'scope':'Private custom-item category/format readers; native consumer acceptance is recorded separately.'})
 monsters=extract_monsters();monster_review={r['id']:r for r in json.loads((ROOT/'translations/monsters-review.json').read_text())['entries']}
 for actor in monsters['entries']:
  for kind in ('raw_table','dungeon'):
   src=actor[kind];ident=f"rom.{src['offset']:08x}" if kind=='raw_table' else f"dungeon-data.{src['offset']:08x}"
   row=retain(ident,'actor-name',bytes.fromhex(src['raw_hex']),src['japanese'],{'actor':actor['id'],'kind':kind})
   translated=monster_review[actor['id']]
   row.update(english=translated['english' if kind=='raw_table' else 'dungeon_english'],language_status=translated['status'],source_evidence='Bounded raw table / original native relocated dungeon data; renderer reachability is separate.')
 for reviewed in json.loads((ROOT/'translations/combat-review.json').read_text())['entries']:
  src=reviewed['source'];row=retain(f"rom.{src['offset']:08x}",'combat',bytes.fromhex(src['raw_hex']),src['japanese'],{'table_offset':reviewed['table_offset']})
  row.update(english=reviewed['english'],language_status=reviewed['status'])
 for entry in extract_shared()['entries']:
  src=entry['source']
  retain(f"rom.{src['offset']:08x}",'shared-system',bytes.fromhex(src['raw_hex']),src['japanese'],{'shared_table_offset':entry['table_offset'],'pointer_offset':entry['pointer_offset']})
 for entry in extract_item_use()['entries']:
  src=entry['source']
  retain(f"rom.{src['offset']:08x}",'item-use',bytes.fromhex(src['raw_hex']),src['japanese'],{'category':entry['category'],'pointer_offset':entry['pointer_offset']})
 from tools.extract_spells import extract as extract_spells
 spell_catalog=json.loads((ROOT/'translations/spells-review.json').read_text())
 spell_reviews={r['id']:r for r in spell_catalog['entries']}
 require(spell_catalog['base_rom_sha256']==digest(rom),'Spell inventory base differs')
 for spell in extract_spells()['entries']:
  reviewed=spell_reviews[spell['id']]
  require(all(reviewed[k]==v for k,v in spell.items()),'Spell inventory review/source differs')
  for kind in ('name','description'):
   src=spell[kind+'_source'];row=retain(f"rom.{src['offset']:08x}",'spell',bytes.fromhex(src['raw_hex']),src['japanese'],{'spell':spell['id'],'kind':kind,'menu_eligible':spell['menu_eligible']})
   row.update(english=reviewed[kind],language_status=reviewed['status'])
   row.setdefault('reviewed_variants',[]).append({'resource':f"spell.{kind}.{spell['id']}",'english':reviewed[kind],'scope':'Language review; isolated Info prototype and other spell consumers are separately validated.'})
 for reviewed in spell_catalog['ui_entries']:
  src=reviewed['source'];row=rows[f"rom.{src['offset']:08x}"]
  require(row['raw_hex']==src['raw_hex'],'Spell UI inventory identity differs')
  row.update(english=reviewed['english'],language_status=reviewed['status'])
  row.setdefault('reviewed_variants',[]).append({'resource':reviewed['id'],'english':reviewed['english'],'scope':'Owned spell Info prototype; other shared consumers retain their original text.'})
 from tools.extract_skills import extract as extract_skills
 skill_catalog=json.loads((ROOT/'translations/skills-review.json').read_text())
 skill_reviews={r['id']:r for r in skill_catalog['entries']}
 require(skill_catalog['base_rom_sha256']==digest(rom),'Skill inventory base differs')
 for skill in extract_skills()['entries']:
  reviewed=skill_reviews[skill['id']]
  require(all(reviewed[k]==v for k,v in skill.items()),'Skill inventory review/source differs')
  for kind in ('name','description'):
   src=skill[kind+'_source'];row=retain(f"rom.{src['offset']:08x}",'skill',bytes.fromhex(src['raw_hex']),src['japanese'],{'skill':skill['id'],'kind':kind,'menu_eligible':skill['menu_eligible']})
   row.update(english=reviewed[kind],language_status=reviewed['status'])
   row.setdefault('reviewed_variants',[]).append({'resource':f"skill.{kind}.{skill['id']}",'english':reviewed[kind],'scope':'Language review; skill Info prototype and other consumers are separately validated. Naming confidence remains explicit in skills-review.json.'})
 for reviewed in skill_catalog['ui_entries']+skill_catalog['literal_entries']:
  src=reviewed['source'];row=retain(f"rom.{src['offset']:08x}",'skill-ui',bytes.fromhex(src['raw_hex']),src['japanese'],{'resource':reviewed['id']})
  row.update(english=reviewed['english'],language_status=reviewed['status'])
  row.setdefault('reviewed_variants',[]).append({'resource':reviewed['id'],'english':reviewed['english'],'scope':'Owned skill Info prototype; other shared consumers remain separate.'})
 from tools.extract_action_labels import extract as extract_actions
 from tools.container_text import kind_sources
 for entry in extract_actions()['entries']:
  if entry['disposition']!='label':continue
  src=entry['source']
  retain(f"rom.{src['offset']:08x}",'menu-ui',bytes.fromhex(src['raw_hex']),src['japanese'],{'action_id':entry['index'],'pointer_offset':entry['pointer_offset']})
 for entry in kind_sources(rom):
  src=entry['source']
  retain(f"rom.{src['offset']:08x}",'container-kind',bytes.fromhex(src['raw_hex']),src['japanese'],{'container_kind':entry['index'],'pointer_offset':entry['pointer_offset']})
 for filename in ('menus-review.json','dungeon-ui-review.json','options-help-review.json'):
  for reviewed in json.loads((ROOT/'translations'/filename).read_text())['entries']:
   offset=reviewed['source'];offset=offset-0x8000000 if offset>=0x8000000 else offset
   raw=bytes.fromhex(reviewed['source_hex']);require(rom[offset:offset+len(raw)]==raw,'UI source review differs')
   row=retain(f'rom.{offset:08x}','menu-ui',raw,reviewed['japanese'],{'review':filename,'resource':reviewed['id']})
   row.setdefault('reviewed_variants',[]).append({'resource':reviewed['id'],'english':reviewed['english'],'scope':'Language review for owned consumers; other shared consumers may still use Japanese.'})
   if row['language_status']=='untranslated':row.update(english=reviewed['english'],language_status=reviewed['status'])
 for row in master['entries']:
  if row['id'] not in rows:retain(row['id'],'other-native',bytes.fromhex(row['raw_hex']),row['japanese'],{'source':row['source']})
 for filename in ['storage-review.json','bank-review.json','bakery-review.json']:
  for reviewed in json.loads((ROOT/'translations'/filename).read_text())['entries']:
   for row in rows.values():
    if row['family']=='town' and row['source_sha256']==reviewed['source_sha256']:
     row.update(english=reviewed['english'],language_status=reviewed['status'])
 for reviewed in json.loads((ROOT/'translations/player-status-review.json').read_text())['entries']:
  source=reviewed['source'];ident=f"rom.{source['offset']:08x}";row=rows[ident]
  require(row['raw_hex']==source['raw_hex'] and row['source_sha256']==source['sha256'],'Player-status review source differs')
  row.update(english=reviewed['english'],language_status=reviewed['status'])
  row.setdefault('reviewed_variants',[]).append({'resource':reviewed['id'],'english':reviewed['english'],'scope':'Private player-status consumer table only; other shared consumers retain their original pointers.'})
 for filename in ('event-prose-review.json','floor-progress-review.json','well-level-review.json','village-prose-review.json','medal-review.json','story-commands-review.json'):
  catalog=json.loads((ROOT/'translations'/filename).read_text())
  for reviewed in catalog['entries']:
   row=rows[reviewed['id']]
   require(row['raw_hex']==reviewed['source_hex'] and row['source_sha256']==reviewed['source_sha256'],'Story review source differs')
   row.update(english=reviewed['english'],language_status=reviewed['status'])
   row.setdefault('reviewed_variants',[]).append({'resource':reviewed['id'],'review':filename,'scope':'Language review and owned story consumer; ordinary later-story progression is separately reported.'})
   if reviewed.get('editorial_reconstruction'):
    row['editorial_reconstruction']=reviewed['editorial_reconstruction']
  for label in catalog.get('labels',[]):
   raw=bytes.fromhex(label['source_hex']);offset=label['source_offset']
   require(rom[offset:offset+len(raw)]==raw and digest(raw)==label['source_sha256'],'Story field label source differs')
   row=retain(f'rom.{offset:08x}','story-field-label',raw,label['japanese'],{'review':filename,'resource':label['id']})
   row.update(english=label['english'],language_status=label['status'])
   row.setdefault('reviewed_variants',[]).append({'resource':label['id'],'english':label['english'],'scope':'Private well acknowledgement labels; original level-selection menu remains separate.'})
 for reviewed in json.loads((ROOT/'translations/item-aliases-review.json').read_text())['entries']:
  source=reviewed['source']['name'];row=rows[f"rom.{source['offset']:08x}"]
  require(row['raw_hex']==source['raw_hex'] and row['source_sha256']==source['sha256'],'Appearance review source differs')
  row.update(english=reviewed['name'],canonical_name=reviewed['canonical_name'],language_status=reviewed['status'])
  row.setdefault('reviewed_variants',[]).append({'resource':'item-appearance-'+str(reviewed['id']),'english':reviewed['name'],'scope':'Private unidentified-name consumer prototype; insertion in the cumulative ROM and ordinary discovery are separate.'})
 for filename in ('player-effects-review.json','item-use-review.json','player-conditions-review.json','inventory-actions-review.json','pickup-review.json','swap-review.json','container-review.json','player-messages-review.json','selection-prompts-review.json','remi-warp-names-review.json','well-picker-review.json','hunger-review.json','status-traps-review.json','warp-trap-review.json','unequip-trap-review.json','mud-trap-review.json','damage-traps-review.json','rust-review.json','summon-trap-review.json','blast-traps-review.json','pitfall-review.json','queue-notices-review.json','bear-trap-review.json','stumble-trap-review.json','curse-review.json','drain-review.json','level-drain-review.json','steal-gold-review.json','monster-conditions-review.json','results-review.json','history-review.json','history-menu-review.json','records-review.json','password-review.json','priest-review.json','projectile-review.json','monster-announcements-review.json','companion-review.json','recovery-review.json','soldier-review.json','spell-menu-review.json','item-theft-review.json','skill-menu-review.json','dungeon-leaves-review.json','floor-buff-review.json','fullness-review.json','status-effects-review.json','spell-item-review.json','spell-messages-review.json','discovery-messages-review.json','monster-interactions-review.json','staff-use-review.json','scroll-item-review.json','writing-review.json','item-loss-review.json','player-notices-review.json','skill-messages-review.json','battle-results-review.json','dungeon-shop-review.json','save-notices-review.json','reference-lists-review.json','priest-warning-review.json','save-preview-review.json','town-root-review.json','fused-loss-review.json','cannot-talk-review.json','step-stairs-review.json','pot-view-review.json','book-travel-review.json','ability-info-review.json','dungeon-story-review.json','empty-read-review.json','travel-gate-review.json','ending-review.json','dungeon-travel-review.json','tutorial-help-review.json','link-text-review.json','ending-notice-review.json','pickup-help-review.json','carpenter-review.json','fire-scene-review.json','travel-confirm-review.json','town-routes-review.json','form-refusal-review.json','ground-remove-review.json','monster-identity-review.json','status-expiry-review.json','caller-repairs-review.json','remaining-callers-review.json','wind-review.json','town-overview-review.json'):
  catalog=json.loads((ROOT/'translations'/filename).read_text())
  for reviewed in catalog['entries']+catalog.get('ui_entries',[])+catalog.get('abilities',[]):
   source=reviewed['source']
   if f"rom.{source['offset']:08x}" not in rows:
    raw=bytes.fromhex(source['raw_hex']);offset=source['offset']
    require(rom[offset:offset+len(raw)]==raw and digest(raw)==source['sha256'],'Private literal source differs')
    retain(f'rom.{offset:08x}','private-literal',raw,source['japanese'],{'review':filename,'resource':reviewed['id']})
   row=rows[f"rom.{source['offset']:08x}"]
   require(row['raw_hex']==source['raw_hex'] and row['source_sha256']==source['sha256'],'Private message review source differs')
   row.update(english=reviewed['english'],language_status=reviewed['status'])
   row.setdefault('reviewed_variants',[]).append({'resource':reviewed['id'],'review':filename,'english':reviewed['english'],'scope':'Language review for an isolated consumer prototype; cumulative insertion and ordinary progression are separately reported.'})
 inscription=json.loads((ROOT/'translations/writing-input-review.json').read_text())
 require(inscription['base_rom_sha256']==digest(rom),'Inscription source base differs')
 for table in inscription['tables']:
  require(digest(rom[table['source_offset']:table['end_exclusive']])==table['source_sha256'],'Inscription table source differs')
  for entry in table['original_entries']:
   src=entry['source'];raw=bytes.fromhex(src['raw_hex']);offset=src['offset']
   require(rom[offset:offset+len(raw)]==raw and digest(raw)==src['sha256'] and entry['status']=='reviewed','Inscription source review differs')
   row=retain(f'rom.{offset:08x}','writing-input',raw,src['japanese'],{'review':'writing-input-review.json','family':table['family'],'target':entry['target']})
   if row['language_status']=='untranslated':row.update(english=' / '.join(entry['english_aliases']),language_status='reviewed')
   row.setdefault('reviewed_variants',[]).append({'english_aliases':entry['english_aliases'],'scope':'English input aliases map to the original target; original kana spellings remain accepted for compatibility.'})
 for filename in ('town-prose-review.json','blacksmith-review.json','gaibara-review.json','remi-review.json','mayor-review.json'):
  for reviewed in json.loads((ROOT/'translations'/filename).read_text())['entries']:
   row=rows[reviewed.get('source_id',reviewed['id'])]
   require(row['raw_hex']==reviewed['source_hex'] and row['source_sha256']==reviewed['source_sha256'],'Town prose/service source differs')
   row.update(english=reviewed['english'],language_status=reviewed['status'])
   row.setdefault('reviewed_variants',[]).append({'resource':reviewed['id'],'review':filename,'english':reviewed['english'],'scope':'Language review for a private town-service consumer. Insertion, native service coverage, other consumers and ordinary progression are separately reported.'})
 town_actions=json.loads((ROOT/'translations/town-actions-review.json').read_text())
 for reviewed in town_actions['entries']:
  row=rows[reviewed['id']]
  require(row['raw_hex']==reviewed['source_hex'] and row['source_sha256']==reviewed['source_sha256'],'Town item review source differs')
  row.update(english=reviewed['english'],language_status=reviewed['status'])
  row.setdefault('reviewed_variants',[]).append({'resource':reviewed['id'],'english':reviewed['english'],'scope':'Private town inventory consumer only; original town table and other consumers remain separate.'})
 for filename in ('container-review.json','town-actions-review.json'):
  for reviewed in json.loads((ROOT/'translations'/filename).read_text())['labels']:
   src=reviewed['source'];row=rows[f"rom.{src['offset']:08x}"]
   require(row['raw_hex']==src['raw_hex'] and row['source_sha256']==src['sha256'],'Private label review source differs')
   row.update(english=reviewed['english'],language_status=reviewed['status'])
   row.setdefault('reviewed_variants',[]).append({'resource':reviewed['id'],'english':reviewed['english'],'scope':'Owned private container kind / town action consumer only.'})
 fixed=json.loads((ROOT/'translations/results-review.json').read_text())['history_zero_actor']
 src=fixed['source'];row=retain(f"rom.{src['offset']:08x}",'result-field',bytes.fromhex(src['raw_hex']),src['japanese'],{'review':'results-review.json','kind':'history-zero-actor'})
 row.update(english=fixed['english'],language_status=fixed['status'])
 dispositions=json.loads((ROOT/'translations/source-dispositions-review.json').read_text())
 require(dispositions['base_rom_sha256']==digest(rom),'Source disposition base differs')
 require(len({r['id'] for r in dispositions['entries']})==len(dispositions['entries']),'Duplicate source dispositions')
 for disposition in dispositions['entries']:
  row=rows[disposition['id']]
  require(disposition['language_status'] in ('reviewed','retained-nonlinguistic','retained-japanese','replaced-by-component'),'Unknown source disposition')
  require(all(row[k]==disposition[k] for k in ('raw_hex','source_sha256','japanese')) and digest(bytes.fromhex(row['raw_hex']))==row['source_sha256'],'Source disposition differs from extracted bytes')
  require(row['language_status'] in ('untranslated',disposition['language_status']),'Source disposition conflicts with existing review')
  row.update(english=disposition['english'],language_status=disposition['language_status'],disposition_reason=disposition['reason'],disposition_evidence=disposition['evidence'],disposition_reachability=disposition['reachability'])
 rows=sorted(rows.values(),key=lambda r:r['id']);OUT.mkdir(parents=True,exist_ok=True)
 report={'source_rom_sha256':digest(rom),'unique_sources':len(rows),'source_families':dict(Counter(r['family'] for r in rows)),'language_status':dict(Counter(r['language_status'] for r in rows)),'native_observed':sum(r['native_observed'] for r in rows),'scope':'Seven event banks, shared town table, 654 shared system/combat/menu pointers, 221 item definitions and descriptions plus the invisible-item fallback, 154 unidentified appearances with an end marker and 14 category-label pointers, both 141-ID actor-name tables, 61 spell definitions and Info descriptions, 128 skill definitions and Info descriptions, five category-indexed item-use sources,40 nonempty original action-label IDs in45 slots, two container-kind labels, nine town-overview descriptor labels, computed wind expulsion and owned menu/UI reviews. Not all game text: other tables/consumers and unclassified scan leads remain to be accounted for. Language review is separate from insertion/native acceptance and does not establish translation of every shared consumer.'}
 (OUT/'catalog.json').write_text(json.dumps({'report':report,'entries':rows},ensure_ascii=False,indent=2)+'\n');(OUT/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2));return report
if __name__=='__main__':run()
