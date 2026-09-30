"""Native two-row cutscene pages and widest dynamic-name reserves."""
import json,re
from tools.rom import ROOT,digest,require
from tools.dialogue_layout import PLAYER_WIDTH,INITIAL_WIDTH

def append_contexts(config,build,source=ROOT/'build/english'):
 path=source/'dungeon-story-validation/report.json';report=json.loads(path.read_text());require(report['passed'] and report['rom_sha256']==build['output_sha256'] and len(report['cases'])==33,'Dungeon-story budget evidence stale')
 config['contexts']=[c for c in config['contexts'] if not c['id'].startswith('dungeon-story-current-')];groups={}
 for row in build['dungeon_story']['entries']:
  for page in row['layout']['pages']:
   for line in page:
    reserve=line.count('{player}')*PLAYER_WIDTH+line.count('{initial}')*INITIAL_WIDTH
    label=re.sub(r'\{(?:player|initial|center)\}','',line)
    if label not in groups.setdefault(reserve,[]):groups[reserve].append(label)
 for reserve,labels in groups.items():
  for i in range(0,len(labels),8):
   group=labels[i:i+8]
   config['contexts'].append({'id':f'dungeon-story-current-{reserve}-{i//8}','name':'Dungeon story pages, '+str(reserve)+'px name reserve','stage':'current','window':224,'start':reserve,'end':216,'rows':len(group),'labels':group,'alternatives':[],'reference':str(path.relative_to(ROOT)),'native_report_sha256':digest(path.read_bytes()),'note':'Original two-row modal,216px safe line budget. Seven widest14px name glyphs and14px initial reserved where used; native pages, centred yellow inscriptions and all identity choices verified. Graphics and story progression remain separately scoped.'})
