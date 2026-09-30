import json
from tools.rom import ROOT,digest,require

def validate(build,receipt,counts,source=ROOT/'build/english'):
 folder=source/'dungeon-travel-validation';path=folder/'report.json';r=json.loads(path.read_text());rows=r['cases'];expected={f'state-{s}-unlocked' for s in range(8)}|{f'state-{s}-locked' for s in range(2,7)}|{'state-6-more','stored-meadow'}|{f'select-{s}-{t}' for s in (5,7) for t in range(5)}
 require(r['passed'] and r['rom_sha256']==build['output_sha256'] and len(rows)==25 and {x['case'] for x in rows}==expected,'Dungeon travel evidence stale/incomplete')
 require(all(x['caller_guard_abi_preserved'] and x['visible_pixels_checked'] and x['inputs'] and len(x['returns'])==3 and len(x['closures'])==6 and all(y['native_result_checked'] for y in x['returns']) for x in rows),'Dungeon travel native ABI/cursor/closure evidence incomplete')
 require({x['id'] for c in rows for x in c['reads']}=={x['id'] for x in build['dungeon_travel']['entries']},'Dungeon travel labels incomplete')
 images={x['case']+'/'+p:sha for x in rows for p,sha in x['images'].items()};require(json.loads((folder/'preview.json').read_text())=={'rom_sha256':build['output_sha256'],'cases':25,'images':images},'Dungeon travel gallery stale')
 for p,sha in images.items():require(digest((folder/p).read_bytes())==sha,'Dungeon travel capture changed')
 for pattern in ('*.json','index.html','*/*.png','native/*.json'):
  for p in folder.glob(pattern):receipt['artifacts'][str(p.relative_to(ROOT))]=digest(p.read_bytes())
 counts['dungeon-travel']=25;receipt['dungeon_travel_scope']=r['scope']
