"""Decode the user-nominated Shiren area-title bitmaps into a reference sheet."""
import re

from PIL import Image, ImageDraw

from PIL import ImageFont

from tools.rom import ROOT, digest, require as check
from tools.extract_graphics_audition import save_json


def label_font(size):
    return ImageFont.load_default(size=size)

SOURCE = ROOT.parent / 'Shiren/shiren-revamp-fixes'
DESTINATION = ROOT / 'build/arrival-cards/shiren'


def export():
    bitmap = SOURCE / 'gfx/fonts/area_title_font.2bpp'
    pointer_source = SOURCE / 'data/demos/demos.asm'
    title_source = SOURCE / 'code/bank_05.asm'
    import json
    config = json.loads((ROOT/'config/shiren-arrival-font.json').read_text())
    for path, expected in config['source_files'].items():
        check(digest((SOURCE/path).read_bytes()) == expected, 'Shiren reference source changed: '+path)
    data = bitmap.read_bytes()
    check(len(data) == 0x9000, 'Review changed Shiren bitmap asset size')
    section = pointer_source.read_text().split('Data_db6000:', 1)[1].split('.org $6200', 1)[0]
    pointers = [int(n, 16) for n in re.findall(r'\.dw\s+\$([0-9A-Fa-f]+)', section)]
    check(len(pointers) == 194, 'Review changed title-chunk pointer table')
    section = title_source.read_text().split('UNREACH_C5CDCE:', 1)[1].split('UNREACH_C5CEFA:', 1)[0]
    records, pending, label = [], [], None
    for line in section.splitlines():
        if '.db' not in line:
            continue
        pending += [int(n, 16) for n in re.findall(r'\$([0-9A-Fa-f]+)', line.split(';')[0])]
        if ';"' in line:
            label = line.split(';"', 1)[1].split('"')[0]
        if len(pending) == 10:
            records.append((pending, label))
            pending, label = [], None
        check(len(pending) < 10, 'Unexpected title record boundary')
    check(len(records) == 30 and not pending, 'Review changed area-title records')
    DESTINATION.mkdir(parents=True, exist_ok=True)
    sheet = Image.new('RGB', (1080, 60+14*94), '#20232a')
    draw = ImageDraw.Draw(sheet)
    font = label_font(13)
    draw.text((12, 10), 'Shiren revamp: decoded English area-title bitmaps (2x)', font=font, fill='white')
    draw.text((12, 30), 'Existing source pixels; no new lettering or ROM edits', font=font, fill='#b7c1cf')
    rows = []
    for row, (record, label) in enumerate(records):
        if label is None:
            check(all(n >= 0xF0 for n in record[1:]), 'Unexpected unlabelled title artwork')
            continue
        strip = Image.new('RGB', (256, 24))
        x, spans = 0, []
        for index in record[1:]:
            if index >= 0xF0:
                x += (256-index)*8
                continue
            # Each pointer addresses nine sequential SNES 2bpp tiles (24x24).
            start = pointers[index]-0x7000
            check(0 <= start <= len(data)-144 and x+24 <= strip.width, 'Chunk leaves source or strip')
            spans.append({'chunk_id': index, 'start': hex(start), 'end_exclusive': hex(start+144)})
            for tile in range(9):
                for y in range(8):
                    off = start+tile*16+y*2
                    for px in range(8):
                        value = ((data[off] >> (7-px)) & 1) | (((data[off+1] >> (7-px)) & 1) << 1)
                        check(value in (0, 1), 'Review changed source palette indexes')
                        if value:
                            strip.putpixel((x+(tile%3)*8+px, tile//3*8+y), (255, 255, 255))
            x += 24
        filename = DESTINATION / f'shiren-title-{row:02d}.png'
        strip.save(filename)
        i = len(rows)
        px, py = 12+i%2*540, 60+i//2*94
        sheet.paste(strip.resize((512, 48), Image.Resampling.NEAREST), (px, py))
        draw.text((px, py+54), f'{row:02d} {label}', font=font, fill='#b7c1cf')
        rows.append({'row': row, 'source_comment_label': label,
                     'original_start_column': record[0], 'chunk_ids': record[1:],
                     'bitmap_file_spans': spans, 'ink_bbox': strip.getbbox(),
                     'png': str(filename.relative_to(ROOT)), 'png_sha256': digest(filename.read_bytes())})
    check(len(rows) == 28, 'Review changed visible-title count')
    sheet.save(DESTINATION / 'shiren-area-titles.png')
    save_json(DESTINATION / 'shiren-source.json', {
        'source_project': '../Shiren/shiren-revamp-fixes',
        'source_files': [{'path': str(p.relative_to(SOURCE)), 'bytes': p.stat().st_size,
                          'sha256': digest(p.read_bytes())} for p in (bitmap, pointer_source, title_source)],
        'source_rom': None, 'output_rom': None,
        'address_space': 'External Shiren source-file offsets; not Torneko ROM addresses or allocations',
        'bitmap_envelope': {'start': '0x0', 'end_exclusive': '0x9000'},
        'harness_sha256': digest((ROOT / 'tools/extract_shiren_arrival_reference.py').read_bytes()),
        'font_identity': 'Unknown; no Papyrus attribution or reusable outline-font source found in this checkout',
        'scope': 'Decode of 28 existing English title strips from 30 records. Source pixels are unchanged, displayed white on black. Strips are left aligned for comparison, without original screen positioning or floor digits. No emulator proof, new alphabet, English audition or ROM patch.',
        'entries': rows,
    })
    return rows



if __name__ == '__main__':
    export()
