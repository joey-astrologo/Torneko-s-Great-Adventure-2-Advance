"""Present unchanged native mansion captures with labels and provenance."""

import json
from PIL import Image, ImageDraw, ImageFont

from tools.rom import ROOT, digest, require


def run():
    output = ROOT/'build/english'
    report = json.loads((output/'mansion-validation/report.json').read_text())
    require(report['passed'] and report['output_rom_sha256'] == digest((output/'torneko-2-english.gba').read_bytes()),
            'Preview requires current native acceptance')
    cases = [('floor-six-voice-006.png','6F: the anonymous voice'),
             ('imp-introduction-002.png','Imp: challenge before native combat'),
             ('name-probes/required-English.png','Controlled name display: Torneko'),
             ('banker-thanks-002.png','Return: the recovered safe'),
             ('family-question-003.png','Family: original Yes/No question'),
             ('family-1-1/old-man-question-004.png','The old man and the Joy Chest'),
             ('family-1-1/bank-permission-002.png','Next morning: the blacksmith'),
             ('family-1-1/bank-opening-003.png','Bank opening: Tipper\'s joke'),
             ('family-1-1/morning-controls.png','Town movement resumes')]
    canvas = Image.new('RGB',(1504,1138),'#101a2b')
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf',20)
    draw.text((16,12),'Torneko 2 Advance - mansion safe recovery and bank opening',font=font,fill='#eef3fa')
    images = []
    for i,(name,caption) in enumerate(cases):
        path = output/'mansion-validation'/name
        picture = Image.open(path).convert('RGB')
        require(picture.size == (240,160),'Unexpected native image size')
        x,y = 16+(i%3)*496,48+(i//3)*362
        draw.text((x,y),caption,font=font,fill='#91d8bd')
        canvas.paste(picture.resize((480,320),Image.Resampling.NEAREST),(x,y+28))
        images.append({'source':str(path.relative_to(ROOT)),'sha256':digest(path.read_bytes()),'caption':caption})
    canvas.save(output/'mansion-preview.png')
    (output/'mansion-preview.json').write_text(json.dumps({'output_rom_sha256':report['output_rom_sha256'],
        'native_captures_only':True,'nearest_neighbour_scale':2,'images':images},indent=2)+'\n')
    print(output/'mansion-preview.png')


if __name__ == '__main__':
    run()
