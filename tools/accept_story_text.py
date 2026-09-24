"""Require current-ROM evidence for ordinary prose and each special consumer."""
import json
from collections import Counter
from tools.rom import ROOT,digest,require
from tools.opening_text import banks
from tools.event_text import table_entries
from tools.emulator import Snapshot

def validate(ledger):
    if not ledger['dialogue'].get('story_consumers'):
        return {'controlled':set(),'reviewed':{},'files':set(),'summary':{}}
    rom_hash=ledger['output_sha256'];output=ROOT/'build/english'
    reviewed={};files=set();controlled=set();summary={}
    specs=[('event-prose','event-prose-review.json','event-prose-validation',None),
           ('floor_progress','floor-progress-review.json','floor-progress-validation',27),
           ('well_level','well-level-review.json','well-level-validation',40),
           ('village_prose','village-prose-review.json','village-prose-validation',12),
           ('medals','medal-review.json','medal-validation',33),
           ('story_commands','story-commands-review.json','story-command-validation',45)]
    for family,catalog_name,directory,count in specs:
        catalog_path=ROOT/'translations'/catalog_name;catalog=json.loads(catalog_path.read_text())
        rows={r['id']:r for r in ledger['dialogue']['entries'] if r['batch']==family}
        require(set(rows)=={r['id'] for r in catalog['entries']},'Story review/build selection differs: '+family)
        evidence=(ledger['dialogue']['event_prose_review_sha256'] if family=='event-prose' else
                  ledger[family].get('review_sha256',ledger[family].get('catalog_sha256')))
        require(evidence==digest(catalog_path.read_bytes()),'Story review catalog stale: '+family)
        for row in catalog['entries']:
            require(row['status']=='reviewed' and row['prose_review']
                    and row['source_sha256']==rows[row['id']]['source_sha256'],'Story language/source review differs')
            require(row['id'] not in reviewed,'Overlapping story reviews')
            reviewed[row['id']]=row|{'language_status':'reviewed'}
        path=output/directory/'report.json';report=json.loads(path.read_text())
        require(report['passed'] and report['rom_sha256']==rom_hash,'Stale story report: '+family)
        files.add(str(path.relative_to(ROOT)))
        if family=='event-prose':
            expected={(row['id'],label) for row in rows.values()
                      for label in (('required-English','widest-English','widest-Japanese')
                                    if any(c in row['layout']['commands'] for c in ('{player}','{initial}')) else ('native',))}
            fixture=Snapshot.load(output/directory/'native/reader-entry')
            require(fixture.rom_sha256==rom_hash,'Stale prose reader fixture')
            revision=digest((ROOT/'tools/verify_prose_preflight.py').read_bytes()
                            +(ROOT/'tools/dialogue_checks.py').read_bytes()+(ROOT/'tools/emulator.py').read_bytes())
            cases=set();glyphs=0
            for relative in report['case_reports']:
                case_path=ROOT/relative
                require(case_path.resolve().is_relative_to((output/directory).resolve()),'Prose case outside evidence directory')
                case=json.loads(case_path.read_text());key=case['cache_key'];ident=key['id'];pair=(ident,key['case'])
                require(pair in expected and pair not in cases and case['passed'],'Unexpected/duplicate prose case')
                require(key['rom_sha256']==rom_hash and key['fixture_sha256']==digest(fixture.state)
                        and key['verifier_sha256']==revision,'Stale prose case provenance')
                require(case['source_sha256']==rows[ident]['source_sha256']
                        and {r['id'] for r in case['reads']}=={ident},'Prose case checks the wrong source')
                for image,sha in case['images'].items():
                    image_path=case_path.parent/image
                    require(digest(image_path.read_bytes())==sha,'Prose screenshot differs')
                    files.add(str(image_path.relative_to(ROOT)))
                files.add(relative);cases.add(pair);glyphs+=case['glyph_checks']
            require(cases==expected and report['cases']==len(cases) and report['sources']==len(rows)
                    and report['glyph_checks']==glyphs,'Incomplete prose rendering coverage')
            summary['ordinary_prose']={'sources':len(rows),'cases':len(cases),'glyph_checks':glyphs}
        else:
            cases=report['cases'];require(len(cases)==count and len({c['case'] for c in cases})==count,
                                         'Missing story consumer cases: '+family)
            require({r['id'] for case in cases for r in case['reads']}==set(rows),'Missing consumer source reads: '+family)
            if family=='well_level':
                require(Counter(c['level'] for c in cases)==Counter({i:4 for i in range(1,11)}),'Missing native well levels')
                require(len(catalog['labels'])==len(ledger[family]['labels'])==10,'Incomplete private well labels')
                require(ledger[family]['labels']==[r|{'offset':built['offset'],'encoded_hex':built['encoded_hex']}
                                                  for r,built in zip(catalog['labels'],ledger[family]['labels'])],
                        'Well private label review differs')
            if family=='story_commands':
                require(Counter(c['id'] for c in cases)==Counter({ident:3 for ident in rows}),
                        'Story announcement name cases missing')
                require(all(len(c['commands'])==len(c['sounds'])==1 and c['commands'][0]['command']=='@A@'
                            and c['commands'][0]['abi_preserved'] and c['sounds'][0]['id']==0x10F
                            and c['sounds'][0]['parameter']==10 and c['wrapper_abi_preserved']
                            and c['inventory_gold_flags_battery_preserved'] for c in cases),
                        'Story announcement callback evidence incomplete')
            summary[family]={'sources':len(rows),'cases':count}
            if 'capacity' in ledger[family]:summary[family]['stack_capacity']=ledger[family]['capacity']
        controlled.update(rows)
        for pattern in ('*/*.png','native/*.json'):
            files.update(str(p.relative_to(ROOT)) for p in (output/directory).glob(pattern))
    path=output/'event-bindings-validation/report.json';bindings=json.loads(path.read_text())
    require(bindings['passed'] and bindings['rom_sha256']==rom_hash,'Stale actual-ROM event binding proof')
    expected={(b['id'],e['group'],e['index']) for b in banks() for e in table_entries(b)}
    actual=[(case['bank'],e['group'],e['index']) for case in bindings['cases'] for e in case['getter_cases']]
    require(len(actual)==len(expected) and set(actual)==expected,'Incomplete native getter coverage')
    targets={r['id']:r['rom_offset']+0x08000000 for r in ledger['dialogue']['entries'] if r['id'].startswith('event-bank-')}
    seen=set()
    for case in bindings['cases']:
        for word in case['controlled_table_words']:
            require(word['before']==word['after'] and word['target']==targets[word['id']],
                    'Binding proof replaced a ROM offset in RAM or used the wrong target')
            seen.add(word['id'])
    require(seen==set(targets),'Some inserted event sources lack actual-ROM getter proof')
    files.add(str(path.relative_to(ROOT)));summary['native_event_getters']=len(actual)
    return {'controlled':controlled,'reviewed':reviewed,'files':files,'summary':summary}
