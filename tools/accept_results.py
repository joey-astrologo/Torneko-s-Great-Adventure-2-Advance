"""Require all raw actor and reviewed cause cases on the matching cumulative ROM."""
import json
from tools.rom import ROOT, digest, require


def validate(build, receipt, counts):
    folder = ROOT/'build/english/results-validation'
    report = json.loads((folder/'report.json').read_text())
    resources = build['results']
    expected = {f'{family}-{ident}' for family in ('results','history') for ident in range(141)}
    expected |= {f'{family}-cause-{reason}' for family in ('results','history') for reason in set(range(28))-{21}}
    rows = report['cases']
    require(report['passed'] and report['rom_sha256'] == build['output_sha256'], 'Stale results evidence')
    require(len(rows) == len(expected) and {r['case'] for r in rows} == expected, 'Results case coverage differs')
    require(len(resources['entries']) == 141 and len(resources['causes']) == 27 and resources['other_defeat'],
            'Results resource coverage differs')
    require(all(r['visible_pixels_checked'] > 0 and len(r['reads']) == len(r['formats']) == 1 and
                r['formats'][0]['tail_guard_abi_match'] for r in rows), 'Results final-screen/format evidence incomplete')
    ids = {r['case']: r for r in rows}
    require(ids['results-0']['english_actor'] == 'Someone' and ids['history-0']['english_actor'] == 'Torneko' and
            ids['results-131']['english_actor'] == ids['history-131']['english_actor'] == 'False priest',
            'Raw/dungeon/special history identity distinction lost')
    images = {r['case']+'/'+p: sha for r in rows for p,sha in r['images'].items()}
    preview = json.loads((folder/'preview.json').read_text())
    require(preview['rom_sha256'] == build['output_sha256'] and preview['cases'] == len(rows) and
            preview['images'] == images, 'Stale results gallery')
    for path,sha in images.items():
        require(digest((folder/path).read_bytes()) == sha, 'Results image changed')
    for pattern in ('*.json','index.html','*/*.png','native/*.json'):
        for path in folder.glob(pattern):
            receipt['artifacts'][str(path.relative_to(ROOT))] = digest(path.read_bytes())
    counts['results'] = len(rows)
    receipt.update(results_resources=171+len(resources.get('ui_entries',[])), results_native_cases=len(rows), results_scope=report['scope'])
    if resources.get('ui_entries'):
        from tools.extract_items import extract
        named={int(r['id'].split('.')[-1]) for r in build['items']['entries'] if r['id'].startswith('item.name.')}
        equipment=[r['id'] for r in extract()['items'] if r['category'] in (1,3,6) and r['id'] in named]
        common={f'dungeon-{i}-reason-{reason}' for i in range(13) for reason in (21,32,33)}
        common|={'bounds-'+s for s in ('zero','maximum','signed-minimum')}
        common|={f'exit-{r}-kind-{k}' for r,k in ((32,0),(32,1),(32,2),(34,0),(35,0),(36,0))}
        result_cases=common|{f'equipment-{i}-{s}' for i in equipment for s in ('identified','unidentified','cursed','maximum-fields','priced','priced-maximum','priced-cursed-maximum','ability-present')}
        history_cases=common|{'history-'+s for s in ('minimum','maximum','time-59','rank-50','empty','navigate')}
        menu_cases={f'{variant}-{action}' for variant in ('two','three') for action in ('navigate','scores','populated-scores','records')}|{'three-password'}
        require(len(resources['ui_entries'])==33 and len(build['history']['entries'])==9 and len(build['history_menu']['entries'])==2,'Results/history UI resources differ')
        for family,expected in (('ui-validation',result_cases),('history-ui-validation',history_cases),('history-menu-validation',menu_cases)):
            path=ROOT/'build/english'/family
            evidence=json.loads((path/'report.json').read_text());cases=evidence['cases']
            require(evidence['passed'] and evidence['rom_sha256']==build['output_sha256'],'Stale '+family)
            require(len(cases)==len(expected) and {r['case'] for r in cases}==expected,'Incomplete '+family)
            require(all(r['visible_pixels_checked']>0 and r['reads'] and r['return'] for r in cases),'Incomplete final-screen/return evidence '+family)
            if family!='history-menu-validation':
                require(all(f['guard_tail_abi_match'] for r in cases for f in r['formats']),'Result UI format guard/ABI failure')
            images={r['case']+'/'+p:sha for r in cases for p,sha in r['images'].items()}
            preview=json.loads((path/'preview.json').read_text())
            require(preview=={'rom_sha256':build['output_sha256'],'cases':len(cases),'images':images},'Stale '+family+' gallery')
            for p,sha in images.items():require(digest((path/p).read_bytes())==sha,'Changed '+family+' capture')
            for pattern in ('*.json','index.html','*/*.png','native/*.json'):
                for artifact in path.glob(pattern):receipt['artifacts'][str(artifact.relative_to(ROOT))]=digest(artifact.read_bytes())
            counts[family]=len(cases)
        receipt.update(history_resources=9,history_menu_resources=2,result_ui_cases=len(result_cases),history_ui_cases=len(history_cases),history_menu_cases=len(menu_cases))
