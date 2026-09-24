"""Town inventory labels, confirmations and controlled native outcomes."""
import argparse,html,json
from tools.rom import ROOT,digest,require

def run(cumulative=False):
    out=ROOT/('build/english/town-action-validation' if cumulative else 'build/town-actions-prototype')
    ledger=ROOT/'build/english/build.json' if cumulative else out/'build.json'
    build=json.loads(ledger.read_text());report=json.loads((out/'report.json').read_text())
    require(report['passed'] and report['rom_sha256']==build['output_sha256'] and len(report['cases'])==10,
            'Town action gallery evidence differs')
    e=html.escape;cards=[];images={}
    budgets=''.join(f'<tr><td>{e(r["english"])}</td><td>{r["advance"]} / {r.get("budget",216)}px</td></tr>'
                    for r in build['town_actions']['labels']+build['town_actions']['entries'])
    for case in report['cases']:
        pictures=[]
        for path in sorted((out/case['case']).glob('*.png')):
            relative=str(path.relative_to(out));images[relative]=digest(path.read_bytes())
            pictures.append(f'<img width="480" height="320" loading="lazy" src="{e(relative)}" alt="{e(relative)}">')
        cards.append('<details><summary>'+e(case['case'])+'</summary>'+''.join(pictures)+'</details>')
    page='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Torneko 2 town item actions</title><style>body{background:#171923;color:#eee;font:16px system-ui;margin:24px}
details{background:#242838;padding:16px;margin:12px 0}img{image-rendering:pixelated;max-width:100%;height:auto;margin:8px}
td{padding:4px 16px}code{overflow-wrap:anywhere}a{color:#bce}</style><h1>Town item actions</h1><p>'''+e(report['scope'])+'''</p>
<p>ROM <code>'''+report['rom_sha256']+'''</code> · <a href="report.json">Results and input schedules</a></p><table>'''+budgets+'</table>'+''.join(cards)+'</html>\n'
    (out/'index.html').write_text(page);(out/'preview.json').write_text(json.dumps({'rom_sha256':report['rom_sha256'],'cases':10,'images':images},indent=2)+'\n')
    print(out/'index.html')

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--cumulative',action='store_true');run(parser.parse_args().cumulative)
