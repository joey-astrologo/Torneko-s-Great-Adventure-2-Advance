"""Recover a source-only arrival face from the nominated Shiren title graphics.

No outline font or unrelated substitute is used. This is a title-use subset,
not a claim that the artwork contains a complete Latin alphabet or digits.
"""
import json
import string

from PIL import Image, ImageDraw

from tools.extract_graphics_audition import ARRIVALS, save_json
from tools.extract_shiren_arrival_reference import DESTINATION, export, label_font
from tools.rom import ROOT, digest, require

OUTPUT = ROOT/'assets/fonts/shiren-arrival.json'


def crop_glyph(image, baseline):
    bounds = image.getbbox()
    require(bounds is not None, 'Empty source glyph')
    image = image.crop(bounds)
    return {'width': image.width, 'height': image.height,
            'top': bounds[1]-baseline, 'advance': image.width+1,
            'rows': [''.join('3' if image.getpixel((x, y)) else '0'
                             for x in range(image.width)) for y in range(image.height)]}


def proof(font):
    chars = string.ascii_uppercase+string.ascii_lowercase+string.digits+"'-."
    sheet = Image.new('RGB', (1000, 100+((len(chars)+9)//10)*108), '#20232a')
    draw = ImageDraw.Draw(sheet)
    small = label_font(13)
    draw.text((16, 12), 'Shiren source lettering | 3x pixels, shared baseline', font=small, fill='white')
    draw.text((16, 36), 'White: exact source crop. Amber: derived period. Grey: absent, not substituted.', font=small, fill='#bcc8d4')
    draw.text((16, 60), 'All 13 current T2 location names + Level are covered. Retain original T2 floor digits.', font=small, fill='#bcc8d4')
    for i, ch in enumerate(chars):
        x, y = 16+(i % 10)*100, 100+(i//10)*108
        g = font['glyphs'].get(ch)
        colour = '#ffffff' if g and g['origin'] == 'shiren_crop' else '#f2b862' if g else '#7f8b9b'
        draw.line((x, y+58, x+70, y+58), fill='#344152')
        if g:
            for yy, row in enumerate(g['rows']):
                for xx, pixel in enumerate(row):
                    if pixel == '3':
                        px, py = x+xx*3, y+58+(g['top']+yy)*3
                        draw.rectangle((px, py, px+2, py+2), fill=colour)
        else:
            draw.text((x, y+20), 'absent', font=small, fill=colour)
        draw.text((x, y+82), ch+('  source' if g and g['origin'] == 'shiren_crop' else '  derived' if g else ''), font=small, fill=colour)
    sheet.save(DESTINATION/'alphabet.png')


def build():
    entries = export()
    config_path = ROOT/'config/shiren-arrival-font.json'
    config = json.loads(config_path.read_text())
    by_row = {e['row']: e for e in entries}
    glyphs = {' ': {'width': 0, 'height': 0, 'top': 0,
                    'advance': config['space_advance'], 'rows': [], 'origin': 'spacing'}}
    for char, selection in sorted(config['crops'].items()):
        entry = by_row[selection['row']]
        source = ROOT/entry['png']
        require(digest(source.read_bytes()) == entry['png_sha256'], 'Source strip changed')
        require(char in entry['source_comment_label'], 'Selected character absent from source label')
        box = selection['crop']
        require(0 <= box[0] < box[2] <= 256 and box[1] == 0 and box[3] == 24,
                'Glyph boundary outside the title strip')
        g = crop_glyph(Image.open(source).convert('L').crop(box), config['title_baseline'])
        glyphs[char] = g | {'origin': 'shiren_crop', 'source_row': entry['row'],
                            'crop': box, 'source_png': entry['png'],
                            'source_png_sha256': entry['png_sha256']}
    source_chars = set(''.join(e['source_comment_label'] for e in entries))-{' '}
    require(set(config['crops']) == source_chars and len(source_chars) == 43,
            'Source character coverage differs')
    # Preserve the three-row dot above i and move it to the writing baseline.
    dot = glyphs['i']['rows'][:3]
    require(dot == ['00300', '33333', '33333'] and
            glyphs['i']['rows'][3:6] == ['00000']*3, 'Recheck the isolated i dot')
    glyphs['.'] = {'width': 5, 'height': 3, 'top': -2, 'advance': 6, 'rows': dot,
                   'origin': 'shiren_derived_supplement', 'derived_from': 'i',
                   'operation': 'Isolate rows [0,3) of the recovered i and move the dot to baseline; no pixel reshaping.',
                   'review_status': 'New punctuation draft, not an original Shiren period'}
    needed = set(''.join(english for _, english in ARRIVALS)+'Level')
    require(not needed-set(glyphs), 'Current T2 arrival names need missing characters')
    manifest_path = DESTINATION/'shiren-source.json'
    font = {'id': 'shiren-source', 'name': 'Shiren source pixels + derived period',
            'cap_height': config['cap_height'], 'glyphs': glyphs,
            'source': {'project': config['source_project'], 'files': config['source_files'],
                       'config_sha256': digest(config_path.read_bytes()),
                       'reference_manifest_sha256': digest(manifest_path.read_bytes()),
                       'generator_sha256': digest((ROOT/'tools/build_shiren_arrival_font.py').read_bytes())},
            'scope': '43 exact Shiren title glyphs, a period made from its i dot, and new spacing. Covers every current T2 location name and Level. Incomplete alphabet; no substitute font. Use original T2 floor digits. Audition only.'}
    report = {'schema': 1, 'source_rom': None, 'output_rom': None,
              'recovered_characters': ''.join(sorted(source_chars)), 'derived_characters': '.',
              'missing_latin_letters': ''.join(c for c in string.ascii_uppercase+string.ascii_lowercase if c not in glyphs),
              'missing_digits': string.digits, 'current_arrival_names_covered': 13,
              'typeface_identity': 'Unknown; reconstructed bitmap subset, not an identified outline font.',
              'font': font}
    save_json(OUTPUT, report)
    proof(font)
    (DESTINATION/'index.html').write_text('''<!doctype html><html lang="en"><meta charset="utf-8">
<title>Torneko 2 · Shiren source lettering</title><style>body{font:17px/1.6 system-ui;background:#171e28;color:#e7edf5;max-width:1120px;margin:40px auto;padding:20px}a{color:#91decb}img{max-width:100%;image-rendering:pixelated}</style>
<h1>Shiren source lettering</h1><p>Recovered directly from ../Shiren/shiren-revamp-fixes/gfx/fonts/area_title_font.2bpp.
The asset holds assembled words, not a complete alphabet or an outline font.</p>
<p>43 exact glyph crops and one derived period cover all 13 current Torneko 2 arrival names and Level.
The period reuses the dot above i. Spacing is newly assigned. Missing letters and digits are shown explicitly;
there is no automatic fallback. The card studio retains T2's original floor numbers by default.</p>
<p><a href="../audition/index.html">Try the Shiren source candidate on Torneko 2 cards</a> ·
<a href="../../../docs/SHIREN_ARRIVAL_FONT.md">Provenance and limits</a></p>
<h2>Recovered character set</h2><img src="alphabet.png" alt="Recovered source glyphs, derived period and missing characters">
<h2>Original Shiren title strips</h2><p>Left aligned, white on black, 2× source pixels. Original names remain intact.</p>
<img src="shiren-area-titles.png" alt="All 28 original Shiren English area-title strips"></html>''')
    print('Shiren source font: 43 recovered glyphs, derived period, 13/13 T2 names covered.')


if __name__ == '__main__':
    build()
