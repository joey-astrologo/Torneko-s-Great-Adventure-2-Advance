import json
from tools.rom import ROOT,digest,require

def validate(build,receipt,counts,source=ROOT/'build/english'):
 folder=source/'ending-notice-validation';r=json.loads((folder/'report.json').read_text());rows=r['cases'];require(r['passed'] and r['rom_sha256']==build['output_sha256'] and {x['case'] for x in rows}=={'A','B'} and len(rows)==2,'Ending notice evidence stale/incomplete');require(all(x['caller_guard_abi_preserved'] and x['visible_pixels_checked'] and len(x['modals'])==len(x['modal_returns'])==len(x['returns'])==1 for x in rows),'Ending notice native checks incomplete');require({x['id'] for c in rows for x in c['reads']}=={x['id'] for x in build['ending_notice']['entries']},'Ending notice source coverage incomplete');images={x['case']+'/'+p:sha for x in rows for p,sha in x['images'].items()};require(json.loads((folder/'preview.json').read_text())=={'rom_sha256':build['output_sha256'],'cases':2,'images':images},'Ending notice gallery stale')
 for p,sha in images.items():require(digest((folder/p).read_bytes())==sha,'Ending notice capture changed')
 for pattern in ('*.json','index.html','*/*.png','native/*.json'):
  for p in folder.glob(pattern):receipt['artifacts'][str(p.relative_to(ROOT))]=digest(p.read_bytes())
 counts['ending-notice']=2;receipt['ending_notice_scope']=r['scope']
