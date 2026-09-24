"""Native menu screenshots with per-label width and producer evidence."""
import argparse,html,json
from tools.rom import ROOT,digest,require

def run(child=False,cumulative=False):
    out=ROOT/('build/child-actions-prototype' if child else 'build/additional-actions-prototype')
    if cumulative:out=ROOT/('build/english/child-action-validation' if child else 'build/english/additional-action-validation')
    build=json.loads((out/'build.json').read_text());report=json.loads((out/'report.json').read_text())
    require(report['passed'] and report['rom_sha256']==build['output_sha256'] and len(report['cases'])==12,
            'Action label gallery evidence differs')
    rows={int(r['id'].split('.')[1]):r for r in build['menus']['entries'] if r['id'].startswith('action.')}
    e=html.escape;cards=[];images={}
    for case in report['cases']:
        budgets=''.join(f'<tr><td>{i&127}</td><td>{e(rows[i&127]["english"])}</td><td>{rows[i&127]["advance"]} / 36px</td></tr>' for i in case['ids'])
        pictures=[]
        for name in ('open-0.png','restored.png'):
            relative=case['case']+'/'+name;images[relative]=digest((out/relative).read_bytes())
            pictures.append(f'<img width="480" height="320" loading="lazy" src="{e(relative)}" alt="{e(case["case"])} {name}">')
        cards.append('<details><summary>'+e(case['case'])+'</summary><table>'+budgets+'</table>'+''.join(pictures)+'</details>')
    title='Contained-item actions' if child else 'Additional item actions'
    page='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Torneko 2 action labels</title><style>body{background:#171923;color:#eee;font:16px system-ui;margin:24px}
details{background:#242838;padding:16px;margin:12px 0}img{image-rendering:pixelated;max-width:100%;height:auto;margin:8px}
td{padding:4px 16px}code{overflow-wrap:anywhere}a{color:#bce}</style><h1>'''+title+'</h1><p>'+e(report['scope'])+'''</p>
<p>Native validation. ROM <code>'''+report['rom_sha256']+'''</code> · <a href="report.json">Results and input schedules</a></p>'''+''.join(cards)+'</html>\n'
    (out/'index.html').write_text(page);(out/'preview.json').write_text(json.dumps({'rom_sha256':report['rom_sha256'],'cases':12,'images':images},indent=2)+'\n')
    print(out/'index.html')

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--child',action='store_true');parser.add_argument('--cumulative',action='store_true');args=parser.parse_args();run(args.child,args.cumulative)
