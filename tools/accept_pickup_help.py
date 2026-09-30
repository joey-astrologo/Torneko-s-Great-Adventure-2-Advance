import json
from tools.rom import ROOT,digest,require

def validate(build,receipt,counts,source=ROOT/'build/english'):
 folder=source/'pickup-help-validation';r=json.loads((folder/'report.json').read_text());rows=r['cases'];items={i:e for e in build['pickup_help']['entries'] for i in e['item_ids']}
 require(r['passed'] and r['rom_sha256']==build['output_sha256'] and len(rows)==13 and {(c['item_id'],c['mode']) for c in rows}=={(i,11) for i in items}|{(1,0),(2,11)},'Pickup help evidence stale/incomplete')
 for c in rows:
  active=c['mode']==11 and c['item_id'] in items
  require(len(c['queues'])==1+active and len(c['formats'])==len(c['mode_reads'])==1 and c['inputs'] and c['images'] and c['inventory_after']==c['inventory_before']+1 and c['gold_before']==c['gold_after'],'Pickup help native outcome evidence incomplete')
  if active:
   e=items[c['item_id']];require(c['queues'][1]['hex']==e['encoded_hex'][:-2] and len(c['tabs'])==e['english'].count('\t'),'Pickup help complete text/09 evidence differs')
 images={c['case']+'/'+p:sha for c in rows for p,sha in c['images'].items()};require(json.loads((folder/'preview.json').read_text())==dict(rom_sha256=build['output_sha256'],cases=13,images=images),'Pickup help gallery stale')
 for p,sha in images.items():require(digest((folder/p).read_bytes())==sha,'Pickup help capture changed')
 for pattern in ('*.json','index.html','*/*.png','native/*.json'):
  for p in folder.glob(pattern):receipt['artifacts'][str(p.relative_to(ROOT))]=digest(p.read_bytes())
 counts['pickup-help']=13;receipt['pickup_help_scope']=r['scope']
