"""Render the verified player status messages screenshot gallery and measured message budgets."""
import argparse,html,json
from tools.rom import ROOT,digest,require

def run(cumulative=False):
    out=ROOT/('build/english/player-message-validation' if cumulative else 'build/player-messages-prototype')
    ledger=ROOT/'build/english/build.json' if cumulative else out/'build.json'
    build=json.loads(ledger.read_text());report=json.loads((out/'report.json').read_text())
    require(report['passed'] and report['rom_sha256']==build['output_sha256'] and len(report['cases'])==6*(len(build['player_messages']['entries'])+3),
            'Player message gallery evidence stale/incomplete')
    rows={r['id']:r for r in build['player_messages']['entries']};e=html.escape;cards=[];images={}
    for case in report['cases']:
        row=rows.get(case['id'],{'english':case['id']+': unmapped pointer stays unchanged'});pictures=[]
        for name in ('selection.png','result.png'):
            relative=case['case']+'/'+name;images[relative]=digest((out/relative).read_bytes())
            pictures.append(f'<img width="480" height="320" loading="lazy" src="{e(relative)}" alt="{e(case["case"])} {name}">')
        q=case['queue'];metrics=f"Actual lines: {q['line_widths']}px; {q['bytes']} bytes including NUL. Native message capacity: 256 bytes."
        cards.append('<details><summary>'+e(case['case'])+'</summary><p>'+e(row['english'])+'</p><p>'+e(metrics)+'</p>'+''.join(pictures)+'</details>')
    page='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Torneko 2 player status messages review</title><style>body{background:#171923;color:#eee;font:16px system-ui;margin:24px}
details{background:#242838;padding:16px;margin:12px 0}img{image-rendering:pixelated;max-width:100%;height:auto;margin:8px}
code{overflow-wrap:anywhere}a{color:#bce}</style><h1>Torneko 2: player status messages</h1><p>'''+('Cumulative candidate. ' if cumulative else 'Separate prototype. ')+e(report['scope'])+'''</p>
<p>ROM <code>'''+report['rom_sha256']+'''</code> · <a href="report.json">Results and input schedules</a></p>'''+''.join(cards)+'</html>\n'
    (out/'index.html').write_text(page);(out/'preview.json').write_text(json.dumps({'rom_sha256':report['rom_sha256'],'cases':len(report['cases']),'images':images},indent=2)+'\n')
    print(out/'index.html')

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--cumulative',action='store_true');run(parser.parse_args().cumulative)
