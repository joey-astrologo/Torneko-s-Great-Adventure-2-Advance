import json
from tools.rom import ROOT,digest,require

def append_contexts(config,build,source=ROOT/'build/english'):
 path=source/'travel-confirm-validation/report.json';r=json.loads(path.read_text());require(r['passed'] and r['rom_sha256']==build['output_sha256'] and len(r['cases'])==105,'Travel confirmation budget evidence stale');config['contexts']=[c for c in config['contexts'] if not c['id'].startswith('travel-confirm-current-')];groups={}
 for e in build['travel_confirm']['entries']:
  for page in e['layout']['pages']:
   for line in page:groups.setdefault(112 if '{village}' in line else 0,[]).append(line.replace('{village}','').replace('{center}',''))
 for reserve,labels in groups.items():
  config['contexts'].append(dict(id=f'travel-confirm-current-{reserve}',name='Dungeon entry and overwrite confirmations',stage='current',window=224,start=reserve,end=216,rows=len(labels),labels=labels,alternatives=[],reference=str(path.relative_to(ROOT)),native_report_sha256=digest(path.read_bytes()),note='Three original callers, native Yes/No/B and saved-village getter, centred two-row panel,112px reserved for eight legacy Japanese name glyphs.105 controlled native cases; actual travel and save overwrite excluded.'))
