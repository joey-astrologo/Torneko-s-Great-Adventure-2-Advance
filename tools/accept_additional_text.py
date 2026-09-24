"""Require current-ROM evidence for village naming, well selection and warnings."""
import json
from tools.rom import ROOT,digest,require
from tools.dialogue_checks import player_layout_cases


def validate(build,receipt,counts):
    families={'mayor':{'report.json':12,'editor.json':5,'persistence.json':3},
              'well-picker':{'report.json':20},'hunger':{'report.json':7},
              'status-traps':{'report.json':18}}
    all_reports={}
    for family,files in families.items():
        folder=ROOT/f'build/english/{family}-validation';all_reports[family]={}
        for filename,count in files.items():
            report=json.loads((folder/filename).read_text());rows=report['cases']
            require(report['passed'] and report['rom_sha256']==build['output_sha256'],'Stale additional text evidence: '+family+'/'+filename)
            require(len(rows)==count and len({r['case'] for r in rows})==count,'Additional text cases missing/duplicate: '+family+'/'+filename)
            all_reports[family][filename]=rows;counts[family+'-'+filename.removesuffix('.json')]=count
        for pattern in ('*.json','*.sav','index.html','*/*.png','*/*.json','native/*.json'):
            for path in folder.glob(pattern):
                if path.is_file():receipt['artifacts'][str(path.relative_to(ROOT))]=digest(path.read_bytes())
    mayor=all_reports['mayor']
    require({r['id'] for r in mayor['report.json']}=={r['id'] for r in build['mayor']['entries']},'Mayor source coverage missing')
    require({r['case'] for r in mayor['editor.json']}=={'decline','cancel-editor','required','maximum','redo'},'Mayor editor paths missing')
    require({r['case'] for r in mayor['persistence.json']}=={'required','maximum','redo'},'Mayor save/cold-load paths missing')
    well=all_reports['well-picker']['report.json']
    require({r['case'] for r in well}=={f'progress-{p}-{a}' for p in (1,2,9,10,255) for a in ('cancel','initial','minimum','maximum')},'Well picker boundaries missing')
    require({r['id'] for case in well for r in case['reads']}=={'well-picker.prompt','well-picker.level'} and all(case['formats'] for case in well),'Well prompt/number rendering missing')
    hunger=all_reports['hunger']['report.json']
    require({r['case'] for r in hunger}=={'twenty','ten','empty-first','empty-second','empty-third','above-twenty','empty-later'},'Hunger transitions missing')
    require({t['slot'] for r in hunger for t in r['transitions']}=={r['table_offset'] for r in build['hunger']['entries']},'Hunger sources missing')
    traps=all_reports['status-traps']['report.json']
    require({r['case'] for r in traps}=={f'{kind}-{failed}-{name}' for kind in ('sleep','hallucination','confusion') for failed in (0,1) for name,_ in player_layout_cases()},'Trap activation/name cases missing')
    require({r['table_offset'] for r in build['status_traps']['entries']}<={slot for case in traps for slot in case['queue_slots']},'Trap sources missing')
    receipt.update(additional_text_native_cases=65,additional_text_resources=18,
        additional_text_scope='Village renaming has controlled entry, ordinary keyboard choices and three ordinary book-save/cold-load checks. Well selection has controlled progress values and native bounds/output. Hunger uses controlled fullness/counter then ordinary attacks. Three trap handlers use controlled entry, activation and cleared resistance fields with complete message chains and native timers. Ordinary unlocking, well dungeon entry, trap discovery/resistance and other handlers remain separate.')
