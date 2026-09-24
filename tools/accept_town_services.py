"""Require the bounded synthesis/Remi native evidence on the cumulative ROM."""
import json
from tools.rom import ROOT,digest,require


def validate(build,receipt,counts):
    families={
        'gaibara':{'report.json':39,'menus.json':5,'transactions.json':25,'selector.json':3},
        'remi':{'report.json':73,'menus.json':10,'pickers.json':21,'picker-fallbacks.json':3,
                'vocations.json':18,'saved-village.json':6,'safe.json':6,'charges.json':6,
                'levels.json':5,'warp-menus.json':17,'warp-payments.json':5}}
    reports={}
    for family,expected in families.items():
        folder=ROOT/f'build/english/{family}-validation';reports[family]={};seen=set()
        for filename,count in expected.items():
            path=folder/filename;report=json.loads(path.read_text())
            require(report['passed'] and report['rom_sha256']==build['output_sha256'],'Stale town service: '+family+'/'+filename)
            require(len(report['cases'])==count and len({r['case'] for r in report['cases']})==count,'Town service cases missing/duplicate: '+filename)
            seen.update(r['id'] for case in report['cases'] for r in case.get('reads',[]))
            reports[family][filename]=report;counts[family+'-'+filename.removesuffix('.json')]=count
            receipt['artifacts'][str(path.relative_to(ROOT))]=digest(path.read_bytes())
        expected_ids={r['id'] for r in build[family]['entries']}
        if family=='remi':
            expected_ids-={'remi.164','remi.165','remi.166'}
            expected_ids.update(r['id'] for r in build['remi']['warp_names']['entries'])
            arguments={r['index']:bytes.fromhex(r['encoded_hex'])[:-1] for r in build['remi']['entries'] if r['index'] in (164,165,166)}
            for vocation in range(3):
                cases=[r for r in reports[family]['vocations.json']['cases'] if r['case'].startswith(f'vocation-{vocation}-')]
                require(len(cases)==6 and all(any(f['id']=='remi.153' and arguments[164+vocation] in bytes.fromhex(f['expected_hex']) for f in r['formats']) for r in cases),'Vocation argument text missing')
            require({r['case'] for r in reports[family]['warp-menus.json']['cases'] if r['case'].startswith('select-')}=={'select-'+str(i) for i in (0,1,2,3,4,5,6,8,9,10)},'Warp destination selection missing')
            require(len([x for r in reports[family]['warp-menus.json']['cases'] for x in r['restorations']])==18,'Warp page restoration cases missing')
            require({r['case'] for r in reports[family]['safe.json']['cases']}=={'buy','exact-gold','decline','poor','full','already-owned'},'Iron safe service cases missing')
            require({r['case'] for r in reports[family]['charges.json']['cases']}=={'charge-five','charge-to-cap','decline','cancel-item','poor','no-staff'},'Staff charge service cases missing')
        else:
            expected_ids.update(r['id'] for r in build['selection_prompt']['entries'])
            require({r['case'] for r in reports[family]['selector.json']['cases']}=={'cancel','select-second','info-reopen'},'Item selector cases missing')
        require(expected_ids<=seen,'Town service source rendering missing: '+repr(sorted(expected_ids-seen)))
        for pattern in ('*.json','index.html','*/*.png','*/*.json','native/*.json'):
            for path in folder.glob(pattern):
                if path.is_file():receipt['artifacts'][str(path.relative_to(ROOT))]=digest(path.read_bytes())
    receipt.update(reviewed_synthesis_resources=len(build['gaibara']['entries']),
        reviewed_selection_prompt_resources=len(build['selection_prompt']['entries']),
        reviewed_remi_resources=len(build['remi']['entries'])+len(build['remi']['warp_names']['entries']),
        synthesis_native_cases=72,remi_native_cases=170,
        town_services_scope='Controlled service entry with native buttons, formatting, ownership, original windows and bounded transactions. Ordinary service unlocking remains separate. Remi warp payment/output is verified at consumer return; the later dispatcher transition and actual village overwrite/cold reload are not claimed.')
