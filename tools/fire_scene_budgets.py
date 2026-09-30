import json
from tools.rom import ROOT,digest,require

def append_contexts(config,build,source=ROOT/'build/english'):
 path=source/'fire-scene-validation/report.json';r=json.loads(path.read_text());require(r['passed'] and r['rom_sha256']==build['output_sha256'] and len(r['cases'])==56,'Fire scene budget evidence stale');config['contexts']=[c for c in config['contexts'] if not c['id'].startswith('fire-scene-current-')];groups={}
 for e in build['fire_scene']['entries']:
  for page in e['layout']['pages']:
   for line in page:groups.setdefault(98 if '{player}' in line else 0,[]).append(line.replace('{player}',''))
 for reserve,labels in groups.items():
  for i in range(0,len(labels),8):config['contexts'].append(dict(id=f'fire-scene-current-{reserve}-{i//8}',name='House-fire scene dialogue',stage='current',window=224,start=reserve,end=216,rows=len(labels[i:i+8]),labels=labels[i:i+8],alternatives=[],reference=str(path.relative_to(ROOT)),native_report_sha256=digest(path.read_bytes()),note='Full original indexed text dispatcher,40 records, all page waits and maximum English/Japanese player names. Original two-row panel; name reserves98px. Private512-byte ROM records, no new RAM; actor staging and natural story trigger remain separate.'))
