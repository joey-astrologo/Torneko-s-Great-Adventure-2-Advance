"""Pin dungeon cutscene text/choice evidence without implying story progression."""
import json
from tools.rom import ROOT,digest,require
from tools.verify_dungeon_story import BLOCKS
from tools.dialogue_checks import player_layout_cases

def validate(build,receipt,counts,source=ROOT/'build/english'):
 folder=source/'dungeon-story-validation';path=folder/'report.json';report=json.loads(path.read_text());rows=report['cases']
 expected={f'{i}-{name}-{choice}' for i in BLOCKS for name in ([p for p,_ in player_layout_cases()] if i in (8,11,18,21) else ['ordinary']) for choice in (('yes','no','cancel') if i==11 else ('continue',))}
 require(report['passed'] and report['rom_sha256']==build['output_sha256'] and len(rows)==33 and {r['case'] for r in rows}==expected,'Dungeon-story evidence stale/incomplete')
 require(all(r['caller_guard_abi_preserved'] and r['inventory_stable_during_message_block'] and r['visible_pixels_checked'] and r['inputs'] and len(r['modals'])==len(r['modal_returns']) for r in rows),'Dungeon-story native ABI/pixels missing')
 require({r['id'] for c in rows for r in c['reads']}=={r['id'] for r in build['dungeon_story']['entries']},'Dungeon-story source coverage incomplete')
 require(all(len(r['choice_results'])==1 and [int(c['id'].split('.')[-1]) for c in r['reads']]==[11,12 if r['choice']=='yes' else 13,14] for r in rows if r['index']==11),'Dungeon-story native choice branches missing')
 require(all(len(r['helpers'])==1 for r in rows if r['index'] in (8,18)),'Relic helper source/frame evidence missing')
 images={r['case']+'/'+p:sha for r in rows for p,sha in r['images'].items()}
 require(json.loads((folder/'preview.json').read_text())=={'rom_sha256':build['output_sha256'],'cases':33,'images':images},'Dungeon-story gallery stale')
 for p,sha in images.items():require(digest((folder/p).read_bytes())==sha,'Dungeon-story capture changed')
 for pattern in ('*.json','index.html','*/*.png','native/*.json'):
  for p in folder.glob(pattern):receipt['artifacts'][str(p.relative_to(ROOT))]=digest(p.read_bytes())
 counts['dungeon-story']=33;receipt['dungeon_story_scope']=report['scope'];receipt['dungeon_story_resources']=len(build['dungeon_story']['entries'])
