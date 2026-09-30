"""Audition every verified Blank-scroll effect in its original inventory row."""
import json
from tools.rom import ROOT,digest,require

def append_contexts(config,build):
    path=ROOT/'build/english/scroll-item-validation/report.json';report=json.loads(path.read_text())
    require(report['passed'] and report['rom_sha256']==build['output_sha256'] and len(report['cases'])==77,'Scroll inscription audition evidence incomplete')
    config['contexts']=[c for c in config['contexts'] if not c['id'].startswith('scroll-item-current-')]
    names=[r for r in build['scroll_item']['entries'] if r['id'].startswith('scroll-item.effect.')]
    require({r['item_id'] for r in names}==set(range(116,153)),'Scroll audition effect set differs')
    for start in range(0,len(names),8):
        group=names[start:start+8]
        config['contexts'].append({'id':f'scroll-item-current-{start//8+1}','name':f'Inscribed scroll effects {start+1}-{start+len(group)}','stage':'current','window':168,'start':20,'end':130,'rows':len(group),'labels':['Blank: '+r['english'] for r in group],'alternatives':[],'reference':str(path.relative_to(ROOT)),'native_report_sha256':digest(path.read_bytes()),'capture':'build/english/scroll-item-validation/149-priced-maximum/inventory.png','note':'110px name region reserves14px for markers after6px inset and38px for price. Blank identifies the inscribed original; the complete reviewed effect replaces Japanese suffix truncation. All37 category0 non-spell selectors have normal/priced pixel and64-byte guard checks, plus maximum-price/marker stress. Maximum base101px; conservative complete byte bound63. Special/reserved states are controlled probes, not ordinary acquisition claims.'})
