import json
from tools.rom import ROOT,digest,require

def append_contexts(config,build,source=ROOT/'build/english'):
 p=source/'ground-remove-validation/report.json';r=json.loads(p.read_text());require(r['passed'] and r['rom_sha256']==build['output_sha256'] and len(r['cases'])==2,'Ground Remove budget evidence stale');config['contexts']=[c for c in config['contexts'] if c['id']!='ground-remove-current'];config['contexts'].append(dict(id='ground-remove-current',name='Floor Remove fragment',stage='current',window=224,start=0,end=216,rows=1,labels=[build['ground_remove']['entries'][0]['english']],alternatives=[],reference=str(p.relative_to(ROOT)),native_report_sha256=digest(p.read_bytes()),note='Original one-line mode1 queue; full Remove owner/branch, min/max floor-selector bytes50/255. Retains original incomplete phrase. Source bytes immutable, original font and spacing preserved.'))
