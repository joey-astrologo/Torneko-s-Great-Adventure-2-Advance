"""Native original/English and previous/corrected menu galleries."""
import html,json
from PIL import Image,ImageDraw
from tools.rom import ROOT,digest,require

PAIRS=[('Dungeon commands','dungeon-root'),('Food actions','inventory-food'),
       ('Arrow actions','inventory-arrows'),('Equipped item actions','inventory-equipped'),
       ('Ground item actions','ground-arrows')]

def run():
    out=ROOT/'build/menu-resize';ledger=json.loads((ROOT/'build/english/build.json').read_text())
    report=json.loads((ROOT/'build/english/menu-validation/report.json').read_text())
    require(report['passed'] and report['rom_sha256']==ledger['output_sha256'],'Menu preview source is stale')
    require(len(report['border_checks'])==11 and all(c['gap_px']==8 for c in report['border_checks']),
            'Separate borders need native verification')
    images=[]
    def gallery(previous=False):
        sheet=Image.new('RGB',(500,len(PAIRS)*190),(18,25,42));draw=ImageDraw.Draw(sheet);blocks=[]
        for i,(title,case) in enumerate(PAIRS):
            draw.text((8,i*190+4),title+(' (previous)' if previous else ' (Japanese)'),fill='white')
            draw.text((258,i*190+4),'Corrected English',fill='white');cards=[]
            left=out/f'previous-wide/{case}.png' if previous else ROOT/f'build/menu-layout-audit/native/{case}/menu.png'
            for j,(label,path) in enumerate([('Previous wide layout' if previous else 'Original Japanese',left),
                    ('Corrected English',ROOT/f'build/english/menu-validation/{case}/menu.png')]):
                picture=Image.open(path).convert('RGB');sheet.paste(picture,(5+j*250,i*190+24))
                rel=str(path.relative_to(ROOT));images.append({'source':rel,'sha256':digest(path.read_bytes())})
                cards.append(f'<figure><figcaption>{label}</figcaption><img src="../../{html.escape(rel)}"></figure>')
            blocks.append('<h2>'+title+'</h2><div class="pair">'+''.join(cards)+'</div>')
        sheet.resize((1000,len(PAIRS)*380),Image.Resampling.NEAREST).save(out/('correction.png' if previous else 'menus.png'))
        return ''.join(blocks)
    original=gallery();previous=gallery(True) if (out/'previous-wide/report.json').exists() else ''
    (out/'index.html').write_text('''<!doctype html><meta charset="utf-8"><title>Torneko 2 menus</title><style>body{background:#12192a;color:white;font:17px system-ui;max-width:1100px;margin:30px auto}.pair{display:flex;flex-wrap:wrap}img{width:480px;image-rendering:pixelated}figure{margin:10px}a{color:#9de6d0}summary{cursor:pointer}</style><h1>Torneko 2 font: corrected native menus</h1><p>Swap, Info, Floor, Option, Remove and Take fit the original 40-pixel windows. Main commands have 34 usable pixels; item/ground actions have 36. Original window positions restore 8-pixel gaps between borders. The dungeon-name and inventory windows retain their original sizes. These captures use ordinary inputs; Japanese and English routes can have different item quantities.</p><p><a href="../typography/index.html">New: Weapon, number font and item spacing corrections</a> · <a href="../services/index.html">Dungeon UI, banking, items and storage</a></p><p><a href="correction.png">Previous wide layout / corrected English contact sheet</a> · <a href="../font-audition/index.html">Interactive font and budget comparison</a> · <a href="../../docs/MENU_LAYOUTS.md">Validation and remaining coverage</a></p>'''+
        ('<details open><summary>Previous wide layout versus corrected English</summary>'+previous+'</details>' if previous else '')+
        '<details><summary>Original Japanese versus corrected English</summary>'+original+'</details>'+'''<h2>Controlled stress cases</h2><p>These use explicitly synthetic inventory/menu state, separate from natural gameplay acceptance.</p><div class="pair"><figure><figcaption>Twenty-item inventory, third page</figcaption><img src="../english/menu-edge-validation/full-inventory/menu.png"></figure><figure><figcaption>Seven disabled rows (Remove)</figcaption><img src="../english/menu-edge-validation/seven-disabled/menu.png"></figure></div>''')
    (out/'preview.json').write_text(json.dumps({'rom_sha256':ledger['output_sha256'],'border_checks':report['border_checks'],'images':images},indent=2)+'\n')
    print(out/'index.html')
if __name__=='__main__':run()
