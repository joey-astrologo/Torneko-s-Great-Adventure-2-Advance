import json
from tools.rom import ROOT,digest,require
def append_contexts(config,build,source=ROOT/'build/english'):
 path=source/'empty-read-validation/report.json';r=json.loads(path.read_text());require(r['passed'] and r['rom_sha256']==build['output_sha256'] and len(r['cases'])==4,'Empty-read budget evidence stale')
 config['contexts']=[c for c in config['contexts'] if c['id']!='empty-read-current']
 config['contexts'].append({'id':'empty-read-current','name':'Empty-inventory scroll refusal','stage':'current','window':224,'start':0,'end':216,'rows':1,'labels':[build['empty_read']['entries'][0]['english']],'alternatives':[],'reference':str(path.relative_to(ROOT)),'native_report_sha256':digest(path.read_bytes()),'note':'One-line native refusal for four Floor/Read scroll IDs, original window/font; failed read leaves scroll intact.'})
