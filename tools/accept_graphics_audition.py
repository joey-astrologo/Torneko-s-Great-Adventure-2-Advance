"""Bind offline graphics studios to their extraction, browser and native evidence."""
import json

from PIL import Image

from tools.extract_graphics_audition import save_json
from tools.rom import ROOT, digest, load_base, require


def read(relative):
    return json.loads((ROOT/relative).read_text())


def run():
    source_rom = load_base()
    base = digest(source_rom)
    cm = read('build/credits/manifest.json')
    am = read('build/arrival-cards/manifest.json')
    credit = read('build/credits/research/report.json')
    arrival = read('build/arrival-cards/native/report.json')
    require(all(r['source_rom_sha256'] == base for r in (cm, am, credit, arrival)),
            'Graphics evidence uses different ROMs')
    require(credit['passed'] and arrival['passed'], 'Native graphics checks did not pass')
    require(cm['decoded_sha256'] == credit['decoded_sha256'], 'Credits decode differs')
    require(credit['generator_sha256'] == digest((ROOT/'tools/research_credits.py').read_bytes()),
            'Stale credit native generator')
    require(set(credit['fully_covered_lines']) == {l['id'] for l in cm['lines']},
            'Credit visible-line coverage incomplete')
    require(len(cm['lines']) == 67 and len(cm['sections']) == 15, 'Credit inventory changed')
    credit_start, credit_end = cm['source']['start'], cm['source']['end_exclusive']
    development_rom = (ROOT/'build/torneko-2-english.gba').read_bytes()
    require(development_rom[credit_start:credit_end] == source_rom[credit_start:credit_end],
            'Approved original GBA credit artwork changed in the development ROM')
    require({(r['selector'], r['floor']) for r in arrival['cases']} ==
            {(i, 1) for i in range(13)} | {(11, n) for n in (10, 99, 999)} | {(12, 10), (12, 11)},
            'Arrival native cases incomplete')
    require(all(r['pixels_compared'] == 38400 for r in arrival['cases']), 'Arrival pixel scope differs')
    for row in arrival['cases']:
        path=ROOT/'build/arrival-cards/native'/row['id']/'card.png'
        require(digest(path.read_bytes()) == row['png_sha256'], 'Native arrival screenshot changed')
    browser = {}
    for family in ('credits', 'arrival-cards'):
        folder = ROOT/'build'/family/'audition'
        built = json.loads((folder/'build.json').read_text())
        checked = json.loads((folder/'browser-checks.json').read_text())
        require(built['source_rom_sha256'] == base and checked['passed'], 'Studio source or browser check differs')
        require(digest((folder/'index.html').read_bytes()) == built['html_sha256'] == checked['html_sha256'],
                'Stale studio browser receipt')
        require(checked['checks_sha256'] == digest((ROOT/'tools/check_graphics_audition.js').read_bytes()),
                'Stale browser verifier')
        for path, wanted in built['inputs'].items():
            require(digest((ROOT/path).read_bytes()) == wanted, 'Stale studio input: '+path)
        if family == 'credits':
            require(checked['original_credit_sections_compared'] == 15,
                    'Approved original credit previews were not verified')
        else:
            require(checked['source_only_shiren_checked'], 'Source-only Shiren coverage was not checked')
        browser[family] = {'passed': True, 'html_sha256': built['html_sha256'],
                           'measurements': len(checked['all_font_budgets']),
                           'starting_candidate_overflows': checked['default_overflows']}
    shiren = read('assets/fonts/shiren-arrival.json')
    reference = read('build/arrival-cards/shiren/shiren-source.json')
    provenance = shiren['font']['source']
    require(provenance['reference_manifest_sha256'] == digest((ROOT/'build/arrival-cards/shiren/shiren-source.json').read_bytes()),
            'Shiren source manifest changed')
    require(provenance['config_sha256'] == digest((ROOT/'config/shiren-arrival-font.json').read_bytes()),
            'Shiren glyph selections changed')
    require(provenance['generator_sha256'] == digest((ROOT/'tools/build_shiren_arrival_font.py').read_bytes()) and
            reference['harness_sha256'] == digest((ROOT/'tools/extract_shiren_arrival_reference.py').read_bytes()),
            'Stale Shiren reconstruction')
    for name, expected in provenance['files'].items():
        require(digest((ROOT/provenance['project']/name).read_bytes()) == expected,
                'External Shiren source changed: '+name)
    source_count = 0
    for char, g in shiren['font']['glyphs'].items():
        if g['origin'] != 'shiren_crop':
            continue
        path = ROOT/g['source_png']
        require(digest(path.read_bytes()) == g['source_png_sha256'], 'Shiren title strip changed')
        selected = Image.open(path).convert('L').crop(g['crop'])
        box = selected.getbbox()
        selected = selected.crop(box)
        actual = [''.join('3' if selected.getpixel((x, y)) else '0'
                          for x in range(selected.width)) for y in range(selected.height)]
        require(g['rows'] == actual and g['top'] == box[1]-19,
                'Recovered Shiren glyph differs from its source crop: '+char)
        source_count += 1
    require(source_count == 43, 'Shiren recovered glyph count changed')
    originals = {name: digest((ROOT/'build'/name).read_bytes())
                 for name in ('torneko-2-english.gba', 'torneko-2-english.bps')}
    report = {'schema': 1, 'passed': True, 'source_rom_sha256': base,
              'credits': {'visible_lines': 67, 'sections': 15,
                          'decision': 'Preserve original English GBA artwork, user 2026-09-30',
                          'development_rom_original_artwork_bytes_verified': credit_end-credit_start,
                          'exact_native_frames': len(credit['exact_frame_matches'])},
              'arrivals': {'locations': len(am['entries']), 'native_cases': len(arrival['cases'])},
              'shiren': {'source_crops_verified': source_count, 'derived_punctuation': '.',
                         'current_arrival_names_covered': shiren['current_arrival_names_covered'],
                         'font_sha256': digest((ROOT/'assets/fonts/shiren-arrival.json').read_bytes())},
              'browser': browser, 'existing_development_outputs': originals,
              'evidence': {name: digest((ROOT/name).read_bytes()) for name in (
                  'build/credits/manifest.json', 'build/credits/research/report.json',
                  'build/arrival-cards/manifest.json', 'build/arrival-cards/native/report.json')},
              'scope': 'Offline graphics comparison/extraction acceptance only. Arrival defaults use approved insertion geometry, including 136px Ordeal Mansion. Native insertion acceptance is separate in build/arrival-cards/inserted/acceptance.json. No natural ending/town or whole-game localization acceptance.'}
    save_json(ROOT/'build/graphics-audition/acceptance.json', report)
    print('Offline graphics comparisons accepted: 67 credit lines, 13 arrivals, both browser studios; native insertion acceptance is separate.')


if __name__ == '__main__':
    run()
