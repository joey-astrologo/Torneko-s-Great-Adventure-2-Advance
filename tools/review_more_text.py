"""Native galleries for the pending additional text-consumer prototypes."""
import argparse,html,json
from tools.rom import ROOT,digest,require

def run(family,cumulative=False):
    require(family in ('story-command','player-condition','inventory-action','pickup'),'Unknown prototype gallery')
    out=ROOT/(f'build/english/{family}-validation' if cumulative else f'build/{family}-prototype')
    build=json.loads((ROOT/'build/english/build.json' if cumulative else out/'build.json').read_text())
    report=json.loads((out/'report.json').read_text())
    count={'inventory-action':44,'pickup':36}.get(family,45)
    require(report['passed'] and report['rom_sha256']==build['output_sha256'] and len(report['cases'])==count,
            'Prototype gallery evidence stale/incomplete')
    key={'story-command':'story_commands','player-condition':'player_conditions','inventory-action':'inventory_actions','pickup':'pickup'}[family]
    rows={r['id']:r for r in build[key]['entries']};e=html.escape;cards=[];images={}
    for case in report['cases']:
        ids=[case['id']] if family=='story-command' else [r['id'] for r in case['formats']]
        text=''.join('<p>'+e(rows[ident]['english']).replace('\n','<br>')+'</p>' for ident in ids)
        paths=list(case['images']) if family=='story-command' else ['result.png' if family in ('inventory-action','pickup') else 'condition.png'];pictures=[]
        for relative in paths:
            path=case['case']+'/'+relative;sha=digest((out/path).read_bytes());images[path]=sha
            if 'images' in case:require(sha==case['images'][relative],'Prototype screenshot changed')
            pictures.append(f'<img loading="lazy" width="480" height="320" src="{e(path)}" alt="{e(case["case"])} {e(relative)}">')
        cards.append('<details><summary>'+e(case['case'])+'</summary>'+text+''.join(pictures)+'</details>')
    page='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Torneko 2 native text review</title><style>body{background:#171923;color:#eee;font:16px system-ui;margin:24px}
details{background:#242838;padding:16px;margin:12px 0}img{image-rendering:pixelated;max-width:100%;height:auto;margin:8px}
code{overflow-wrap:anywhere}a{color:#bce}</style><h1>Torneko 2: '''+e(family)+'''</h1><p>'''+('Cumulative candidate. ' if cumulative else 'Separate prototype. ')+e(report['scope'])+'''</p>
<p>ROM <code>'''+report['rom_sha256']+'''</code> · <a href="report.json">Results and input schedules</a></p>'''+''.join(cards)+'</html>\n'
    (out/'index.html').write_text(page)
    (out/'preview.json').write_text(json.dumps({'rom_sha256':report['rom_sha256'],'cases':count,'images':images},indent=2)+'\n')
    print(out/'index.html')

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('family',choices=['story-command','player-condition','inventory-action','pickup'])
    parser.add_argument('--cumulative',action='store_true');args=parser.parse_args()
    run(args.family,args.cumulative)
