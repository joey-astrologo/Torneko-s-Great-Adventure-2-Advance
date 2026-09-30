import json
from tools.rom import ROOT,digest,require

def append_contexts(config,build,source=ROOT/'build/english'):
 path=source/'pickup-help-validation/report.json';r=json.loads(path.read_text());require(r['passed'] and r['rom_sha256']==build['output_sha256'] and len(r['cases'])==13,'Pickup help budget evidence stale')
 config['contexts']=[c for c in config['contexts'] if not c['id'].startswith('pickup-help-current-')];labels=list(dict.fromkeys(line.lstrip('\t') for e in build['pickup_help']['entries'] for line in e['english'].split('\n') if line))
 for i in range(0,len(labels),8):config['contexts'].append(dict(id=f'pickup-help-current-{i//8}',name='Tutorial item pickup tips',stage='current',window=224,start=0,end=216,rows=len(labels[i:i+8]),labels=labels[i:i+8],alternatives=[],reference=str(path.relative_to(ROOT)),native_report_sha256=digest(path.read_bytes()),note='Original queued reader consumes09 as a flag, not a tab. Native walking dispatch for all11 item IDs, mode-off and unrelated-item negatives, glyph pixels and original source controls pass.1024-byte queue and192-byte preceding pickup formatter are bounded separately. Controlled identities/mode load; not natural tutorial progression.'))
