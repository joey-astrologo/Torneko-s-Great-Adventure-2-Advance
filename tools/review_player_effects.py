"""Native single-line player-effect comparison gallery."""
import argparse,html,json
from tools.rom import ROOT,digest,require

def run(cumulative=False):
    out=ROOT/('build/english/player-effect-validation' if cumulative else 'build/player-effect-prototype')
    build=json.loads((ROOT/'build/english/build.json' if cumulative else out/'build.json').read_text());report=json.loads((out/'report.json').read_text())
    require(report['passed'] and report['rom_sha256']==build['output_sha256'],'Effect evidence stale')
    rows={r['id']:r for r in build['player_effects']['entries']};cards=[];images={};e=html.escape
    require(len(report['cases'])==39 and {r['id'] for r in report['cases']}==set(rows),'Effect coverage incomplete')
    for case in report['cases']:
        row=rows[case['id']];path=case['case']+'/effect.png';images[path]=digest((out/path).read_bytes())
        cards.append(f'<article><h2>{e(row["english"])}</h2><p lang="ja">{e(row["source"]["japanese"])}</p>'
                     f'<p>{e(case["case"])} · maximum {row["maximum_width"]}/216px · {row["maximum_bytes"]}/256 bytes</p>'
                     f'<img loading="lazy" width="480" height="320" src="{e(path)}" alt="{e(row["english"])}"></article>')
    page='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Torneko 2 player effects</title><style>body{margin:24px;background:#171923;color:#eee;font:16px system-ui}
main{display:grid;grid-template-columns:repeat(auto-fit,minmax(360px,1fr));gap:20px}article{padding:16px;background:#242838;border-radius:8px}
h2{font-size:18px}img{max-width:100%;height:auto;image-rendering:pixelated}code{overflow-wrap:anywhere}a{color:#bce}</style>
<h1>Torneko 2: one-line player effects</h1><p>Separate prototype: thirteen source reads, three name lengths each.
Controlled dispatch and resistance states exercise the native consumers; ordinary acquisition remains separate.</p>
<p>ROM <code>'''+report['rom_sha256']+'''</code> · <a href="report.json">Results and input schedules</a></p><main>'''+''.join(cards)+'</main></html>\n'
    if cumulative:page=page.replace('Separate prototype:', 'Cumulative candidate:')
    (out/'index.html').write_text(page)
    (out/'preview.json').write_text(json.dumps({'rom_sha256':report['rom_sha256'],'cases':39,'images':images},indent=2)+'\n')
    print(out/'index.html')

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--cumulative',action='store_true');run(parser.parse_args().cumulative)
