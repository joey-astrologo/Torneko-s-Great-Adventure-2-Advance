import json
from tools.rom import ROOT,digest,require

def validate(build,receipt,counts,source=ROOT/'build/english'):
 covered=set()
 for family,count in [('tutorial-help',6),('tutorial-all-menu',27),('tutorial-bank',22),('tutorial-alternate',4)]:
  folder=source/(family+'-validation');r=json.loads((folder/'report.json').read_text());rows=r['cases'];require(r['passed'] and r['rom_sha256']==build['output_sha256'] and len(rows)==count and len({x['case'] for x in rows})==count,'Tutorial evidence stale/incomplete: '+family);require(all(x['caller_guard_abi_preserved'] and x['visible_pixels_checked'] and x['inputs'] and len(x['returns'])==3 and len(x['modals'])==len(x['modal_returns']) for x in rows),'Tutorial native ABI/menu/prose evidence incomplete');covered.update(x['id'] for c in rows for x in c['reads'])
  if family=='tutorial-help':require({x['group'] for x in rows}=={0,3,18,19,24,25} and next(x for x in rows if x['group']==18)['pages']==[18,19],'Tutorial direct prose/pages incomplete')
  elif family=='tutorial-all-menu':require({x['group'] for x in rows}==set(range(27)),'Tutorial configurations incomplete')
  elif family=='tutorial-alternate':require({x['group'] for x in rows}=={6,17,20,21},'Tutorial alternate headers incomplete')
  else:
   from tools.verify_tutorial_banks import COHORTS
   require({(x['group'],x['native_bank_loads'][0]['bank']) for x in rows}=={(i,bn) for i,nums in COHORTS.items() for bn in nums},'Tutorial bank binding cohort incomplete');groups={g['index']:g for g in build['tutorial_help']['groups']};require(all(len(x['native_bank_loads'])==len(x['fixture_bank_restores'])==3 and len(x['selections'])==len(x['modals'])==groups[x['group']]['descriptor'][7]-1 for x in rows),'Tutorial bank load/selection coverage incomplete')
   from PIL import Image
   mimic=next(x for x in rows if x['group']==14);parents=mimic.get('parent_checks',[]);closed=mimic.get('closed_display_checks',[])
   require(len(parents)==7 and {p['image'] for p in parents}=={f'{stage}-{cycle}.png' for stage in ('opened','last') for cycle in range(3)}|{'reopened-14-0.png'},'Mimic parent/cursor/reopen evidence incomplete')
   require(len({p['sha256'] for p in parents})==1 and all(p['rectangle']==[4,20,236,52] for p in parents),'Mimic header/frame/gap differs')
   for p in parents:
    with Image.open(folder/mimic['case']/p['image']) as pic:require(digest(pic.crop(tuple(p['rectangle'])).tobytes())==p['sha256'],'Mimic parent pixels changed')
   require(len(closed)==3 and {c['cycle'] for c in closed}==set(range(3)) and all(c['before']==c['after'] for c in closed),'Mimic close did not restore display layers')
  images={x['case']+'/'+p:sha for x in rows for p,sha in x['images'].items()};require(json.loads((folder/'preview.json').read_text())=={'rom_sha256':build['output_sha256'],'cases':count,'images':images},'Tutorial gallery stale')
  for p,sha in images.items():require(digest((folder/p).read_bytes())==sha,'Tutorial capture changed')
  for pattern in ('*.json','index.html','*/*.png','native/*.json'):
   for p in folder.glob(pattern):receipt['artifacts'][str(p.relative_to(ROOT))]=digest(p.read_bytes())
  counts[family]=count;receipt[family.replace('-','_')+'_scope']=r['scope']
 require({x['id'] for x in build['tutorial_help']['entries']}<=covered,'Tutorial text source coverage incomplete')
 folder=source/'tutorial-script-validation';report=json.loads((folder/'report.json').read_text())
 require(report['passed'] and report['rom_sha256']==build['output_sha256'] and len(report['cases'])==3,'Tutorial script routes stale/incomplete')
 require(report['tool_sha256']==digest((ROOT/'tools/verify_tutorial_script_routes.py').read_bytes()),'Tutorial script verifier changed')
 require({(c['bank'],c['map'],c['selector']) for c in report['cases']}=={(4,11,1),(4,11,2),(5,4,1)},'Tutorial NPC route cohort differs')
 for case in report['cases']:
  require(case['caller_guard_abi_preserved'] and case['active_bank_preserved'] and case['inventory_battery_preserved'] and case['inputs'],'Tutorial script state/ABI evidence incomplete')
  audit=case['audit'];require(not audit['unclassified_glyphs'] and not audit['unreadable_streams'] and not audit['layout_violations'],'Tutorial script has text findings')
  for name,sha in case['images'].items():
   path=folder/case['case']/name;require(digest(path.read_bytes())==sha,'Tutorial script screenshot changed');receipt['artifacts'][str(path.relative_to(ROOT))]=sha
 receipt['artifacts'][str((folder/'report.json').relative_to(ROOT))]=digest((folder/'report.json').read_bytes())
 counts['tutorial-script']=3;receipt['tutorial_script_scope']=report['scope']
 receipt['tutorial_retained_original_mapping_gaps']=[1,2,8,9]
