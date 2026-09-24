"""Pin the service/item/typography reports alongside cumulative acceptance."""
import json
from tools.accept_menu_layouts import run as accept_menus
from tools.rom import ROOT,digest,require

def run():
 from tools.audit_terminology import run as audit_terminology
 audit_terminology()
 receipt=accept_menus();build=json.loads((ROOT/'build/english/build.json').read_text());counts={}
 from tools.verify_items import required_case_names
 item_cases=required_case_names(build)
 for name,count in [('dungeon-ui',6),('bank',12),('bank-rewards',21),('bakery',13),('player-status',9),('player-effect',39),('item-use',60),('item-alias',166),('player-condition',45),('inventory-action',44),('pickup',36),('swap',20),('container',54),('town-action',10),('additional-action',12),('child-action',12),('player-message',216),('blacksmith',57),('items',len(item_cases)),('numeric',62),('storage',3),('storage-services',9),('bank-persistence',3)]:
  path=ROOT/f'build/english/{name}-validation/report.json';report=json.loads(path.read_text())
  require(report['passed'] and report['rom_sha256']==build['output_sha256'],'Stale service report: '+name)
  rows=report.get('cases',report.get('probes'));require(len(rows)==count,'Missing cases: '+name);counts[name]=count
  if name=='items':require({r['case'] for r in rows}==item_cases,'Required item/state/name cases missing')
  if name=='item-alias':
   require({r['alias_id'] for r in rows if r['state']=='unknown'}==set(range(154)), 'Appearance sources missing')
  if name in ('player-effect','item-use'):
   resource=build['player_effects' if name=='player-effect' else 'item_use']
   require({r['id'] for r in rows}=={r['id'] for r in resource['entries']},'Private message source coverage differs')
   require(all(sum(c['id']==r['id'] for c in rows)==(3 if name=='player-effect' else 12)
               for r in resource['entries']),'Private message name/state cases missing')
  if name in ('player-condition','inventory-action','pickup'):
   resource=build[{'player-condition':'player_conditions','inventory-action':'inventory_actions','pickup':'pickup'}[name]]
   require(len({r['case'] for r in rows})==count,'Duplicate additional consumer cases: '+name)
   require({f['id'] for r in rows for f in r['formats']}=={r['id'] for r in resource['entries']},
           'Additional consumer sources missing: '+name)
  if name=='swap':
   require({r['id'] for r in rows}=={r['id'] for r in build['swap']['entries']},'Swap sources missing')
  if name=='container':
   require({f['id'] for r in rows for f in r['formats']}=={r['id'] for r in build['containers']['entries'] if r['table_offset']!=0x38},'Container format sources missing')
   require({k['index'] for r in rows for k in r['kind_reads']}=={0,1},'Container kind labels missing')
   prefix=next(r['offset']+0x08000000 for r in build['containers']['entries'] if r['table_offset']==0x38)
   require(any(f['table_offset']==0xB4 and f['printf_arguments'][0]==prefix for r in rows for f in r['formats']),'Container floor-prefix use missing')
  if name=='town-action':
   require({r['case'] for r in rows}=={'empty','cancel','info','trash-no','trash-yes','pot-empty-no','pot-empty-yes','pot-filled-no','pot-filled-yes','view'},'Town item cases missing')
   require({r['id'] for r in build['town_actions']['entries']}<={c['id'] for r in rows for c in r['reads']},'Town item messages missing')
   require({r['english'] for r in build['town_actions']['labels']}=={label for r in rows for f in r['formats'] for label in f['labels']},'Town action labels missing')
  if name=='player-message':
   require(len({r['case'] for r in rows})==216,'Duplicate player-wrapper cases')
   require({r['id'] for r in rows if r['mapped']}=={r['id'] for r in build['player_messages']['entries']},'Player-wrapper sources missing')
   require({r['id'] for r in rows if not r['mapped']}=={'fallback-english','fallback-japanese','fallback-ram'},'Player-wrapper fallbacks missing')
   from tools.dialogue_checks import player_layout_cases
   expected={(label,flag) for label,_ in player_layout_cases() for flag in (0,1)}
   for ident in {r['id'] for r in rows}:
    require({(r['player_case'],r['queue_flag']) for r in rows if r['id']==ident}==expected,'Player-wrapper name/flag cases missing')
  if name=='blacksmith':
   require(len({r['case'] for r in rows})==57 and {r['id'] for r in rows}=={r['id'] for r in build['blacksmith']['entries']},'Blacksmith source cases missing')
   transaction_path=ROOT/'build/english/blacksmith-validation/transactions.json'
   transactions=json.loads(transaction_path.read_text())
   require(transactions['passed'] and transactions['rom_sha256']==build['output_sha256'],'Blacksmith transactions stale')
   require(len(transactions['cases'])==13 and {r['case'] for r in transactions['cases']}=={'jobs-'+str(i) for i in [0]+list(range(9,100,10))+[119,120]},'Blacksmith exchange/tip/cap cases missing')
   counts['blacksmith-transactions']=13
   receipt['artifacts'][str(transaction_path.relative_to(ROOT))]=digest(transaction_path.read_bytes())
  if name in ('additional-action','child-action'):
   from tools.menu_text import ACTIONS
   for disabled in (False,True):
    require({i&127 for r in rows for i in r['ids'] if bool(i&128)==disabled}==set(ACTIONS),'Owned action label/state missing')
  if name in ('swap','container','town-action','additional-action','child-action','player-message','blacksmith'):
   require(len({r['case'] for r in rows})==count,'Duplicate extra menu/action cases')
  receipt['artifacts'][str(path.relative_to(ROOT))]=digest(path.read_bytes())
 for relative,expected in [('build/english/monster-validation/report.json',2),('build/english/combat-validation/actor-levels.json',12),('build/english/combat-validation/controlled/report.json',173),('build/english/combat-validation/misses/report.json',149)]:
  path=ROOT/relative;report=json.loads(path.read_text())
  require(report['passed'] and report['rom_sha256']==build['output_sha256'] and len(report['cases'])==expected,'Stale combat/name report: '+relative)
  receipt['artifacts'][relative]=digest(path.read_bytes())
  counts[relative]=expected
 receipt.update(service_native_cases=counts,reviewed_ui_resources=len(build['ui']['entries']),
                reviewed_bank_resources=len(build['dialogue']['town_resource']['service_entries']),
                reviewed_item_resources=len(build['items']['entries']),compact_numeric_aliases=38,
                reviewed_actor_names=len(build['monsters']['entries']),reviewed_combat_formats=len(build['combat']['entries']),
                english_item_spacing=0,english_word_space_px=3,storage_subset_complete=True, bakery_complete=False,bakery_consumer_resources=len(build['dialogue']['town_resource']['bakery_entries']),
                reviewed_player_status_resources=len(build['player_status']['entries']),
                reviewed_player_effect_resources=len(build['player_effects']['entries']),
                reviewed_item_use_resources=len(build['item_use']['entries']),
                reviewed_item_appearance_resources=len(build['aliases']['entries']),
                reviewed_player_condition_resources=len(build['player_conditions']['entries']),
                reviewed_inventory_action_resources=len(build['inventory_actions']['entries']),
                reviewed_pickup_resources=len(build['pickup']['entries']),
                reviewed_player_message_resources=len(build['player_messages']['entries']),
                reviewed_blacksmith_resources=len(build['blacksmith']['entries']),
                reviewed_swap_resources=len(build['swap']['entries']),
                reviewed_container_resources=len(build['containers']['entries'])+len(build['containers']['labels']),
                reviewed_town_action_resources=len(build['town_actions']['entries'])+len(build['town_actions']['labels']),
                contained_action_buffer_bytes=build['child_actions']['output_capacity'],
                reviewed_story_resources=sum(len(r['entries']) for r in build['dialogue'].get('story_consumers',{}).values())+sum(r['batch']=='event-prose' for r in build['dialogue']['entries']),
                reviewed_private_well_labels=len(build.get('well_level',{}).get('labels',[])),
                reviewed_storage_resources=len(build['dialogue']['town_resource']['storage_entries']), total_reviewed_inserted_resources=build['total_reviewed_inserted_resources'])
 for pattern in ['build/combat/index.html','build/combat/preview.json','build/english/combat-validation/controlled/*/*.png','build/english/combat-validation/misses/*/*.png','build/english/combat-validation/misses/native/provenance.json','build/english/combat-validation/misses/player-branch/provenance.json','build/typography/*.json','build/typography/*.html','build/typography/before/*.png',
                 'build/english/dungeon-ui-validation/*/*.png','build/english/bank-validation/*/*.png','build/english/bakery-validation/*/*.png','build/english/bakery-validation/native/provenance.json','build/english/player-status-validation/*/*.png','build/english/player-status-validation/native/provenance.json','build/english/bank-rewards-validation/*/*.png','build/english/bank-rewards-validation/native/provenance.json',
                 'build/english/item-alias-validation/*/*.png','build/english/item-alias-validation/native/provenance.json',
                 'build/english/player-effect-validation/*/*.png','build/english/player-effect-validation/native/provenance.json',
                 'build/english/item-use-validation/*/*.png','build/english/item-use-validation/native/provenance.json',
                 'build/english/item-alias-validation/index.html','build/english/item-alias-validation/preview.json',
                 'build/english/player-effect-validation/index.html','build/english/player-effect-validation/preview.json',
                 'build/english/item-use-validation/index.html','build/english/item-use-validation/preview.json',
                 'build/english/items-validation/*/*.png','build/english/storage-services-validation/*/*.png','build/english/bank-persistence-validation/*/*.png','build/text-inventory/*.json','build/item-extraction/catalog.json','build/services/index.html','build/services/preview.json','build/services/storage-native/report.json','build/services/storage-native/storage-ready.sav','build/english/storage-validation/report.json','build/english/storage-validation/*/*.png','config/routes/storage-japanese.json']:
  for p in ROOT.glob(pattern):receipt['artifacts'][str(p.relative_to(ROOT))]=digest(p.read_bytes())
 for family in ('story-command','player-condition','inventory-action','pickup','swap','container','town-action','additional-action','child-action','player-message','blacksmith'):
  for pattern in ('report.json','index.html','preview.json','*/*.png','native/*.json'):
   for p in (ROOT/f'build/english/{family}-validation').glob(pattern):
    receipt['artifacts'][str(p.relative_to(ROOT))]=digest(p.read_bytes())
 from tools.accept_town_services import validate as validate_town_services
 validate_town_services(build,receipt,counts)
 from tools.accept_additional_text import validate as validate_additional_text
 validate_additional_text(build,receipt,counts)
 from tools.accept_trap_text import validate as validate_trap_text
 validate_trap_text(build,receipt,counts)
 from tools.accept_results import validate as validate_results
 validate_results(build,receipt,counts)
 from tools.accept_records import validate as validate_records
 validate_records(build,receipt,counts)
 from tools.accept_monster_effects import validate as validate_monster_effects
 validate_monster_effects(build,receipt,counts)
 from tools.accept_queue_notices import validate as validate_queue_notices
 validate_queue_notices(build,receipt,counts)
 storage=json.loads((ROOT/'build/english/storage-validation/report.json').read_text());native=json.loads((ROOT/'build/services/storage-native/report.json').read_text())
 require(storage['persistence']['passed'] and native['passed'] and storage['source_save_sha256']==native['save_sha256'],'Storage save provenance/persistence missing')
 require(native['recipe_sha256']==digest((ROOT/'config/routes/storage-japanese.json').read_bytes()),'Storage recipe stale')
 receipt['scope']='Cumulative early-game text and typography build. Case counts are recorded by family above. Ordinary storage sales/empty-inventory, controlled capacity/filled-pot branches, native storage persistence and native bank deposit/withdrawal persistence pass. Sacred-flame dialogue rendering is checked separately with controlled reader arguments; ordinary English quest completion remains unaccepted. All 141 dungeon actor-name pointers and 322 controlled combat display cases pass (173 core and 149 misses); ordinary progression is limited to the recorded routes. All 206 reviewed item names pass nine row states plus natural and maximum-player-name Info cases. Twenty-one controlled bank reward cases check the explicitly enabled reward branch, gifts and full-inventory refusal. Thirteen controlled bakery calls validate all three purchases, cancellation and capacity/gold limits; nine player-status cases validate single-line hallucination, blindness and refusal. All 154 private appearance labels pass 166 controlled native row/state cases. Thirteen additional player-effect reads pass 39 one-line cases; five item-use formats pass 60 conditional join/fallback and colour cases. Story coverage includes 874 ordinary prose sources, 33 owned formatted/command sources, ten well labels and all seven native bank/getter paths, with ordinary later-story progression separately scoped. Fifteen additional story A-jingle streams pass45 native wrapper cases. Nine player conditions pass45 cases/48 one-line messages; nine equipment/removal/drop sources pass44 cases/48 messages; six pickup sources pass36 cases including native gold/arrow/inventory outcomes and the separately controlled automatic-walk wrapper. Five Swap formats pass20 native exchange/refusal cases;15 pot resources pass54 transfer/refusal cases with conserved identities and complete floor prefixes. All39 labels in the owned action copy pass12 grouped enabled/disabled cases in each of two producers. The separate contained-item producer has checked256/64-byte output/scratch regions and original window geometry. Six town inventory resources pass10 controlled invocation cases for View/Trash/Info, empty inventory, cancellation and filled-pot discard warnings. Thirty-three player-name-wrapper messages pass216 mapping/name/queue-flag/fallback cases in the original256-byte output. The private blacksmith table adds43 sources with57 rendering/formatter cases and13 native exchange/tip/counter-cap cases from controlled inventory and service entry; its largest formatted result is464 bytes within512. Ordinary blacksmith unlocking and unowned sources1/2/68 remain separate. Original192/256-byte item-message buffers and64-byte item fields are preserved. Ordinary bakery unlocking and saved purchases, randomized appearance discovery, custom names, inscriptions, special item records, remaining combat, later text consumers and modes remain open.'
 receipt['scope']+=' Private synthesis/selector and Remi consumers add105 resources with72 and170 native cases respectively; see town_services_scope for the explicit progression/save exclusions.'
 receipt['scope']+=' Eighteen village-name/well-picker/hunger/status-trap bindings pass65 additional native cases; see additional_text_scope for controlled setup and progression exclusions.'
 receipt['scope']+=' Thirty-seven further trap/rust bindings pass71 native cases; see trap_text_scope for actual mechanics, field boundaries and explicit controlled-setup exclusions.'
 path=ROOT/'docs/english-services-validation.json';path.write_text(json.dumps(receipt,indent=2)+'\n');print(path)
 return receipt
if __name__=='__main__':run()
