import json
from tools.rom import ROOT,digest,require

def validate(build,receipt,counts,source=ROOT/'build/english'):
 folder=source/'ground-remove-validation';r=json.loads((folder/'report.json').read_text());cases=r['cases'];require(r['passed'] and r['rom_sha256']==build['output_sha256'] and len(cases)==2 and {c['case'] for c in cases}=={'floor-index-50','floor-index-255'},'Ground Remove evidence stale/incomplete');require(all(c['caller_guard_abi_preserved'] and c['inventory_gold_save_preserved'] and len(c['entries'])==len(c['returns'])==len(c['queues'])==1 and c['queue']['one_line'] and c['glyphs']>0 for c in cases),'Ground Remove native evidence incomplete');images={c['case']+'/'+p:sha for c in cases for p,sha in c['images'].items()};require(json.loads((folder/'preview.json').read_text())==dict(rom_sha256=build['output_sha256'],cases=2,images=images),'Ground Remove gallery stale')
 for p,sha in images.items():require(digest((folder/p).read_bytes())==sha,'Ground Remove image changed')
 for pattern in ('*.json','index.html','*/*.png','native/*.json'):
  for p in folder.glob(pattern):receipt['artifacts'][str(p.relative_to(ROOT))]=digest(p.read_bytes())
 counts['ground_remove']=2;receipt['ground_remove_scope']=r['scope']
