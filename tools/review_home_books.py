"""Assemble a labelled preview from unchanged native emulator captures."""

import json
from PIL import Image, ImageDraw, ImageFont

from tools.rom import ROOT, digest, require


def run():
    output = ROOT / 'build/english'
    report = json.loads((output / 'books-validation/report.json').read_text())
    require(report['passed'] and report['output_rom_sha256'] == digest((output / 'torneko-2-english.gba').read_bytes()),
            'Preview requires current native acceptance')
    cases = [('red-book-000.png','Red book: title and native centring'),
             ('red-book-002.png','Ten tips: measured English pages'),
             ('save-continue-menu.png','Blue book: four original actions'),
             ('save-continue-overwrite.png','Overwrite prompt: saved village name'),
             ('banker-yes-reminder-001.png','Banker: the original 6F clue'),
             ('mansion-floor-one.png','Mansion: normal arrival on floor one')]
    canvas = Image.new('RGB',(1008,1140),'#101a2b')
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf',20)
    draw.text((16,12),'Torneko 2 Advance - home books and mansion entrance',font=font,fill='#eef3fa')
    rows = []
    for index,(name,caption) in enumerate(cases):
        path = output / 'books-validation' / name
        picture = Image.open(path).convert('RGB')
        require(picture.size == (240,160),'Unexpected native screenshot size')
        x,y = 16 + (index % 2)*496, 48 + (index // 2)*362
        draw.text((x,y),caption,font=font,fill='#91d8bd')
        canvas.paste(picture.resize((480,320),Image.Resampling.NEAREST),(x,y+28))
        rows.append({'source':str(path.relative_to(ROOT)),'sha256':digest(path.read_bytes()),'caption':caption})
    canvas.save(output / 'books-preview.png')
    (output / 'books-preview.json').write_text(json.dumps({'output_rom_sha256':report['output_rom_sha256'],
        'native_captures_only':True,'nearest_neighbour_scale':2,'images':rows},indent=2)+'\n')
    print(output / 'books-preview.png')


if __name__ == '__main__':
    run()
