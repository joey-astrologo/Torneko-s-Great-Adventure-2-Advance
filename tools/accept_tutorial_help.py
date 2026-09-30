import json
from tools.rom import ROOT,digest,require

def validate(build,receipt,counts,source=ROOT/'build/english'):
 covered=set()
 for family,count in [('tutorial-help',6),('tutorial-all-menu',27),('tutorial-bank',20),('tutorial-alternate',4)]:
  folder=source/(family+'-validation');r=json.loads((folder/'report.json').read_text());rows=r['cases'];require(r['passed'] and r['rom_sha256']==build['output_sha256'] and len(rows)==count and len({x['case'] for x in rows})==count,'Tutorial evidence stale/incomplete: '+family);require(all(x['caller_guard_abi_preserved'] and x['visible_pixels_checked'] and x['inputs'] and len(x['returns'])==3 and len(x['modals'])==len(x['modal_returns']) for x in rows),'Tutorial native ABI/menu/prose evidence incomplete');covered.update(x['id'] for c in rows for x in c['reads'])
  if family=='tutorial-help':require({x['group'] for x in rows}=={0,3,18,19,24,25} and next(x for x in rows if x['group']==18)['pages']==[18,19],'Tutorial direct prose/pages incomplete')
  elif family=='tutorial-all-menu':require({x['group'] for x in rows}==set(range(27)),'Tutorial configurations incomplete')
  elif family=='tutorial-alternate':require({x['group'] for x in rows}=={6,17,20,21},'Tutorial alternate headers incomplete')
  else:
   from tools.verify_tutorial_banks import COHORTS
   require({(x['group'],x['native_bank_loads'][0]['bank']) for x in rows}=={(i,bn) for i,nums in COHORTS.items() for bn in nums},'Tutorial bank binding cohort incomplete');groups={g['index']:g for g in build['tutorial_help']['groups']};require(all(len(x['native_bank_loads'])==len(x['fixture_bank_restores'])==3 and len(x['selections'])==len(x['modals'])==groups[x['group']]['descriptor'][7]-1 for x in rows),'Tutorial bank load/selection coverage incomplete')
  images={x['case']+'/'+p:sha for x in rows for p,sha in x['images'].items()};require(json.loads((folder/'preview.json').read_text())=={'rom_sha256':build['output_sha256'],'cases':count,'images':images},'Tutorial gallery stale')
  for p,sha in images.items():require(digest((folder/p).read_bytes())==sha,'Tutorial capture changed')
  for pattern in ('*.json','index.html','*/*.png','native/*.json'):
   for p in folder.glob(pattern):receipt['artifacts'][str(p.relative_to(ROOT))]=digest(p.read_bytes())
  counts[family]=count;receipt[family.replace('-','_')+'_scope']=r['scope']
 require({x['id'] for x in build['tutorial_help']['entries']}<=covered,'Tutorial text source coverage incomplete')
 receipt['tutorial_retained_original_mapping_gaps']=[1,2,8,9,14]
