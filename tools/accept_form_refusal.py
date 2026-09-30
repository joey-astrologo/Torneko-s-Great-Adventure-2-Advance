import json
from tools.rom import ROOT,digest,require

def validate(build,receipt,counts,source=ROOT/'build/english'):
 folder=source/'form-refusal-validation';r=json.loads((folder/'report.json').read_text());cases=r['cases'];expected={f'{code}-{layout}-{button}' for code in ('M.A','X.A','MXA','M.X') for layout in (0,2) for button in (('A','B') if code=='M.A' else ('none',))};require(r['passed'] and r['rom_sha256']==build['output_sha256'] and len(cases)==len(expected)==10 and {c['case'] for c in cases}==expected,'Form refusal evidence stale/incomplete');require(all(c['caller_guard_abi_preserved'] and len(c['returns'])==len(c['predicates'])==1 and len(c['reads'])==len(c['modals'])==len(c['modal_returns'])==int(c['shown']) and bool(c['visible_pixels_checked'])==c['shown'] for c in cases),'Form refusal native evidence incomplete')
 images={c['case']+'/'+p:sha for c in cases for p,sha in c['images'].items()};require(json.loads((folder/'preview.json').read_text())==dict(rom_sha256=build['output_sha256'],cases=10,images=images),'Form refusal gallery stale')
 for p,sha in images.items():require(digest((folder/p).read_bytes())==sha,'Form refusal image changed')
 for pattern in ('*.json','index.html','*/*.png','native/*.json'):
  for p in folder.glob(pattern):receipt['artifacts'][str(p.relative_to(ROOT))]=digest(p.read_bytes())
 counts['form_refusal']=10;receipt['form_refusal_scope']=r['scope']
