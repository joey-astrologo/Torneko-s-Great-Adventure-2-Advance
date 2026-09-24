"""Native one-line and fallback item-use announcement gallery."""
import argparse,html,json
from tools.rom import ROOT,digest,require

def run(cumulative=False):
    out=ROOT/('build/english/item-use-validation' if cumulative else 'build/item-use-prototype');build=json.loads((ROOT/'build/english/build.json' if cumulative else out/'build.json').read_text())
    report=json.loads((out/'report.json').read_text());rows={r['id']:r for r in build['item_use']['entries']}
    require(report['passed'] and report['rom_sha256']==build['output_sha256'] and len(report['cases'])==60,
            'Item-use evidence stale/incomplete')
    cards=[];images={};e=html.escape
    for case in report['cases']:
        row=rows[case['id']];path=case['case']+'/announcement.png';images[path]=digest((out/path).read_bytes())
        cards.append(f'<article><h2>{e(row["english"].replace(chr(10),""))}</h2>'
                     f'<p lang="ja">{e(row["source"]["japanese"])}</p><p>{e(case["case"])}</p>'
                     f'<p>Actual lines: {e(str(case["queue"]["line_widths"]))} / 216px each</p>'
                     f'<img loading="lazy" width="480" height="320" src="{e(path)}" alt="{e(case["case"])}"></article>')
    page='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Torneko 2 item-use announcements</title><style>body{margin:24px;background:#171923;color:#eee;font:16px system-ui}
main{display:grid;grid-template-columns:repeat(auto-fit,minmax(360px,1fr));gap:20px}article{padding:16px;background:#242838;border-radius:8px}
h2{font-size:18px}img{max-width:100%;height:auto;image-rendering:pixelated}code{overflow-wrap:anywhere}a{color:#bce}</style>
<h1>Torneko 2: item-use announcements</h1><p>Separate prototype: five formats and sixty controlled native cases.
Forty fit one line; twenty retain the full two-line message. Names, colour controls and spacing are preserved.</p>
<p>Drink supplies the native route; category overrides exercise the other verbs. Wide synthetic fields test bounds,
not custom naming or inscriptions.</p><p>ROM <code>'''+report['rom_sha256']+'''</code> · <a href="report.json">Results and input schedules</a></p><main>'''+''.join(cards)+'</main></html>\n'
    if cumulative:page=page.replace('Separate prototype:', 'Cumulative candidate:')
    (out/'index.html').write_text(page)
    (out/'preview.json').write_text(json.dumps({'rom_sha256':report['rom_sha256'],'cases':60,'images':images},indent=2)+'\n')
    print(out/'index.html')

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--cumulative',action='store_true');run(parser.parse_args().cumulative)
