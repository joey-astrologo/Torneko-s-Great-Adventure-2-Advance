"""Build the standalone Torneko 2 title-art audition; no ROM writes."""
import base64
import json
from pathlib import Path
from PIL import Image
from tools.rom import ROOT, load_base, digest, require
from tools.extract_graphics_audition import save_json
from tools.capture_title_audition import OUT, BASELINE

ASSET = ROOT / 'assets/title-screen/wood-gold-v1.png'
PROMPT = ASSET.with_name('wood-gold-v1-prompt.txt')
CONFIG = ASSET.with_name('candidate.json')
TEMPLATE = ROOT / 'tools/title_audition/index.html'
SCRIPT = ROOT / 'tools/title_audition/studio.js'
BG_SCRIPT = SCRIPT.with_name('backgrounds.js')
BG_CONFIG = ROOT / 'assets/title-screen/background-candidate.json'


def uri(path):
    return 'data:image/png;base64,' + base64.b64encode(path.read_bytes()).decode()


def build():
    provenance = json.loads((OUT / 'reference/provenance.json').read_text())
    candidate = json.loads(CONFIG.read_text())
    generation = candidate['generation']
    backgrounds = json.loads((OUT/'backgrounds/reference.json').read_text())
    background_candidate = json.loads(BG_CONFIG.read_text())
    badge = ROOT/background_candidate['asset']
    require(backgrounds['passed'] and backgrounds['baseline_sha256'] == digest(BASELINE.read_bytes()), 'Recapture menu backgrounds')
    require(background_candidate['parent_title_sha256'] == generation['asset_sha256'], 'Corner logo belongs to a different title')
    require(background_candidate['asset_sha256'] == digest(badge.read_bytes()), 'Corner artwork changed')
    require(background_candidate['generation']['prompt_sha256'] == digest((ROOT/background_candidate['generation']['prompt']).read_bytes()), 'Corner prompt changed')
    with Image.open(badge) as im:
        require(list(im.size) == background_candidate['dimensions'] and abs(im.width/im.height-19/9)<0.01, 'Corner logo dimensions changed')
        require(im.mode == 'RGBA' and im.getextrema()[3] == (0,255), 'Floating logo must have real transparency')
    script = SCRIPT.read_text() + '\n' + BG_SCRIPT.read_text()
    require(provenance['passed'] and provenance['source_sha256'] == digest(load_base()), 'Wrong original reference')
    require(provenance['baseline_sha256'] == digest(BASELINE.read_bytes()), 'Recapture current English reference')
    require(generation['asset_sha256'] == digest(ASSET.read_bytes()), 'Candidate artwork changed')
    require(generation['prompt_sha256'] == digest(PROMPT.read_bytes()), 'Candidate prompt changed')
    original = OUT / 'reference/japanese/title.png'
    require(digest(original.read_bytes()) == provenance['cases'][0]['png_sha256'], 'Reference image changed')
    with Image.open(ASSET) as im:
        size = list(im.size)
        require(size == generation['dimensions'] and size[0]*2 == size[1]*3, 'Candidate dimensions differ')
        require(im.convert('RGBA').getextrema()[3] == (255,255), 'Candidate must be opaque')
    data = {'schema': 1, 'source_sha256': provenance['source_sha256'],
            'reference_sha256': digest(original.read_bytes()), 'renderer_sha256': digest(script.encode()),
            'original': uri(original), 'palette': json.loads((OUT/'reference/palette.json').read_text()),
            'prompt_y': candidate['default_preview']['original_prompt_rectangle'][1],
            'candidate': {'id': candidate['id'], 'name': candidate['name'], 'sha256': generation['asset_sha256'],
                          'image': uri(ASSET), 'size': size},
            'backgrounds': {'sha256': digest(BG_CONFIG.read_bytes()+(OUT/'backgrounds/reference.json').read_bytes()),
                            'badge':uri(badge), 'badge_sha256':background_candidate['asset_sha256'], 'cases':[]}}
    for row in backgrounds['cases']:
        placement = background_candidate['placement']
        require(row['rectangle_xywh'] == [placement['x'], placement['family_y'] if row['index']==13 else placement['other_y'], *placement['size']], 'Corner placement differs from native reference audit')
        repair = next(r for r in background_candidate['repairs'] if r['index']==row['index'])
        repair_path = ROOT/repair['asset']
        require(digest(repair_path.read_bytes()) == repair['asset_sha256'], 'Corner repair artwork changed')
        require(digest((ROOT/repair['prompt']).read_bytes()) == repair['prompt_sha256'], 'Corner repair prompt changed')
        require(digest((ROOT/repair['reference']).read_bytes()) == repair['reference_sha256'], 'Corner repair source changed')
        with Image.open(repair_path) as repaired:
            require(list(repaired.size) == repair['dimensions'] and repaired.width*2 == repaired.height*3, 'Corner repair dimensions differ')
            require(repaired.convert('RGBA').getextrema()[3] == (255,255), 'Corner repair must be opaque')
        for key,label in [('background','background'),('menu','menu'),('editor','name')]:
            require(digest((OUT/row[key]).read_bytes()) == row['files_sha256'][label], 'Menu reference image changed')
        raw = (OUT/row['background']).with_name('native.palette').read_bytes()
        require(digest(raw) == row['native_palette_sha256'], 'Menu reference palette changed')
        palette = []
        for at in range(0,480,2):
            value = int.from_bytes(raw[at:at+2],'little')
            palette.append([((value>>shift&31)<<3)|((value>>shift&31)>>2) for shift in (0,5,10)])
        data['backgrounds']['cases'].append({'index':row['index'],'name':row['name'],
            'rectangle':row['rectangle_xywh'],'original':uri(OUT/row['background']),
            'menu':uri(OUT/row['menu']), 'clean':uri(repair_path), 'palette':palette})
    encoded = json.dumps(data, ensure_ascii=False, separators=(',', ':')).replace('<','\\u003c')
    html = TEMPLATE.read_text().replace('__DATA__',encoded).replace('__SCRIPT__',script)
    (OUT/'index.html').write_text(html)
    save_json(OUT/'build.json', {
        'schema': 1, 'source_rom': provenance['source_rom'], 'source_sha256': provenance['source_sha256'],
        'baseline_rom': str(BASELINE.relative_to(ROOT)), 'baseline_sha256': provenance['baseline_sha256'],
        'output_rom': None, 'html_sha256': digest((OUT/'index.html').read_bytes()),
        'reference_sha256': data['reference_sha256'], 'candidate_sha256': generation['asset_sha256'],
        'renderer_sha256': data['renderer_sha256'], 'candidate_dimensions': size, 'generation': generation,
        'status': 'All six approved images inserted; studio retains editable concept previews',
        'backgrounds_sha256':data['backgrounds']['sha256'], 'background_candidate':background_candidate,
        'source_files': {str(p.relative_to(ROOT)):digest(p.read_bytes()) for p in (Path(__file__),TEMPLATE,SCRIPT,BG_SCRIPT,CONFIG,BG_CONFIG)},
        'scope': 'Offline title audition. Native-size canvas reduction and colour previews; original prompt-strip option. No ROM insertion or allocator reservation.'})
    print('Built title audition:', OUT/'index.html')


if __name__ == '__main__':
    build()
