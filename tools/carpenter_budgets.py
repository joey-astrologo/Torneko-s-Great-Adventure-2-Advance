import json
from tools.rom import ROOT,digest,require

def append_contexts(config,build,source=ROOT/'build/english'):
 path=source/'carpenter-validation/report.json';r=json.loads(path.read_text());require(r['passed'] and r['rom_sha256']==build['output_sha256'] and len(r['cases'])==28,'Carpenter budget evidence stale');config['contexts']=[c for c in config['contexts'] if not c['id'].startswith('carpenter-current-')];groups={}
 for e in build['carpenter']['entries']:
  for page in e['layout']['pages']:
   for line in page:groups.setdefault(18 if '{count}' in line else 0,[]).append(line.replace('{count}',''))
 for reserve,labels in groups.items():
  for i in range(0,len(labels),8):config['contexts'].append(dict(id=f'carpenter-current-{reserve}-{i//8}',name='Warehouse repair dialogue',stage='current',window=224,start=reserve,end=216,rows=len(labels[i:i+8]),labels=labels[i:i+8],alternatives=[],reference=str(path.relative_to(ROOT)),native_report_sha256=digest(path.read_bytes()),note='Both original two-row layouts, complete prose pages,Yes/No/B, native1000-gold payment and capacity changes. Numeric field reserves3 compact digits and remains inside original128-byte shared scratch; all28 cases pass. Controlled service entry/state, not natural repair-unlock progression.'))
