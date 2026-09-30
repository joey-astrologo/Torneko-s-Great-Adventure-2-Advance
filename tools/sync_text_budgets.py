"""Keep the font audition's item and combat samples tied to reviewed catalogs."""
import json
from tools.rom import ROOT,require
CONFIG=ROOT/'config/font-audition.json'
def run():
 config=json.loads(CONFIG.read_text());items=json.loads((ROOT/'translations/items-review.json').read_text())['entries']
 items+=json.loads((ROOT/'translations/special-items-review.json').read_text())['entries']
 items.sort(key=lambda row:row['id'])
 config['contexts']=[c for c in config['contexts'] if c['id']!='item-names-current' and not c['id'].startswith(('item-names-cohort-','combat-current-','owned-actions-current-','contained-actions-current-','town-actions-current-','town-services-current-'))]
 for start in range(0,len(items),8):
  group=items[start:start+8]
  config['contexts'].append({'id':f'item-names-cohort-{start//8+1}','name':f'Item base names {start+1}-{start+len(group)}','stage':'current','window':168,'start':6,'end':86,'rows':8,'labels':[r['name'] for r in group],'alternatives':[],'capture':'build/english/items-validation/natural-0/inventory.png','reference':'docs/TEXT_PROGRESS.md','note':'80px base-name reserve and 31 encoded bytes. Complete 64-byte rows, markers, quantities, suffixes and prices require separate native checks. The image illustrates the native inventory, not every listed item.'})
 path=ROOT/'build/english/combat-validation/controlled/report.json'
 if path.exists():
  report=json.loads(path.read_text());build=json.loads((ROOT/'build/english/build.json').read_text());require(report['passed'] and report['rom_sha256']==build['output_sha256'],'Combat budget samples stale')
  for label in ['combat.19c-short','combat.1b4-short','combat.1a0-short','combat.1a8-short','combat.1a0-wide','combat.1a8-wide']:
   r=next(c for c in report['cases'] if c['case']==label);raw=bytes.fromhex(r['queue']['hex']);text='';i=0
   while i<len(raw):
    if raw[i]==0xf0:text+=chr(raw[i+1]);i+=2
    elif raw[i]==13:text+='\n';i+=1
    else:require(48<=raw[i]<=57,'Unexpected combat sample byte');text+=chr(raw[i]);i+=1
   config['contexts'].append({'id':'combat-current-'+label,'name':'Combat: '+label,'stage':'current','window':224,'start':0,'end':216,'rows':2,'labels':text.split('\n'),'alternatives':[],'capture':f'build/english/combat-validation/controlled/{label}/rendered.png','reference':'docs/TEXT_PROGRESS.md','note':'Native controlled combat screenshot. Lines are taken from the actual queued payload after the conditional one-line decision; names and numbers are explicit stress inputs.'})
 build=json.loads((ROOT/'build/english/build.json').read_text())
 labels={int(r['id'].split('.')[1]):r['english'] for r in build['menus']['entries'] if r['id'].startswith('action.')}
 for family,prefix in [('additional-action','owned-actions-current-'),('child-action','contained-actions-current-')]:
  report=json.loads((ROOT/f'build/english/{family}-validation/report.json').read_text())
  require(report['passed'] and report['rom_sha256']==build['output_sha256'],'Action budget samples stale')
  for case in report['cases']:
   if any(i&128 for i in case['ids']):continue
   config['contexts'].append({'id':prefix+case['case'],'name':family+': '+case['case'],'stage':'current','window':40,'start':4,'end':40,'rows':len(case['ids']),'labels':[labels[i] for i in case['ids']],'alternatives':[],'capture':f'build/english/{family}-validation/{case["case"]}/open-0.png','reference':'docs/MENU_LAYOUTS.md','note':'Native controlled action IDs with original36px region and8px border gap. Three open/cancel cycles check parent pixels, disabled states and producer buffers. This does not establish ordinary availability of every action.'})
 report=json.loads((ROOT/'build/english/town-action-validation/report.json').read_text())
 require(report['passed'] and report['rom_sha256']==build['output_sha256'],'Town menu budget samples stale')
 for name in ('trash-no','pot-filled-no'):
  case=next(c for c in report['cases'] if c['case']==name);labels=case['formats'][0]['labels']
  config['contexts'].append({'id':'town-actions-current-'+name,'name':'Town item actions: '+name,'stage':'current','window':40,'start':6,'end':40,'rows':len(labels),'labels':labels,'alternatives':[],'capture':f'build/english/town-action-validation/{name}/actions-0.png','reference':'docs/MENU_LAYOUTS.md','note':'Controlled native town inventory invocation. Original34px region,8px outer-border gap,256-byte message buffer. Trash preserves destructive discard meaning; its confirmation warns about all contents of a filled pot.'})
 from tools.town_service_budgets import append_contexts
 append_contexts(config,build)
 from tools.spell_menu_budgets import append_contexts as append_spell_contexts
 append_spell_contexts(config,build)
 from tools.skill_menu_budgets import append_contexts as append_skill_contexts
 append_skill_contexts(config,build)
 from tools.spell_item_budgets import append_contexts as append_spell_item_contexts
 append_spell_item_contexts(config,build)
 from tools.scroll_item_budgets import append_contexts as append_scroll_item_contexts
 append_scroll_item_contexts(config,build)
 from tools.saved_text_budgets import append_contexts as append_saved_contexts
 append_saved_contexts(config,build)
 from tools.input_text_budgets import append_contexts as append_input_contexts
 append_input_contexts(config,build)
 from tools.book_travel_budgets import append_contexts as append_book_travel
 append_book_travel(config,build)
 from tools.ability_info_budgets import append_contexts as append_ability_info
 append_ability_info(config,build)
 from tools.dungeon_story_budgets import append_contexts as append_dungeon_story
 append_dungeon_story(config,build)
 from tools.empty_read_budgets import append_contexts as append_empty_read
 append_empty_read(config,build)
 from tools.travel_gate_budgets import append_contexts as append_travel_gate
 append_travel_gate(config,build)
 from tools.ending_budgets import append_contexts as append_ending_text
 append_ending_text(config,build)
 from tools.dungeon_travel_budgets import append_contexts as append_dungeon_travel
 append_dungeon_travel(config,build)
 from tools.tutorial_help_budgets import append_contexts as append_tutorial_help
 append_tutorial_help(config,build)
 from tools.link_text_budgets import append_contexts as append_link_text
 append_link_text(config,build)
 from tools.ending_notice_budgets import append_contexts as append_ending_notice
 append_ending_notice(config,build)
 from tools.pickup_help_budgets import append_contexts as append_pickup_help
 append_pickup_help(config,build)
 from tools.carpenter_budgets import append_contexts as append_carpenter
 append_carpenter(config,build)
 from tools.fire_scene_budgets import append_contexts as append_fire_scene
 append_fire_scene(config,build)
 from tools.travel_confirm_budgets import append_contexts as append_travel_confirm
 append_travel_confirm(config,build)
 from tools.town_routes_budgets import append_contexts as append_town_routes
 append_town_routes(config,build)
 from tools.form_refusal_budgets import append_contexts as append_form_refusal
 append_form_refusal(config,build)
 from tools.ground_remove_budgets import append_contexts as append_ground_remove
 append_ground_remove(config,build)
 CONFIG.write_text(json.dumps(config,ensure_ascii=False,indent=2)+'\n');print('Audition contexts:',len(config['contexts']))
if __name__=='__main__':run()
