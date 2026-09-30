"""Font comparison samples from the verified spell menus and their ledger."""
import json,re
from tools.rom import ROOT,digest,require


def append_contexts(config,build):
    folder=ROOT/'build/english/spell-menu-validation'
    path=folder/'report.json';report=json.loads(path.read_text())
    require(report['passed'] and report['rom_sha256']==build['output_sha256'],'Spell menu audition evidence stale')
    config['contexts']=[c for c in config['contexts'] if not c['id'].startswith('spell-menu-current-')]
    common={'stage':'current','alternatives':[],'reference':str(path.relative_to(ROOT)),
            'native_report_sha256':digest(path.read_bytes())}
    for row in build['spell_menu']['entries']:
        if row['kind']!='action':continue
        labels=[re.sub(r'\{[^}]+\}','',line) for line in row['english'].split('\n')]
        config['contexts'].append(common|{'id':'spell-menu-current-'+row['id'],
            'name':'Spell actions: '+labels[1],'window':40,'start':6,'end':40,'rows':3,'labels':labels,
            'note':'Original40px window,6px inset,34px label region and8px outer-border gap. Native report checks enabled/disabled colours, cursor wrap, Info, actual Set/Unset and cancellation/reopening. Controlled learned-spell setup; ordinary acquisition and casting remain separate.'})
    targets={int(r['id'].split('.')[-1],16):r['english'] for r in build['spell_info']['entries'] if r['kind']=='target'}
    definitions=[r for r in build['spell_info']['definitions'] if r['menu_eligible']]
    for start in range(0,len(definitions),8):
        group=definitions[start:start+8]
        config['contexts'].append(common|{'id':f'spell-menu-current-list-{start//8+1}',
            'name':f'Spell rows {start+1}-{start+len(group)}','window':168,'start':20,'end':162,'rows':len(group),
            'labels':[r['name']+' ['+targets[0x8BC+4*r['target_kind']]+']' for r in group],
            'note':'Conservative142px name/target budget after reserving14px for the widest marker within the156px whole-row budget. Actual native row starts at6px; the audition reserves20px including that inset. Original64-byte formatter and168px window. All50 eligible names are checked in available/disabled native states.'})
