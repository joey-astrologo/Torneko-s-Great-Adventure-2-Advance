import json
from tools.rom import ROOT,digest,require

def append_contexts(config,build,source=ROOT/'build/english'):
 path=source/'town-routes-validation/report.json';r=json.loads(path.read_text());require(r['passed'] and r['rom_sha256']==build['output_sha256'] and len(r['cases'])==67,'Town route budget evidence stale');config['contexts']=[c for c in config['contexts'] if not c['id'].startswith('town-routes-current-')]
 for budget,window,start in [(96,104,0),(140,152,12),(76,88,12)]:
  labels=[e['english'] for e in build['town_routes']['entries'] if e['text_budget']==budget]
  config['contexts'].append(dict(id=f'town-routes-current-{budget}',name='Town and dungeon destination labels',stage='current',window=window,start=start,end=start+budget,rows=len(labels),labels=labels,alternatives=[],reference=str(path.relative_to(ROOT)),native_report_sha256=digest(path.read_bytes()),note='Existing town/dungeon panel geometry and12px cursor inset. All48/4 original availability cells, full native cursor wrapping, cancellation/reopening and selector returns. Legacy maximum home names checked separately using the existing English home label.67 cases; natural unlocking and actual travel remain separate.'))
