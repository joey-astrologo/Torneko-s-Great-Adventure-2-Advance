"""Bind complete owned record-menu/travel prompt evidence to the tested ROM."""
import json
from tools.rom import ROOT,digest,require

def validate(build,receipt,counts,source=ROOT/'build/english'):
    folder=source/'book-travel-validation';path=folder/'report.json';report=json.loads(path.read_text());rows=report['cases']
    expected={f'book-{int(v)}-{a}-ordinary' for v in (False,True) for a in ('cancel','records','scores')}|{'book-1-trade-ordinary','book-1-empty-ordinary'}
    expected|={f'travel-{v}-{a}-{p}' for v in (0,1) for a in ('cancel','no','yes') for p in (('ordinary','wide-English','wide-Japanese') if v==0 and a=='yes' else ('ordinary',))}
    require(report['passed'] and report['rom_sha256']==build['output_sha256'] and len(rows)==16 and {r['case'] for r in rows}==expected,'Book/travel evidence stale/incomplete')
    require(all(r['caller_guard_abi_preserved'] and len(r['returns'])==3 and all(e['native_result_checked'] for e in r['returns']) and r['visible_pixels_checked'] and r['inputs'] for r in rows),'Book/travel native results/pixels/ABI missing')
    require({r['id'] for c in rows for r in c['reads']}=={r['id'] for r in build['book_travel']['entries']},'Book/travel source reads missing')
    require(all(r['getter'] for r in rows if r['kind']=='travel' and r['variant']==0 and r['action']=='yes'),'Saved village getter evidence missing')
    images={r['case']+'/'+p:sha for r in rows for p,sha in r['images'].items()}
    require(json.loads((folder/'preview.json').read_text())=={'rom_sha256':build['output_sha256'],'cases':16,'images':images},'Book/travel gallery stale')
    for p,sha in images.items():require(digest((folder/p).read_bytes())==sha,'Book/travel capture changed')
    for pattern in ('*.json','index.html','*/*.png','native/*.json'):
        for p in folder.glob(pattern):receipt['artifacts'][str(p.relative_to(ROOT))]=digest(p.read_bytes())
    counts['book-travel']=16;receipt['book_travel_scope']=report['scope'];receipt['book_travel_resources']=len(build['book_travel']['entries'])
