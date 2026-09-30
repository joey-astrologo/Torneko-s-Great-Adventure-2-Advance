import json
from tools.rom import ROOT,digest,require
GROUPS=[(2,2),(6,3),(15,3),(21,4),(25,4),(30,2),(33,2),(36,2),(38,2)]
def validate(build,receipt,counts,source=ROOT/'build/english'):
 folder=source/'fire-scene-validation';r=json.loads((folder/'report.json').read_text());rows=r['cases'];expected=set()
 for e in build['fire_scene']['entries']:
  for p in (('required-English','widest-English','widest-Japanese') if '{player}' in e['english'] else ('ordinary',)):expected.add(str(e['index'])+'-'+p)
 expected|={f'sequence-{i}-{n}' for i,n in GROUPS}|{'zero-count'}
 require(r['passed'] and r['rom_sha256']==build['output_sha256'] and len(rows)==len(expected)==56 and {c['case'] for c in rows}==expected,'Fire scene evidence stale/incomplete');require(all(c['caller_guard_abi_preserved'] and (c['visible_pixels_checked'] or c['count']==0) and len(c['returns'])==1 and len(c['reads'])==len(c['modals'])==len(c['modal_returns'])==c['count'] for c in rows),'Fire scene native dispatcher evidence incomplete');require({e['id'] for c in rows for e in c['reads']}=={e['id'] for e in build['fire_scene']['entries']},'Fire scene source coverage incomplete')
 images={c['case']+'/'+p:sha for c in rows for p,sha in c['images'].items()};require(json.loads((folder/'preview.json').read_text())==dict(rom_sha256=build['output_sha256'],cases=56,images=images),'Fire scene gallery stale')
 for p,sha in images.items():require(digest((folder/p).read_bytes())==sha,'Fire scene image changed')
 for pattern in ('*.json','index.html','*/*.png','native/*.json'):
  for p in folder.glob(pattern):receipt['artifacts'][str(p.relative_to(ROOT))]=digest(p.read_bytes())
 counts['fire_scene']=56;receipt['fire_scene_scope']=r['scope']
