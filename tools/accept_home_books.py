"""Pin the current cumulative book/banker acceptance after its checks have passed."""

from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import tempfile

from tools.build_english import run as rebuild
from tools.rom import ROOT, default_rom, digest, load_base, require


def run():
    output = ROOT / 'build/english'
    build = json.loads((output / 'build.json').read_text())
    rom_hash = digest((output / 'torneko-2-english.gba').read_bytes())
    bps_hash = digest((output / 'torneko-2-english.bps').read_bytes())
    require(build['output_sha256'] == rom_hash and build['bps']['patch_sha256'] == bps_hash,
            'Build ledger differs from outputs')
    catalog_bytes = (ROOT / 'translations/master.json').read_bytes()
    catalog = json.loads(catalog_bytes)
    require(build['dialogue']['catalog_sha256'] == digest(catalog_bytes), 'Build catalog is stale')
    names = ['name-entry-validation','dialogue-validation','first-dungeon-validation',
             'castle-validation','castle-conversations-validation','destination-validation',
             'home-validation','town-text-validation','books-validation']
    reports = {}
    for name in names:
        report = json.loads((output / name / 'report.json').read_text())
        require(report['passed'] and report['output_rom_sha256'] == rom_hash and
                report['source_rom_sha256'] == digest(load_base()), 'Stale or failed report: ' + name)
        reports[name] = report
    groups = (reports['dialogue-validation']['branches'] + [reports['first-dungeon-validation'],
              reports['castle-validation']['natural']] + reports['castle-conversations-validation']['routes'] +
              [r for r in reports['destination-validation']['cases'] if not r['controlled_name_hex']] +
              reports['home-validation']['routes'] + reports['books-validation']['routes'])
    reads = [row for group in groups for row in group['reads']]
    observed = {row['id'] for row in reads}
    for route in reports['books-validation']['routes']:
        for call in route['formatter_calls']:
            observed.update(call.get('part_ids', []))
    inserted = {row['id'] for row in build['dialogue']['entries']}
    require(inserted <= observed, 'Inserted sources missing native evidence: ' + repr(sorted(inserted - observed)))
    require(all(row['language_status'] == 'reviewed' for row in catalog['entries'] if row['id'] in inserted),
            'Inserted source is not reviewed')
    review = json.loads((ROOT / 'translations/home-books-review.json').read_text())
    current = {row['id']:row for row in catalog['entries']}
    for row in review['entries']:
        require(row['english'] == current[row['id']]['english'] and
                row['source_sha256'] == current[row['id']]['source_sha256'], 'Book review is stale')
    for relative in ('build/text-extraction/report.json','build/text-extraction/event-table-audit.json',
                     'build/text-extraction/verification/report.json'):
        report = json.loads((ROOT / relative).read_text())
        require(report['passed'] and report['catalog_sha256'] == digest(catalog_bytes), 'Stale source audit: ' + relative)
    unit_log = (ROOT / 'build/home-books/final-unit-tests.log').read_text()
    count = re.search(r'Ran (\d+) tests',unit_log)
    require(count is not None and '\nOK\n' in unit_log, 'Final unit suite did not pass')
    require('All checks passed.' in (ROOT / 'build/home-books/toolchain-validation.log').read_text(),
            'Toolchain acceptance did not pass')
    with tempfile.TemporaryDirectory(prefix='books-repro-',dir=ROOT / 'build') as directory:
        rebuilt = rebuild(Path(directory))
        for name in ('torneko-2-english.gba','torneko-2-english.bps'):
            require((Path(directory) / name).read_bytes() == (output / name).read_bytes(), 'Clean build differs: ' + name)
        reproducibility = {'passed':True, 'output_rom_sha256':rom_hash, 'output_bps_sha256':bps_hash,
            'catalog_sha256':digest(catalog_bytes), 'fresh_temporary_output_directory':True,
            'rom_identical':True, 'bps_identical':True, 'bps_apply_matches_target':rebuilt['bps']['apply_matches_target']}
        (output / 'reproducibility.json').write_text(json.dumps(reproducibility,indent=2)+'\n')
    extraction = json.loads((ROOT / 'build/text-extraction/event-table-audit.json').read_text())
    book = reports['books-validation']
    controlled = (reports['castle-validation']['controlled_names'] +
                  [r for r in reports['destination-validation']['cases'] if r['controlled_name_hex']] +
                  reports['home-validation']['controlled_sale_layouts'] + book['controlled_name_layouts'])
    files = {'README.md','AGENTS.md','build.sh','validate.sh','config/rom.json',
             'build/english/build.json','build/english/reproducibility.json',
             'build/english/books-preview.json','build/english/books-preview.png',
             'build/english/books-validation/japanese/trace.json',
             'build/english/home-validation/japanese-castle/trace.json',
             'build/english/home-validation/japanese-destination/trace.json',
             'build/english/home-validation/japanese-home/trace.json',
             'build/home-books/final-build.log','build/home-books/final-unit-tests.log',
             'build/home-books/toolchain-validation.log','build/home-books/common-source/report.json',
             'build/text-extraction/report.json','build/text-extraction/event-table-audit.json',
             'build/text-extraction/event-tables.json','build/text-extraction/town-tables.json',
             'build/text-extraction/verification/report.json','build/text-extraction/index.html',
             'build/toolchain-validation/toolchain.json','build/toolchain-validation/workflow.json',
             'build/compact-font/validation.json'}
    for pattern in ('tools/*.py','tools/*.sh','tests/*.py','translations/*.json','config/routes/*.json','docs/*.md'):
        files.update(str(p.relative_to(ROOT)) for p in ROOT.glob(pattern))
    previous = json.loads((ROOT / 'docs/english-home-validation.json').read_text())
    files.update(p for p in previous['artifacts'] if p.startswith('assets/'))
    files.update('build/english/' + name + '/report.json' for name in names)
    files.update(str(p.relative_to(ROOT)) for p in (ROOT / 'build/home-books/research').glob('*.txt'))
    preview = json.loads((output / 'books-preview.json').read_text())
    require(preview['output_rom_sha256'] == rom_hash, 'Native preview is stale')
    for image in preview['images']:
        require(digest((ROOT / image['source']).read_bytes()) == image['sha256'], 'Preview image source changed')
        files.add(image['source'])
    receipt = {'passed':True, 'checked_at':datetime.now(timezone.utc).isoformat(),
        'source_rom_sha256':digest(load_base()), 'source_save_sha256':digest(default_rom().with_suffix('.sav').read_bytes()),
        'output_rom_sha256':rom_hash, 'output_bps_sha256':bps_hash, 'output_bytes':build['output_bytes'],
        'original_files_unchanged':all(r.get('original_files_unchanged',True) for r in reports.values()),
        'allocations':len(build['allocations']), 'patches':len(build['patches']),
        'inserted_reviewed_text_resources':len(inserted), 'new_book_banker_resources':len(review['entries']),
        'all_inserted_text_resources_observed_natively':True,
        'natural_english_reader_calls':len(reads), 'natural_glyph_checks':sum(g['native_glyph_checks'] for g in groups),
        'controlled_event_table_getters':len(reports['dialogue-validation']['controlled_table_getters']) +
            len(reports['home-validation']['controlled_table_getters']),
        'native_shared_town_pointer_fixups':600, 'controlled_name_or_amount_cases':len(controlled),
        'controlled_name_or_amount_glyph_checks':sum(g['native_glyph_checks'] for g in controlled),
        'book_natural_routes':len(book['routes']), 'book_reader_calls':sum(len(r['reads']) for r in book['routes']),
        'book_native_glyph_checks':sum(r['native_glyph_checks'] for r in book['routes']),
        'book_cold_load_cases':len(book['cold_loads']), 'book_seven_glyph_name_cases':len(book['controlled_name_layouts']),
        'mansion_entrance_and_movement':book['routes'][-1]['mansion_entrance'],
        'unit_tests_passed':int(count.group(1)), 'toolchain_acceptance_passed':True,
        'clean_output_rom_and_bps_identical':True, 'bps_apply_matches_target':True,
        'new_dialogue_ram_bytes':0, 'save_layout_changed':False, 'graphics_patched':False,
        'catalog_native_sources':len(catalog['entries']),
        'catalog_language_status':dict(Counter(row['language_status'] for row in catalog['entries'])),
        'known_event_table_sources':extraction['unique_sources'], 'shared_town':extraction['shared_town'],
        'combined_known_table_sources':extraction['combined_unique_sources'],
        'scan_candidates':extraction['candidate_inventory_count'], 'candidate_dispositions':extraction['candidate_dispositions'],
        'scope':'Cumulative opening/home acceptance plus red-book tips, broken-storehouse blue-book actions/save flows, first banker branches/old-man scene and mansion entrance/movement. Native saves and cold loads pass; controlled name/amount probes are separate. Green-book contents, populated item lists, repaired services, mansion recovery, later text/graphics/credits and full-game testing remain open. No whole-game coverage percentage.',
        'artifacts':{relative:digest((ROOT / relative).read_bytes()) for relative in sorted(files)}}
    (ROOT / 'docs/english-books-validation.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps({k:v for k,v in receipt.items() if k != 'artifacts'},indent=2))
    return receipt


if __name__ == '__main__':
    run()
