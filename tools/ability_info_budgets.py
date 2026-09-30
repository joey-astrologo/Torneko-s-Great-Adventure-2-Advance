"""Original fused-equipment Info body below one/two property-icon rows."""
import json
from tools.rom import ROOT,digest,require

def append_contexts(config,build,source=ROOT/'build/english'):
 path=source/'ability-info-validation/report.json';report=json.loads(path.read_text());require(report['passed'] and report['rom_sha256']==build['output_sha256'] and len(report['cases'])==45,'Ability Info budget evidence stale')
 config['contexts']=[c for c in config['contexts'] if not c['id'].startswith('ability-info-current-body')]
 labels=list(dict.fromkeys(line for row in build['ability_info']['entries'] for line in row['english'].split('\n')))
 for i in range(0,len(labels),8):
  group=labels[i:i+8]
  config['contexts'].append({'id':'ability-info-current-body-'+str(i//8),'name':'Fused-equipment Info descriptions '+str(i//8+1),'stage':'current','window':224,'start':0,'end':216,'rows':len(group),'labels':group,'alternatives':[],'reference':str(path.relative_to(ROOT)),'native_report_sha256':digest(path.read_bytes()),'note':'Original224px by7-row window. Body starts at row3, or row4 with more than12 property sprites; at most3 text rows, with256-byte output including optional cyan control. Complete native selection, body pixels and reopening verified. Property badges are deferred graphics.'})
