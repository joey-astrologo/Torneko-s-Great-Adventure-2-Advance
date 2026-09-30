"""Validate browser-generated title exports and record source preservation."""
import base64
import io
import json
from pathlib import Path
from PIL import Image
from tools.rom import ROOT, digest, require
from tools.extract_graphics_audition import save_json
from tools.capture_title_audition import OUT, BASELINE


def verify():
    report = json.loads((OUT/'browser-checks.json').read_text())
    require(report['status'] == 'passed', 'Title browser checks failed')
    build = json.loads((OUT/'build.json').read_text())
    require(build['html_sha256'] == digest((OUT/'index.html').read_bytes()), 'Stale title page')
    require(report['settings']['renderer_sha256'] == build['renderer_sha256'], 'Stale browser renderer')
    require(report['settings']['candidate_sha256'] == build['candidate_sha256'], 'Stale artwork')
    require(report['settings']['backgrounds_sha256'] == build['backgrounds_sha256'], 'Stale background artwork')
    files = {}
    expected = [('title-english-native.png',(240,160)), ('title-english-4x.png',(960,640)), ('title-comparison.png',(960,382)),
                ('background-comparison.png',(960,1780)), ('corner-logo-native.png',(76,36))]
    expected += [(f'background-{index}-{context}.png',(240,160)) for index in (13,18,19,20,21) for context in ('art','menu','clean')]
    require(set(report['pngs']) == {name for name,_ in expected}, 'Export set differs')
    for name, size in expected:
        url = report['pngs'][name]
        require(url.startswith('data:image/png;base64,'), 'Not a PNG data URL')
        raw = base64.b64decode(url.split(',',1)[1], validate=True)
        with Image.open(io.BytesIO(raw)) as im:
            require(im.format == 'PNG' and im.size == size, 'Export format or dimensions differ')
        (OUT/name).write_bytes(raw)
        files[name] = digest(raw)
    with Image.open(OUT/'title-english-native.png') as im, Image.open(OUT/'reference/japanese/title.png') as original:
        require(im.convert('RGB').crop((0,136,240,160)).tobytes() == original.convert('RGB').crop((0,136,240,160)).tobytes(), 'Export changed original footer')
        colors = len(set(im.convert('RGB').get_flattened_data()))
    backgrounds = json.loads((OUT/'backgrounds/reference.json').read_text())
    background_checks = []
    logo = Image.open(OUT/'corner-logo-native.png').convert('RGBA')
    require(logo.getextrema()[3][0] == 0 and logo.getextrema()[3][1] >= 240, 'Corner logo lost transparency or lettering')
    logo_pixels = logo.load()
    require(all(logo_pixels[x,y][3] == 0 for x,y in ((0,0),(75,0),(0,35),(75,35))), 'Logo has opaque corners')
    for row in backgrounds['cases']:
        x,y,w,h = row['rectangle_xywh']
        clean = Image.open(OUT/f'background-{row["index"]}-clean.png').convert('RGB').load()
        for context,key in [('art','background'),('menu','menu'),('clean','background')]:
            with Image.open(OUT/f'background-{row["index"]}-{context}.png') as output, Image.open(OUT/row[key]) as source:
                output, source = output.convert('RGB'), source.convert('RGB')
                a,b = output.load(), source.load()
                require(all(a[xx,yy] == b[xx,yy] for yy in range(160) for xx in range(240)
                            if not(x<=xx<x+w and y<=yy<y+h)), 'Background artwork or menu changed outside logo')
                patch = output.crop((x,y,x+w,y+h)).tobytes()
                if context != 'clean':
                    for yy in range(h):
                        for xx in range(w):
                            colour = logo_pixels[xx,yy]
                            if colour[3] == 0:
                                require(a[x+xx,y+yy] == clean[x+xx,y+yy], 'Transparent gap did not reveal restored scene')
                            if colour[3] == 255:
                                require(a[x+xx,y+yy] == colour[:3], 'Opaque shared lettering changed')
                background_checks.append({'index':row['index'],'context':context,'all_pixels_outside_logo_unchanged':True,
                     'composited_corner_rgb_sha256':digest(patch),'distinct_colors':len(set(output.get_flattened_data())),
                     'transparent_logo_reveals_reconstructed_scene':context!='clean'})
    provenance = json.loads((OUT/'reference/provenance.json').read_text())
    # Historical provenance predates insertion; verify those ROM/BPS hashes
    # against the archived reference, never against the newer release.
    protected = {}
    for path, sha in provenance['protected_hashes'].items():
        resolved = BASELINE.with_suffix(Path(path).suffix) if path in ('build/torneko-2-english.gba','build/torneko-2-english.bps') else ROOT/path
        require(digest(resolved.read_bytes()) == sha, 'Source or archived reference changed')
        protected[str(resolved.relative_to(ROOT))] = sha
    save_json(OUT/'default-settings.json',report['settings'])
    del report['pngs']
    report.update(html_sha256=build['html_sha256'], export_hashes=files, default_distinct_colors=colors,
                  native_palette_entries=256, preview_is_concept_palette=True, inserted_native_gallery='../title-insertion/index.html',
                  original_footer_export_verified=True, original_sources_and_archived_reference_unchanged=True, protected_reference_hashes=protected,
                  background_checks=background_checks, background_palette_entries=240,
                  shared_logo_rgba_sha256=digest(logo.tobytes()), corner_reconstruction_scope='Only the 76x36 original logo rectangles',
                  verifier_hashes={p:digest((ROOT/p).read_bytes()) for p in ('tools/verify_title_audition.py','tools/verify_title_audition.m','tools/verify_title_audition.sh','tools/title_audition/read_checks.js')})
    save_json(OUT/'verification.json',report)
    print(f'Title audition: {len(report["checks"])} browser checks passed; footer/export/source checks passed; {colors} preview colours (concept preview; inserted palette verified separately).')


if __name__ == '__main__':
    verify()
