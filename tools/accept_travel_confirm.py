import json
from tools.rom import ROOT,digest,require

def validate(build,receipt,counts,source=ROOT/'build/english'):
 folder=source/'travel-confirm-validation';r=json.loads((folder/'report.json').read_text());cases=r['cases'];expected={f'{owner}-{key}-{profile}-{layout}-{choice}' for owner in ('map','destination','picker') for key in ('enter','overwrite') for profile in (('ordinary',) if key=='enter' else ('native-save','required-English','eight-English','eight-Japanese','empty','read-failure')) for layout in ((2,) if owner=='picker' else (0,2)) for choice in ('yes','no','cancel')}
 require(r['passed'] and r['rom_sha256']==build['output_sha256'] and len(cases)==len(expected)==105 and {c['case'] for c in cases}==expected,'Travel confirmation evidence stale/incomplete');require(all(c['caller_guard_abi_preserved'] and c['visible_pixels_checked'] and len(c['reads'])==len(c['returns'])==len(c['modals'])==len(c['modal_returns'])==1 and bool(c['produced'])==(c['key']=='overwrite') for c in cases),'Travel confirmation native evidence incomplete');require({e['id'] for c in cases for e in c['reads']}=={e['id'] for e in build['travel_confirm']['entries']},'Travel confirmation source coverage incomplete')
 images={c['case']+'/'+p:sha for c in cases for p,sha in c['images'].items()};require(json.loads((folder/'preview.json').read_text())==dict(rom_sha256=build['output_sha256'],cases=105,images=images),'Travel confirmation gallery stale')
 for p,sha in images.items():require(digest((folder/p).read_bytes())==sha,'Travel confirmation image changed')
 for pattern in ('*.json','index.html','*/*.png','native/*.json'):
  for p in folder.glob(pattern):receipt['artifacts'][str(p.relative_to(ROOT))]=digest(p.read_bytes())
 counts['travel_confirm']=105;receipt['travel_confirm_scope']=r['scope']
