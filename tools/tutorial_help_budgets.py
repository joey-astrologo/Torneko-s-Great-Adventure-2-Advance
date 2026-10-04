import json
from tools.rom import ROOT,digest,require

def append_contexts(config,build,source=ROOT/'build/english'):
 paths={f:source/(f+'-validation/report.json') for f in ('tutorial-help','tutorial-all-menu','tutorial-bank','tutorial-alternate')}
 for f,count in [('tutorial-help',6),('tutorial-all-menu',27),('tutorial-bank',22),('tutorial-alternate',4)]:
  r=json.loads(paths[f].read_text());require(r['passed'] and r['rom_sha256']==build['output_sha256'] and len(r['cases'])==count,'Tutorial budget evidence stale')
 config['contexts']=[c for c in config['contexts'] if not c['id'].startswith('tutorial-help-current-')];groups={}
 for e in build['tutorial_help']['entries']:
  if 'cells' in e:
   for column,(text,start,width) in enumerate(zip(e['cells'],e['layout']['cell_starts'],e['layout']['cell_budgets'])):groups.setdefault(('column'+str(column),224,start,start+width),[]).append(text)
  else:
   start=e['layout'].get('start',0);width=e['layout'].get('maximum_width',216);window=224 if e['kind']!='label' else max(min(g['descriptor'][6]*16,224) if g['menu'] not in(10,13,14) else 224 for g in build['tutorial_help']['groups'] if any(x['offset']==e['source']['offset'] for x in g['labels']));key=(e['kind'],window,start,start+width)
   for page in e['layout']['pages']:
    for line in page:
     if line not in groups.setdefault(key,[]):groups[key].append(line)
 for (kind,window,start,end),labels in groups.items():
  path=paths['tutorial-help' if kind=='prose' else 'tutorial-all-menu']
  for i in range(0,len(labels),8):config['contexts'].append({'id':f'tutorial-help-current-{kind}-{window}-{start}-{end}-{i//8}','name':'Tutorial '+kind+' text','stage':'current','window':window,'start':start,'end':end,'rows':len(labels[i:i+8]),'labels':labels[i:i+8],'alternatives':[],'reference':str(path.relative_to(ROOT)),'native_report_sha256':digest(path.read_bytes()),'note':'All 27 configurations; actual cursor tables determine 6px or 11px left inset and independent right-column regions. All rendering/cursor cases, 22 bank/topic cases, six direct-prose cases and four alternate-heading probes pass. Pot and early Mimic mappings are repaired; four configurations lack extracted script references and retain menu-only evidence. Ordinary NPC access remains unclaimed.'})
