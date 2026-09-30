import json
from tools.rom import ROOT,digest,require

def append_contexts(config,build,source=ROOT/'build/english'):
 path=source/'form-refusal-validation/report.json';r=json.loads(path.read_text());require(r['passed'] and r['rom_sha256']==build['output_sha256'] and len(r['cases'])==10,'Form refusal budget evidence stale');config['contexts']=[c for c in config['contexts'] if c['id']!='form-refusal-current'];labels=build['form_refusal']['entries'][0]['layout']['pages'][0]
 config['contexts'].append(dict(id='form-refusal-current',name='Guard form refusal',stage='current',window=224,start=0,end=216,rows=2,labels=labels,alternatives=[],reference=str(path.relative_to(ROOT)),native_report_sha256=digest(path.read_bytes()),note='Original two-row modal, both native layout selectors, original colour4 span/restoration. Matching three-byte form code, each individual mismatch and A/B dismissal checked in10 cases. Natural map/transform progression excluded.'))
