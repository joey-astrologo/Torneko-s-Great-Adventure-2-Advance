"""Acceptance for the native non-displaying identity formatter."""
import json
from tools.rom import ROOT,digest,require

def validate(build,receipt,counts,source=ROOT/'build/english'):
 p=source/'monster-identity-validation/report.json';r=json.loads(p.read_text());cases=r['cases'];widest=max(build['monsters']['entries'],key=lambda x:x['width_px'])['id'];expected={f'{i}-1-native' for i in range(141)}|{f'{widest}-32767-native'}|{'1-1-'+s for s in ('maximum-width','maximum-bytes','coloured')};require(r['passed'] and r['rom_sha256']==build['output_sha256'] and len(cases)==len(expected)==145 and {c['case'] for c in cases}==expected,'Monster identity evidence stale/incomplete');require(all(c['no_display_calls'] and c['owner_abi_guard_preserved'] and c['gameplay_save_preserved'] and len(c['formats'])==1 and c['formats'][0]['guard_abi_preserved'] and c['formats'][0]['bytes']<=build['monster_identity']['entries'][0]['maximum_bytes'] for c in cases),'Monster identity evidence incomplete');receipt['artifacts'][str(p.relative_to(ROOT))]=digest(p.read_bytes());counts['monster_identity']=145;receipt['monster_identity_scope']=r['scope']
