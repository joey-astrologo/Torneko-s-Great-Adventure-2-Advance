"""Pin ending dialogue proof, excluding actor/credit/endgame progression."""
import json
from tools.rom import ROOT,digest,require
from tools.dialogue_checks import player_layout_cases

def validate(build,receipt,counts,source=ROOT/'build/english'):
 folder=source/'ending-validation';path=folder/'report.json';r=json.loads(path.read_text());rows=r['cases'];entries=build['ending_text']['entries']
 expected={f"{e['index']}-{name}" for e in entries for name in ([p for p,_ in player_layout_cases()] if '{player}' in e['english'] else ['ordinary'])}
 require(r['passed'] and r['rom_sha256']==build['output_sha256'] and len(rows)==85 and {x['case'] for x in rows}==expected,'Ending evidence stale/incomplete')
 require(all(x['caller_guard_abi_preserved'] and x['inventory_stable_during_message_block'] and x['automatic_pages_without_input'] and x['visible_pixels_checked'] and x['inputs'] and len(x['reads'])==len(x['modals'])==len(x['modal_returns'])==len(x['setup_returns'])==1 for x in rows),'Ending native timing/page/ABI evidence incomplete')
 for x in rows:
  e=next(e for e in entries if e['index']==x['index']);delays=[c['raw_hex'] for c in e['layout']['ending_controls'] if c['token'].startswith('{wait:')]
  require([d['raw_hex'] for d in x['timed_delays']]==delays and all(d['wait_end_frame']-d['wait_start_frame']==d['frames'] for d in x['timed_delays']),'Ending native delays differ')
  require(x['reads'][0]['id']==e['id'] and len(x['images'])==len(e['layout']['pages']) and x['modal_returns'][0]['mode']==(0 if e['index']==0 else 1),'Ending sources/pages/modes incomplete')
 images={x['case']+'/'+p:sha for x in rows for p,sha in x['images'].items()};require(json.loads((folder/'preview.json').read_text())=={'rom_sha256':build['output_sha256'],'cases':85,'images':images},'Ending gallery stale')
 for p,sha in images.items():require(digest((folder/p).read_bytes())==sha,'Ending capture changed')
 for pattern in ('*.json','index.html','*/*.png','native/*.json'):
  for p in folder.glob(pattern):receipt['artifacts'][str(p.relative_to(ROOT))]=digest(p.read_bytes())
 counts['ending-text']=85;receipt['ending_text_scope']=r['scope'];receipt['ending_text_resources']=57
