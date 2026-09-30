import json
from tools.rom import ROOT,digest,require
def validate(build,receipt,counts,source=ROOT/'build/english'):
 folder=source/'travel-gate-validation';path=folder/'report.json';r=json.loads(path.read_text());rows=r['cases'];expected={f'{key}-{n}-{layout}' for key,n in [('limit',1),('limit',5),('limit',32767),('store',0),('sell',0),('level',None)] for layout in ((0,2) if key!='level' else (2,))}
 require(r['passed'] and r['rom_sha256']==build['output_sha256'] and len(rows)==11 and {x['case'] for x in rows}==expected,'Travel-gate evidence stale/incomplete')
 require(all(x['caller_guard_abi_preserved'] and x['visible_pixels_checked'] and x['inputs'] and len(x['formats'])==len(x['modals'])==len(x['modal_returns'])==1 and x['formats'][0]['guard_abi_preserved'] and x['formats'][0]['bytes']<=128 for x in rows),'Travel-gate128-byte/modal/ABI evidence missing')
 require({x['id'] for x in rows}=={x['id'] for x in build['travel_gate']['entries']},'Travel-gate source coverage incomplete')
 images={x['case']+'/'+p:sha for x in rows for p,sha in x['images'].items()};require(json.loads((folder/'preview.json').read_text())=={'rom_sha256':build['output_sha256'],'cases':11,'images':images},'Travel-gate gallery stale')
 for p,sha in images.items():require(digest((folder/p).read_bytes())==sha,'Travel-gate capture changed')
 for pattern in ('*.json','index.html','*/*.png','native/*.json'):
  for p in folder.glob(pattern):receipt['artifacts'][str(p.relative_to(ROOT))]=digest(p.read_bytes())
 counts['travel-gate']=11;receipt['travel_gate_scope']=r['scope']
