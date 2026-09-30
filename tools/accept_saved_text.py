"""Pin shop, reference-list, town-root and save-panel native evidence."""
import json
from tools.rom import ROOT,digest,require

COHORTS={'dungeon-shop':('dungeon_shop',16,5),'save-notices':('save_notices',2,2),
         'reference-lists':('reference_lists',9,5),'priest-warning':('priest_warning',2,1),
         'save-preview':('save_preview',56,20),'town-root':('town_root',4,1)}

def validate(build,receipt,counts,source=ROOT/'build/english'):
    for family,(key,count,resources) in COHORTS.items():
        folder=source/(family+'-validation');path=folder/'report.json'
        report=json.loads(path.read_text());rows=report['cases'];entries=build[key]['entries']
        require(report['passed'] and report['rom_sha256']==build['output_sha256'],'Stale additional text evidence: '+family)
        require(len(entries)==resources and len(rows)==count and len({r['case'] for r in rows})==count,'Incomplete additional text cohort: '+family)
        require(all(r['visible_pixels_checked']>0 and r['inputs'] and r['images'] for r in rows),'Missing additional text pixels/inputs: '+family)
        if family!='save-preview':require(all(r['caller_guard_abi_preserved'] for r in rows),'Additional text caller guard missing: '+family)
        if family=='dungeon-shop':
            require({r['id'] for r in rows}=={r['id'] for r in entries},'Dungeon shop sources missing')
            for owner in ('sell','buy','half-price'):
                require({r['amount'] for r in rows if r['owner']==owner}=={0,17,999999,2147483647},'Dungeon quote bounds missing')
            require(all(len(r['reads'])==len(r['modals'])==len(r['modal_returns'])==1 and all(f['guard_abi_preserved'] for f in r['formats']) for r in rows),'Dungeon shop modal/guard evidence missing')
        elif family=='save-notices':
            require({r['case'] for r in rows}=={'suspend','corrupt'} and {r['id'] for r in rows}=={r['id'] for r in entries},'Save notice sources missing')
            for row in rows:
                require({'page-0.png','page-1.png'}<=set(row['images']) if row['case']=='suspend' else 'page-0.png' in row['images'],'Save notice pagination missing')
                require(len(row['modals'])==len(row['modal_returns'])==1,'Save notice modal return missing')
        elif family=='reference-lists':
            require({r['case'] for r in rows}=={f'categories-{i}' for i in (1,3,7)}|{f'{kind}-{state}' for kind in ('scroll','skill','spell') for state in ('known','locked')},'Reference menu states missing')
            rom=(source/'torneko-2-english.gba').read_bytes()
            eligible={'scroll':set(rom[0x148343:0x14835E]),'skill':{r['id'] for r in build['skill_info']['definitions'] if r['menu_eligible']},'spell':{r['id'] for r in build['spell_info']['definitions'] if r['menu_eligible']}}
            for row in rows:
                if row['kind']:require(set(row['covered_ids'])==(eligible[row['kind']] if row['known'] else set()),'Reference name coverage differs')
                require(all(f['guard_abi_preserved'] for f in row['formats']),'Reference formatter guards missing')
            require({r['id'] for r in entries}<=({r['id'] for c in rows for r in c['reads']}|{ident for c in rows for f in c['formats'] for ident in f['label_ids']}),'Reference static labels missing')
        elif family=='priest-warning':
            require({r['field'] for r in rows}=={'player','monster'} and {r['id'] for r in rows}=={r['id'] for r in entries},'Priest expiry recipients missing')
            require(all(not r['visual_effect_skips'] and all(f['guard_abi_match'] for f in r['formats']) for r in rows),'Priest expiry scope/guards differ')
        elif family=='save-preview':
            native=[r for r in rows if r['native_resume']]
            require({r['case'] for r in native}=={'native-town','native-dungeon'} and all(len(r['returns'])==1 for r in native),'Native save Continue evidence missing')
            require({(r['kind'],r['profile']) for r in rows if not r['native_resume']}=={(kind,profile) for kind in list(range(13))+['town-0','town-1','town-2','town-3','completed'] for profile in ('ordinary','wide-English','wide-Japanese')},'Save preview selector/name profiles differ')
            require(all(r['source_save_sha256'] and len(r['formats'])==1 and all(f['formatter_guard_abi_preserved'] for f in r['formats']) for r in rows),'Save preview formatter/source evidence missing')
        elif family=='town-root':
            require({r['case'] for r in rows}=={'cancel','items-empty','items-populated','option'},'Town root states missing')
            require(all(len(r['children'])==(0 if r['case']=='cancel' else 2) and len(r['reads'])==(1 if r['case']=='cancel' else 3) for r in rows),'Town root child/reopening evidence missing')
        images={r['case']+'/'+p:sha for r in rows for p,sha in r['images'].items()}
        require(json.loads((folder/'preview.json').read_text())=={'rom_sha256':build['output_sha256'],'cases':count,'images':images},'Stale additional text gallery: '+family)
        for p,sha in images.items():require(digest((folder/p).read_bytes())==sha,'Changed additional text capture: '+p)
        for pattern in ('*.json','index.html','*/*.png','native/*.json'):
            for p in folder.glob(pattern):receipt['artifacts'][str(p.relative_to(ROOT))]=digest(p.read_bytes())
        counts[family]=count;receipt[family+'_scope']=report['scope']
    receipt['additional_saved_text_resources']=sum(v[2] for v in COHORTS.values())
