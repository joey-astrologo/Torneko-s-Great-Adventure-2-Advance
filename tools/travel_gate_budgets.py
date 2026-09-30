import json
from tools.rom import ROOT,digest,require
def append_contexts(config,build,source=ROOT/'build/english'):
 path=source/'travel-gate-validation/report.json';r=json.loads(path.read_text());require(r['passed'] and r['rom_sha256']==build['output_sha256'] and len(r['cases'])==11,'Travel-gate budget evidence stale')
 config['contexts']=[c for c in config['contexts'] if not c['id'].startswith('travel-gate-current-')]
 for reserve in (0,30):
  labels=list(dict.fromkeys(line.replace('{count}','') for row in build['travel_gate']['entries'] for line in row['english'].split('\n') if bool('{count}' in line)==bool(reserve)))
  config['contexts'].append({'id':'travel-gate-current-'+str(reserve),'name':'Dungeon-entry restrictions, '+str(reserve)+'px count reserve','stage':'current','window':224,'start':reserve,'end':216,'rows':len(labels),'labels':labels,'alternatives':[],'reference':str(path.relative_to(ROOT)),'native_report_sha256':digest(path.read_bytes()),'note':'Original two-row message regions and128-byte scratch. Thirty pixels reserve the signed16-bit getter maximum32767; no gameplay limit is inferred from that stress bound. Full source/formatter/modal native checks pass.'})
