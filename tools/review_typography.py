"""Native before/after evidence for the user's typography corrections."""
import html,json
from tools.rom import ROOT,digest,require

def run():
 out=ROOT/'build/typography';build=json.loads((ROOT/'build/english/build.json').read_text());images=[];blocks=[]
 for name in ['items','bank','dungeon-ui']:
  report=json.loads((ROOT/f'build/english/{name}-validation/report.json').read_text())
  require(report['passed'] and report['rom_sha256']==build['output_sha256'],'Stale typography evidence: '+name)
 pairs=[('status','Weapon label and status values','dungeon-ui-validation/controls/status.png'),
        ('items','Normal item spacing and quantities','items-validation/natural-0/inventory.png'),
        ('enhancement','Enhancement digits (controlled +99 case)','items-validation/30-maximum-fields/inventory.png'),
        ('price','Price column (controlled priced item)','items-validation/30-priced/inventory.png'),
        ('bank','Bank balances','bank-validation/roundtrip/menu.png'),
        ('amount','Bank amount editor','bank-validation/roundtrip/amount-or-empty.png')]
 for ident,title,after in pairs:
  paths=[out/f'before/{ident}.png',ROOT/'build/english'/after];cards=[]
  for label,path in zip(['Before','Corrected'],paths):
   rel=str(path.relative_to(ROOT));images.append({'source':rel,'sha256':digest(path.read_bytes())})
   cards.append(f'<figure><figcaption>{label}</figcaption><img width="480" height="320" src="../../{html.escape(rel)}" alt="{html.escape(title+": "+label)}"></figure>')
  blocks.append('<h2>'+html.escape(title)+'</h2><div class="pair">'+''.join(cards)+'</div>')
 (out/'index.html').write_text('''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Torneko 2 typography corrections</title><style>body{background:#12192a;color:white;font:17px/1.5 system-ui;max-width:1050px;margin:30px auto;padding:0 16px}.pair{display:flex;flex-wrap:wrap}figure{margin:8px}img{image-rendering:pixelated;max-width:100%;height:auto}a{color:#9de6d0}</style><h1>Weapon, matching numbers and normal item spacing</h1><p>Actual native mGBA captures. The matching digits already exist in Torneko 2's compact font. Native decimal and item digit families now use those shapes; inverse price styling now has a continuous background between digits. Word spaces, including both sides of x, are reduced from six to three pixels. Bank colons are attached to their labels. English item rows no longer trigger Japanese byte-length compression. Original window sizes and bank editor cursor cells are preserved.</p><p>The bank editor uses 12-pixel selection cells containing smaller, centered glyphs. Ordinary balances and item quantities use six-pixel digit advances. Item quantities and enhancement values are checked against their native inventory records. Untranslated names still use the original Japanese spacing rules.</p><p><a href="../menu-resize/index.html">Menu gallery</a> · <a href="../../docs/TYPOGRAPHY.md">Implementation and validation scope</a></p>'''+''.join(blocks)+'</html>')
 (out/'report.json').write_text(json.dumps({'passed':True,'rom_sha256':build['output_sha256'],'images':images},indent=2)+'\n')
 print(out/'index.html')
if __name__=='__main__':run()
