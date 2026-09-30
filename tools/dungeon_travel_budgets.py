import json
from tools.rom import ROOT,digest,require

def append_contexts(config,build,source=ROOT/'build/english'):
 path=source/'dungeon-travel-validation/report.json';r=json.loads(path.read_text());require(r['passed'] and r['rom_sha256']==build['output_sha256'] and len(r['cases'])==25,'Dungeon travel budgets stale');config['contexts']=[c for c in config['contexts'] if not c['id'].startswith('dungeon-travel-current-')]
 for kind,window,start,end,entries in [('names',144,6,144,[e for e in build['dungeon_travel']['entries'] if e['index']!=7]),('heading',160,0,152,[e for e in build['dungeon_travel']['entries'] if e['index']==7])]:
  config['contexts'].append({'id':'dungeon-travel-current-'+kind,'name':'Dungeon destination picker '+kind,'stage':'current','window':window,'start':start,'end':end,'rows':len(entries),'labels':[e['english'] for e in entries],'alternatives':[],'reference':str(path.relative_to(ROOT)),'native_report_sha256':digest(path.read_bytes()),'note':'Original160px heading and144px five-row list;6px native cursor reserve. All original availability rows, fallbacks, wrapping, selection and twice reopening pass; meadow label uses a separate controlled selector.'})
