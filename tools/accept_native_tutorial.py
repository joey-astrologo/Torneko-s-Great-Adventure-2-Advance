import json
from tools.rom import ROOT,digest,require

def validate(build,receipt,counts,source=ROOT/'build/english'):
 folder=source/'native-tutorial-validation';r=json.loads((folder/'report.json').read_text());require(r['passed'] and r['rom_sha256']==build['output_sha256'] and not r['japanese_glyph_leads'] and len(r['pickups'])==len(r['checks'])==14 and {p['floor'] for p in r['pickups']}=={1,2,3} and all(c['complete'] and c['returned'] for c in r['checks']),'Fresh tutorial evidence stale/incomplete')
 require(digest((ROOT/r['fixture']).with_suffix('.state').read_bytes())==r['fixture_state_sha256'],'Fresh tutorial source checkpoint changed')
 require(digest((ROOT/r['fixture']).parent.joinpath('report.json').read_bytes())==r['opening_report_sha256'],'Fresh tutorial opening provenance changed')
 for p,sha in r['images'].items():require(digest((folder/p).read_bytes())==sha,'Fresh tutorial capture changed');receipt['artifacts'][str((folder/p).relative_to(ROOT))]=sha
 for p in (folder/'report.json',folder/'index.html'):receipt['artifacts'][str(p.relative_to(ROOT))]=digest(p.read_bytes())
 counts['native_tutorial_pickups']=14;receipt['native_tutorial_scope']=r['scope']
