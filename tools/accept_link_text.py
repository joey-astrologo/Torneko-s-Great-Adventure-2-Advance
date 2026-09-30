import json
from tools.rom import ROOT,digest,require

def validate(build,receipt,counts,source=ROOT/'build/english'):
 for family,count in [('link-message',21),('link-picker',3)]:
  folder=source/(family+'-validation');r=json.loads((folder/'report.json').read_text());rows=r['cases'];require(r['passed'] and r['rom_sha256']==build['output_sha256'] and len(rows)==count and len({x['case'] for x in rows})==count,'Link evidence stale/incomplete');require(all(x['caller_guard_abi_preserved'] and x['visible_pixels_checked'] and x['inputs'] and x['returns'] for x in rows),'Link native checks incomplete')
  if family=='link-message':
   require({x['index'] for x in rows if x['kind']=='error'}==set(range(5)),'Link error selectors incomplete')
   expected={('error',i,'dismiss',None) for i in range(5)}|{('instruction',0,'dismiss',None)}|{(kind,0,action,profile) for kind in ('connect','repeat','item') for action in ('yes','no','cancel') for profile in (('ordinary','maximum-width','maximum-bytes') if kind=='item' else (None,))};require({(x['kind'],x['index'],x['action'],x['profile']) for x in rows}==expected,'Link message choice/field cases differ');require(all(len(x['modals'])==len(x['modal_returns'])==1 for x in rows),'Link modal returns incomplete')
  else:require({x['case'] for x in rows}=={'cancel','trade','info'} and all(len(x['returns'])==3 and x['parent_restoration_checks']>=3 for x in rows),'Link picker action/reopen/restoration incomplete')
  images={x['case']+'/'+p:sha for x in rows for p,sha in x['images'].items()};require(json.loads((folder/'preview.json').read_text())=={'rom_sha256':build['output_sha256'],'cases':count,'images':images},'Link gallery stale')
  for p,sha in images.items():require(digest((folder/p).read_bytes())==sha,'Link capture changed')
  for pattern in ('*.json','index.html','*/*.png','native/*.json'):
   for p in folder.glob(pattern):receipt['artifacts'][str(p.relative_to(ROOT))]=digest(p.read_bytes())
  counts[family]=count;receipt[family.replace('-','_')+'_scope']=r['scope']
