"""Ending dialogue lines with verified name reserves and nonprinting timing."""
import json,re
from tools.rom import ROOT,digest,require
from tools.dialogue_layout import PLAYER_WIDTH,INITIAL_WIDTH
from tools.ending_text import SPECIAL

def append_contexts(config,build,source=ROOT/'build/english'):
 path=source/'ending-validation/report.json';r=json.loads(path.read_text());require(r['passed'] and r['rom_sha256']==build['output_sha256'] and len(r['cases'])==85,'Ending budget evidence stale');groups={}
 for row in build['ending_text']['entries']:
  for page in row['layout']['pages']:
   for line in page:
    reserve=PLAYER_WIDTH*line.count('{player}')+INITIAL_WIDTH*line.count('{initial}');label=SPECIAL.sub('',line).replace('{player}','').replace('{initial}','');groups.setdefault(reserve,[])
    if label not in groups[reserve]:groups[reserve].append(label)
 config['contexts']=[c for c in config['contexts'] if not c['id'].startswith('ending-current-')]
 for reserve,labels in groups.items():
  for i in range(0,len(labels),8):
   group=labels[i:i+8];config['contexts'].append({'id':f'ending-current-{reserve}-{i//8}','name':f'Ending dialogue, {reserve}px name reserve','stage':'current','window':224,'start':reserve,'end':216,'rows':len(group),'labels':group,'alternatives':[],'reference':str(path.relative_to(ROOT)),'native_report_sha256':digest(path.read_bytes()),'note':'Original two-row224px window; automatic pages and original W/w delays checked at native frame counts. Name reserves98px and initial14px. Actor/credit progression excluded.'})
