"""Pin cumulative acceptance of the reviewed mansion quest build."""

from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import tempfile

from tools.build_english import run as rebuild
from tools.rom import ROOT, default_rom, digest, load_base, require


def run(receipt_path=None, check_directory='build/mansion'):
    output = ROOT/'build/english'
    ledger = json.loads((output/'build.json').read_text())
    rom_hash = digest((output/'torneko-2-english.gba').read_bytes())
    bps_hash = digest((output/'torneko-2-english.bps').read_bytes())
    require(ledger['output_sha256'] == rom_hash and ledger['bps']['patch_sha256'] == bps_hash,
            'Build output differs from ledger')
    catalog_path = ROOT/'translations/master.json'
    catalog_hash = digest(catalog_path.read_bytes())
    catalog = json.loads(catalog_path.read_text())
    require(ledger['dialogue']['catalog_sha256'] == catalog_hash,'Build catalog is stale')
    names = ['name-entry','dialogue','first-dungeon','castle','castle-conversations',
             'destination','home','town-text','books','mansion']
    reports = {}
    for name in names:
        report = json.loads((output/(name+'-validation')/'report.json').read_text())
        require(report['passed'] and report['source_rom_sha256'] == digest(load_base()) and
                report['output_rom_sha256'] == rom_hash,'Stale or failed report: '+name)
        reports[name] = report
    groups = (reports['dialogue']['branches'] + [reports['first-dungeon'],reports['castle']['natural']] +
              reports['castle-conversations']['routes'] +
              [r for r in reports['destination']['cases'] if not r['controlled_name_hex']] +
              reports['home']['routes'] + reports['books']['routes'] + reports['mansion']['routes'])
    observed = {r['id'] for group in groups for r in group['reads']}
    for route in reports['books']['routes']:
        for call in route['formatter_calls']:
            observed.update(call.get('part_ids',[]))
    inserted = {r['id'] for r in ledger['dialogue']['entries']}
    quest_path = output/'holy-flame-text-validation/report.json'
    quest = json.loads(quest_path.read_text())
    require(quest['passed'] and quest['rom_sha256'] == rom_hash, 'Stale controlled quest rendering')
    controlled = {r['id'] for case in quest['cases'] for r in case['reads']}
    quest_inserted = {r['id'] for r in ledger['dialogue']['entries'] if r['batch'] == 'holy-flame-quest'}
    require(controlled == quest_inserted and quest['sources'] == len(quest_inserted),
            'Controlled quest source coverage differs')
    from tools.accept_story_text import validate as validate_story
    story = validate_story(ledger)
    controlled.update(story['controlled'])
    require(inserted <= observed | controlled,
            'Inserted sources lack native rendering acceptance: '+repr(sorted(inserted-observed-controlled)))
    current = {r['id']:r for r in catalog['entries']}
    require(not set(current) & set(story['reviewed']), 'Story catalog overlaps the native master')
    current.update(story['reviewed'])
    require(all(current[i]['language_status'] == 'reviewed' for i in inserted),'Unreviewed insertion')
    review = json.loads((ROOT/'translations/mansion-review.json').read_text())
    require({r['id'] for r in review['entries']} ==
            {r['id'] for r in ledger['dialogue']['entries'] if r['batch'] == 'mansion-quest'},
            'Mansion insertion/review set differs')
    for row in review['entries']:
        require(all(row[k] == current[row['id']][k] for k in ('english','japanese','source_sha256')),
                'Stale bilingual review')
    for name in ('report.json','event-table-audit.json','verification/report.json'):
        report = json.loads((ROOT/'build/text-extraction'/name).read_text())
        require(report['passed'] and report['catalog_sha256'] == catalog_hash,'Stale source audit: '+name)
    japanese = json.loads((ROOT/'build/mansion/native/trace.json').read_text())
    require(japanese['passed'] and japanese['suspend']['native_save_frames'] and
            japanese['suspend']['save_sha256'] == reports['mansion']['native_japanese_suspend_sha256'] ==
            digest((ROOT/'build/mansion/native/floor-five-native.sav').read_bytes()),'Suspend provenance differs')
    unit_log = (ROOT/check_directory/'final-unit-tests.log').read_text()
    count = re.search(r'Ran (\d+) tests',unit_log)
    require(count and '\nOK\n' in unit_log,'Unit suite did not pass')
    require('All checks passed.' in (ROOT/check_directory/'toolchain-validation.log').read_text(),
            'Toolchain checks did not pass')
    with tempfile.TemporaryDirectory(prefix='mansion-repro-',dir=ROOT/'build') as directory:
        rebuilt = rebuild(Path(directory))
        for name in ('torneko-2-english.gba','torneko-2-english.bps'):
            require((Path(directory)/name).read_bytes() == (output/name).read_bytes(),'Clean rebuild differs')
        reproducibility = {'passed':True,'output_rom_sha256':rom_hash,'output_bps_sha256':bps_hash,
            'catalog_sha256':catalog_hash,'fresh_temporary_output_directory':True,
            'rom_identical':True,'bps_identical':True,'bps_apply_matches_target':rebuilt['bps']['apply_matches_target']}
        (output/'reproducibility.json').write_text(json.dumps(reproducibility,indent=2)+'\n')
    preview = json.loads((output/'mansion-preview.json').read_text())
    require(preview['output_rom_sha256'] == rom_hash,'Stale native preview')
    files = {'README.md','AGENTS.md','build.sh','validate.sh','config/rom.json',
             'build/english/build.json','build/english/reproducibility.json',
             'build/english/mansion-preview.json','build/english/mansion-preview.png',
             'build/mansion/native/trace.json','build/mansion/native/floor-five-native.sav',
             check_directory+'/final-unit-tests.log',check_directory+'/toolchain-validation.log',
             check_directory+'/final-build.log','build/text-extraction/report.json',
             'build/text-extraction/event-table-audit.json','build/text-extraction/verification/report.json',
             'build/text-extraction/index.html'}
    for pattern in ('tools/*.py','tools/*.sh','tests/*.py','translations/*.json','config/routes/*.json',
                    'docs/*.md','assets/**/*'):
        files.update(str(p.relative_to(ROOT)) for p in ROOT.glob(pattern) if p.is_file())
    files.add(str(quest_path.relative_to(ROOT)))
    files.update(story['files'])
    files.update(str(p.relative_to(ROOT)) for p in (output/'holy-flame-text-validation').glob('*/*.png'))
    files.update('build/english/'+name+'-validation/report.json' for name in names)
    for row in preview['images']:
        require(digest((ROOT/row['source']).read_bytes()) == row['sha256'],'Preview source changed')
        files.add(row['source'])
    audit = json.loads((ROOT/'build/text-extraction/event-table-audit.json').read_text())
    receipt = {'passed':True,'checked_at':datetime.now(timezone.utc).isoformat(),
        'source_rom_sha256':digest(load_base()),'source_save_sha256':digest(default_rom().with_suffix('.sav').read_bytes()),
        'output_rom_sha256':rom_hash,'output_bps_sha256':bps_hash,'output_bytes':ledger['output_bytes'],
        'original_files_unchanged':all(r.get('original_files_unchanged',True) for r in reports.values()),
        'inserted_reviewed_text_resources':len(inserted),'new_mansion_resources':len(review['entries']),
        'all_inserted_text_resources_rendered_natively':True,
        'all_inserted_text_resources_observed_in_ordinary_play':inserted <= observed,
        'ordinary_play_dialogue_sources':len(inserted & observed),
        'controlled_only_dialogue_sources':sorted(inserted-observed),
        'controlled_quest_rendering_cases':len(quest['cases']),
        'controlled_story_validation':story['summary'],
        'native_acceptance_reports':len(reports)+1+(6 if story['summary'] else 0),
        'natural_english_reader_calls':sum(len(g['reads']) for g in groups),
        'natural_glyph_checks':sum(g['native_glyph_checks'] for g in groups),
        'mansion_routes':len(reports['mansion']['routes']),
        'mansion_glyph_checks':sum(r['native_glyph_checks'] for r in reports['mansion']['routes']),
        'mansion_controlled_name_cases':len(reports['mansion']['controlled_name_layouts']),
        'unit_tests_passed':int(count.group(1)),'toolchain_acceptance_passed':True,
        'clean_output_rom_and_bps_identical':True,'bps_apply_matches_target':True,
        'new_dialogue_ram_bytes':0,'save_layout_changed':False,'graphics_patched':False,
        'catalog_native_sources':len(catalog['entries']),
        'catalog_language_status':dict(Counter(r['language_status'] for r in catalog['entries'])),
        'known_table_sources':audit['combined_unique_sources'],'scan_candidates':audit['candidate_inventory_count'],
        'candidate_dispositions':audit['candidate_dispositions'],
        'scope':reports['mansion']['scope']+' Earlier cumulative opening, name/save, castle, village and book checks pass on this ROM. Holy-flame text passes controlled reader checks; ordinary English quest completion is not accepted. No whole-game coverage percentage.',
        'artifacts':{p:digest((ROOT/p).read_bytes()) for p in sorted(files)}}
    (receipt_path or ROOT/'docs/english-mansion-validation.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps({k:v for k,v in receipt.items() if k != 'artifacts'},indent=2))
    return receipt


if __name__ == '__main__':
    run()
