"""Package standalone credits and arrival studios from pinned T2 bitmap exports."""
import base64
import io
import json

from tools.compact_font import load_font
from tools.extract_graphics_audition import credits, arrivals, save_json
from tools.review_fonts import extract, code_for
from tools.rom import ROOT, load_base, digest
from tools.arrival_art import artwork


def data_url(image):
    output = io.BytesIO()
    image.save(output, format='PNG')
    return 'data:image/png;base64,'+base64.b64encode(output.getvalue()).decode()


def fonts(rom):
    imported = json.loads((ROOT/'assets/fonts/graphics-comparison.json').read_text())
    compact = load_font()
    faces = []
    for ident, name in [('t2-compact', 'Torneko 2 compact English'), ('t2-serif', 'Torneko 2 native serif Latin')]:
        glyphs = {}
        for c, g in compact['glyphs'].items():
            if ident == 't2-serif' and c.isascii() and c.isalnum():
                native = extract(rom, code_for(c))
                rows = [''.join('3' if p else '0' for p in row) for row in native['pixels']]
                advance = native['width']
            else:
                rows = [row.replace('.', '0').replace('#', '3') for row in g['rows']]
                advance = g['advance']
            glyphs[c] = {'rows': rows, 'width': len(rows[0]), 'height': len(rows),
                         'top': -13, 'advance': advance,
                         'origin': 'T2 native serif' if ident == 't2-serif' and c.isalnum() else 'T2 compact English'}
        h = [y for y, row in enumerate(glyphs['H']['rows']) if '3' in row]
        faces.append({'id': ident, 'name': name, 'glyphs': glyphs, 'cap_height': max(h)-min(h)+1,
                      'scope': 'T2 bitmap comparison; uniformly scaled only in this graphics audition.'})
    shiren = json.loads((ROOT/'assets/fonts/shiren-arrival.json').read_text())['font']
    return faces+[shiren]+imported['faces']


def build():
    rom = load_base()
    cm, roll = credits(rom)
    am, atlas, cards, floor = arrivals(rom)
    _, _, approved = artwork(rom)
    for entry, selected in zip(am['entries'], approved, strict=True):
        entry['original_text_region'] = entry['text_region']
        entry['text_region'] = selected['text_region']
    faces = fonts(rom)
    font_hash = digest(json.dumps(faces, sort_keys=True, separators=(',', ':')).encode())
    template = ROOT/'tools/graphics_audition/index.html'
    script = ROOT/'tools/graphics_audition/studio.js'
    common = {'schema': 1, 'source_sha256': digest(rom), 'font_sha256': font_hash,
              'renderer_sha256': digest(script.read_bytes()), 'fonts': faces,
              'credits': cm, 'arrivals': am,
              'images': {'roll': data_url(roll), **{k: data_url(v) for k, v in cards.items()},
                         **{'glyph-'+k: data_url(v) for k, v in floor.items()}}}
    outputs = []
    for mode, path in [('credits', ROOT/'build/credits/audition'),
                       ('arrivals', ROOT/'build/arrival-cards/audition')]:
        data = common | {'mode': mode}
        encoded = json.dumps(data, ensure_ascii=False, separators=(',', ':')).replace('<', '\\u003c')
        page = template.read_text().replace('__DATA__', encoded).replace('__SCRIPT__', script.read_text())
        path.mkdir(parents=True, exist_ok=True)
        (path/'index.html').write_text(page)
        save_json(path/'build.json', {'schema': 1, 'source_rom_sha256': digest(rom), 'output_rom': None,
                                     'html_sha256': digest(page.encode()), 'font_sha256': font_hash,
                                     'inputs': {str(p.relative_to(ROOT)): digest(p.read_bytes()) for p in
                                                (template, script, ROOT/'config/credits-audition.json',
                                                 ROOT/'assets/fonts/graphics-comparison.json',
                                                 ROOT/'assets/fonts/shiren-arrival.json',
                                                 ROOT/'config/shiren-arrival-font.json',
                                                 ROOT/'tools/build_shiren_arrival_font.py',
                                                 ROOT/'tools/extract_shiren_arrival_reference.py',
                                                 ROOT/'config/arrival-art.json',
                                                 ROOT/'tools/arrival_art.py',
                                                 ROOT/'assets/fonts/compact-english.json',
                                                 ROOT/'tools/extract_graphics_audition.py',
                                                 ROOT/'translations/save-preview-review.json',
                                                 ROOT/'tools/review_fonts.py',
                                                 ROOT/'tools/compact_font.py',
                                                 ROOT/'tools/build_graphics_audition.py')},
                                     'mode': mode, 'credits_decision': 'Preserve original English GBA artwork (user, 2026-09-30).',
                                     'scope': 'Offline bitmap-font/layout comparison. Credits default to the approved original; arrival defaults reproduce the approved Shiren insertion geometry. Native inserted-artwork evidence is separate in build/arrival-cards/inserted. Saved settings and metrics are source/font/renderer pinned.'})
        outputs.append(path/'index.html')
    index = ROOT/'build/graphics-audition/index.html'
    index.parent.mkdir(parents=True, exist_ok=True)
    index.write_text('''<!doctype html><html lang="en"><meta charset="utf-8"><title>Torneko 2 graphics auditions</title>
<style>body{font:18px/1.6 system-ui;max-width:760px;margin:70px auto;background:#111923;color:#e6eef4;padding:24px}a{color:#8fdbca}li{margin:24px 0}</style>
<h1>Torneko 2 graphics auditions</h1><p>Original GBA artwork and English typography comparisons. The approved Shiren arrival lettering is now inserted.</p>
<ul><li><a href="../credits/audition/index.html">Ending credits viewer</a> — original English GBA artwork approved unchanged; 67 lines in 15 sections.</li>
<li><a href="../arrival-cards/audition/index.html">Arrival and dungeon card studio</a> — 13 location rectangles, floor numbers and Well levels.</li>
<li><a href="../arrival-cards/inserted/index.html">Inserted arrival cards in mGBA</a> — all 13 cards; 30 native validation cases.</li>
<li><a href="../arrival-cards/shiren/index.html">Shiren lettering source and alphabet</a> — 28 title strips; 43 recovered glyphs and a derived period.</li></ul>
<p><a href="../../docs/GRAPHICS_AUDITION.md">Discovery, reproduction and verification notes</a></p></html>''')
    print('\n'.join(str(p.relative_to(ROOT)) for p in outputs))


if __name__ == '__main__':
    build()
