import json
from tools.rom import ROOT,digest,require

def append_contexts(config,build,source=ROOT/'build/english'):
 paths=[source/(f+'-validation/report.json') for f in ('link-message','link-picker')]
 for path,count in zip(paths,(21,3)):
  r=json.loads(path.read_text());require(r['passed'] and r['rom_sha256']==build['output_sha256'] and len(r['cases'])==count,'Link budget evidence stale')
 config['contexts']=[c for c in config['contexts'] if not c['id'].startswith('link-text-current-')];groups={}
 for e in build['link_text']['entries']:
  for line in e['english'].split('\n'):
   if '{error}' in line:continue
   reserve=162 if '{item}' in line else 6 if e['source']['offset']==0x6ECAC else 0;window=40 if e['source']['offset']==0x6ECAC else 224;end=40 if window==40 else 216;groups.setdefault((reserve,window,end),[]).append(line.replace('{item}',''))
 for (start,window,end),labels in groups.items():
  path=paths[int(window==40)]
  for i in range(0,len(labels),8):config['contexts'].append({'id':f'link-text-current-{start}-{window}-{i//8}','name':'Link-trade text and original-width actions','stage':'current','window':window,'start':start,'end':end,'rows':len(labels[i:i+8]),'labels':labels[i:i+8],'alternatives':[],'reference':str(path.relative_to(ROOT)),'native_report_sha256':digest(path.read_bytes()),'note':'Original224px/two-row messages or40px action panel with6px cursor reserve and8px outer border gap. Item confirmation reserves162px; separate128-byte formatter bound checked. Native choices/Info/Trade selection pass; successful cable transfer remains untested.'})
