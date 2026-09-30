import json
from tools.rom import ROOT,digest,require
def validate(build,receipt,counts,source=ROOT/'build/english'):
 folder=source/'empty-read-validation';path=folder/'report.json';r=json.loads(path.read_text());rows=r['cases'];require(r['passed'] and r['rom_sha256']==build['output_sha256'] and len(rows)==4 and {x['item_id'] for x in rows}=={117,128,132,133},'Empty-read evidence stale/incomplete')
 require(all(x['caller_guard_abi_preserved'] and x['native_refusal_preserves_floor_scroll'] and x['queue']['one_line'] and x['visible_pixels_checked'] and x['inputs'] for x in rows),'Empty-read native result/pixels missing')
 images={x['case']+'/'+p:sha for x in rows for p,sha in x['images'].items()};require(json.loads((folder/'preview.json').read_text())=={'rom_sha256':build['output_sha256'],'cases':4,'images':images},'Empty-read gallery stale')
 for p,sha in images.items():require(digest((folder/p).read_bytes())==sha,'Empty-read capture changed')
 for pattern in ('*.json','index.html','*/*.png','native/*.json'):
  for p in folder.glob(pattern):receipt['artifacts'][str(p.relative_to(ROOT))]=digest(p.read_bytes())
 counts['empty-read']=4;receipt['empty_read_scope']=r['scope']
