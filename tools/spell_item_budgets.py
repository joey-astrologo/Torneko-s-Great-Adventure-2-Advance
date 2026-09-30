"""Keep inscription font auditions tied to complete native row checks."""
import json
from tools.rom import ROOT,digest,require


def append_contexts(config,build):
    path=ROOT/'build/english/spell-item-validation/report.json';report=json.loads(path.read_text())
    require(report['passed'] and report['rom_sha256']==build['output_sha256'] and len(report['cases'])==125,'Spell inscription audition evidence incomplete')
    config['contexts']=[c for c in config['contexts'] if not c['id'].startswith('spell-item-current-')]
    names=[r for r in build['spell_info']['entries'] if r['kind']=='name']
    for start in range(0,len(names),8):
        group=names[start:start+8]
        config['contexts'].append({'id':f'spell-item-current-{start//8+1}','name':f'Inscribed spellbook names {start+1}-{start+len(group)}','stage':'current','window':168,'start':20,'end':130,'rows':len(group),'labels':['Sp. '+r['english'] for r in group],'alternatives':[],'reference':str(path.relative_to(ROOT)),'native_report_sha256':digest(path.read_bytes()),'capture':'build/english/spell-item-validation/43-priced-maximum/inventory.png','note':'110px name region conservatively reserves14px for markers after6px inset and38px for the native price region. Full spell names; Sp. abbreviates the category Spell. Native125cases independently check all61 selectors, ordinary/priced states, maximal six-digit price, markers,64-byte guards and restoration. Maximum base width97px; conservative complete byte bound63. Retained Japanese custom aliases and other inscriptions are separate.'})
