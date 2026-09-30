import json
from tools.rom import ROOT,digest,require

def validate(build,receipt,counts,source=ROOT/'build/english'):
 folder=source/'carpenter-validation';r=json.loads((folder/'report.json').read_text());rows=r['cases'];names={'working','finished','complete','capacity30','capacity170','capacity255-boundary','pay-exact','pay-surplus','pay-maximum','pay-signed-boundary','no','cancel','empty','short'}
 require(r['passed'] and r['rom_sha256']==build['output_sha256'] and len(rows)==28 and {c['case'] for c in rows}=={f'{name}-layout{layout}' for name in names for layout in (0,2)},'Carpenter evidence stale/incomplete');require(all(c['caller_guard_abi_preserved'] and c['visible_pixels_checked'] and len(c['returns'])==1 and len(c['modals'])==len(c['modal_returns'])==len(c['reads'])==len(c['sequence']) and len(c['helpers'])==len(c['helper_returns']) for c in rows),'Carpenter original-owner/modal evidence incomplete');require({e['id'] for c in rows for e in c['reads']}=={e['id'] for e in build['carpenter']['entries']},'Carpenter source coverage incomplete')
 images={c['case']+'/'+p:sha for c in rows for p,sha in c['images'].items()};require(json.loads((folder/'preview.json').read_text())==dict(rom_sha256=build['output_sha256'],cases=28,images=images),'Carpenter gallery stale')
 for p,sha in images.items():require(digest((folder/p).read_bytes())==sha,'Carpenter image changed')
 for pattern in ('*.json','index.html','*/*.png','native/*.json'):
  for p in folder.glob(pattern):receipt['artifacts'][str(p.relative_to(ROOT))]=digest(p.read_bytes())
 counts['carpenter']=28;receipt['carpenter_scope']=r['scope']
