"""Bind fused-equipment Info selection and rendering to the compiled ROM."""
import json
from tools.rom import ROOT,digest,require

def validate(build,receipt,counts,source=ROOT/'build/english'):
 folder=source/'ability-info-validation';path=folder/'report.json';report=json.loads(path.read_text());rows=report['cases']
 expected={f'{kind}-{bit}' for kind in (0,1) for bit in range(20)}|{'special','all-sword','all-shield','highlight-sword','highlight-shield'}
 require(report['passed'] and report['rom_sha256']==build['output_sha256'] and len(rows)==45 and {r['case'] for r in rows}==expected,'Ability Info evidence stale/incomplete')
 require(all(r['caller_guard_abi_preserved'] and r['parent_restored'] and len(r['returns'])==3 and r['visible_pixels_checked'] and r['inputs'] and all(c['guard_abi_preserved'] for c in r['copies']) for r in rows),'Ability Info body/parent/ABI/pixels missing')
 require({r['id'] for c in rows for r in c['copies']}=={r['id'] for r in build['ability_info']['entries']},'Ability Info source coverage incomplete')
 require(all(any(c['highlighted'] for c in r['copies']) for r in rows if r['highlight']),'Ability Info highlight coverage missing')
 images={r['case']+'/'+p:sha for r in rows for p,sha in r['images'].items()}
 require(json.loads((folder/'preview.json').read_text())=={'rom_sha256':build['output_sha256'],'cases':45,'images':images},'Ability Info gallery stale')
 for p,sha in images.items():require(digest((folder/p).read_bytes())==sha,'Ability Info capture changed')
 for pattern in ('*.json','index.html','*/*.png','native/*.json'):
  for p in folder.glob(pattern):receipt['artifacts'][str(p.relative_to(ROOT))]=digest(p.read_bytes())
 counts['ability-info']=45;receipt['ability_info_scope']=report['scope'];receipt['ability_info_resources']=len(build['ability_info']['entries'])
