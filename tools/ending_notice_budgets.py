import json
from tools.rom import ROOT,digest,require

def append_contexts(config,build,source=ROOT/'build/english'):
 path=source/'ending-notice-validation/report.json';r=json.loads(path.read_text());require(r['passed'] and r['rom_sha256']==build['output_sha256'] and len(r['cases'])==2,'Ending notice budgets stale');config['contexts']=[c for c in config['contexts'] if c['id']!='ending-notice-current'];config['contexts'].append({'id':'ending-notice-current','name':'Pre-ending save-cancellation notice','stage':'current','window':224,'start':0,'end':216,'rows':1,'labels':[build['ending_notice']['entries'][0]['english']],'alternatives':[],'reference':str(path.relative_to(ROOT)),'native_report_sha256':digest(path.read_bytes()),'note':'Original224px/two-row modal at(8,120), single-line English. Native modal plus secondary A/B acknowledgement preserved. Saving/ending progression excluded from render proof.'})
