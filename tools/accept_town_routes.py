import json
from tools.rom import ROOT,digest,require

def validate(build,receipt,counts,source=ROOT/'build/english'):
 folder=source/'town-routes-validation';r=json.loads((folder/'report.json').read_text());cases=r['cases'];expected={f'town-{s}-{n}' for s in range(8) for n in range(6)}|{f'dungeon-{n}' for n in range(4)}|{f'town-select-{n}' for n in range(7)}|{f'dungeon-select-{n}' for n in range(3)}|{'town-retained-cancel','dungeon-retained-cancel','town-clamped-state','town-home-widest-English','town-home-widest-Japanese'}
 require(r['passed'] and r['rom_sha256']==build['output_sha256'] and len(cases)==len(expected)==67 and {c['case'] for c in cases}==expected,'Town route evidence stale/incomplete');require(all(c['caller_guard_abi_preserved'] and c['visible_pixels_checked'] and len(c['returns'])==len(c['selectors'])==3 and len(c['creates'])==len(c['closures'])==6 for c in cases),'Town route native lifecycle evidence incomplete');require({e['id'] for e in build['town_routes']['entries']}<={e['id'] for c in cases for e in c['reads']},'Town route source coverage incomplete')
 images={c['case']+'/'+p:sha for c in cases for p,sha in c['images'].items()};require(json.loads((folder/'preview.json').read_text())==dict(rom_sha256=build['output_sha256'],cases=67,images=images),'Town route gallery stale')
 for p,sha in images.items():require(digest((folder/p).read_bytes())==sha,'Town route image changed')
 for pattern in ('*.json','index.html','*/*.png'):
  for p in folder.glob(pattern):receipt['artifacts'][str(p.relative_to(ROOT))]=digest(p.read_bytes())
 counts['town_routes']=67;receipt['town_routes_scope']=r['scope']
