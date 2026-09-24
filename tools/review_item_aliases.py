"""Build a native screenshot index for the isolated appearance prototype."""
import argparse,html,json
from tools.rom import ROOT,digest,require

def run(cumulative=False):
    out=ROOT/('build/english/item-alias-validation' if cumulative else 'build/item-alias-prototype')
    build=json.loads((ROOT/'build/english/build.json' if cumulative else out/'build.json').read_text());report=json.loads((out/'report.json').read_text())
    require(report['passed'] and report['rom_sha256']==build['output_sha256'],'Appearance evidence stale')
    rows={r['id']:r for r in build['aliases']['entries']}
    require({c['alias_id'] for c in report['cases'] if c['state']=='unknown'}==set(rows),'Appearance coverage incomplete')
    cards=[];images={}
    for case in report['cases']:
        row=rows[case['alias_id']];relative=case['case']+'/inventory.png';path=out/relative
        images[relative]=digest(path.read_bytes());e=html.escape
        cards.append(f'<article><h2>{e(row["name"])} <small>#{row["id"]}</small></h2>'
                     f'<p lang="ja">{e(row["source"]["name"]["japanese"])}</p>'
                     f'<p>Full name: {e(row["canonical_name"])}</p>'
                     f'<p>{row["display_width_px"]}/80px · {row["display_encoded_bytes"]}/31 bytes · {e(case["state"])}</p>'
                     f'<img loading="lazy" width="480" height="320" src="{e(relative)}" alt="Native inventory: {e(row["name"])}"></article>')
    page='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Torneko 2 item appearances</title><style>
body{margin:24px;background:#171923;color:#eee;font:16px system-ui}h1{font-size:28px}p{margin:7px 0}
main{display:grid;grid-template-columns:repeat(auto-fit,minmax(360px,1fr));gap:20px}
article{padding:16px;background:#242838;border-radius:8px}h2{margin:0;font-size:18px}small{color:#bbc}
img{display:block;max-width:100%;height:auto;image-rendering:pixelated;margin-top:12px}code{overflow-wrap:anywhere}a{color:#bce}
</style><h1>Torneko 2: unidentified item appearances</h1>
<p>Separate prototype: 154 English appearance names and 166 native cases. The selected T2 font and original menu geometry are retained.</p>
<p>Cases explicitly set an item’s appearance and identification state. Normal random assignment, custom names, inscriptions and ordinary discovery remain separate.</p>
<p>ROM <code>'''+report['rom_sha256']+'''</code> · <a href="report.json">Native results and input schedules</a></p><main>'''+''.join(cards)+'</main></html>\n'
    if cumulative:page=page.replace('Separate prototype:', 'Cumulative candidate:')
    (out/'index.html').write_text(page)
    (out/'preview.json').write_text(json.dumps({'rom_sha256':report['rom_sha256'],'native_cases':len(report['cases']),
                                             'appearance_names':len(rows),'images':images},indent=2)+'\n')
    print(out/'index.html')

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--cumulative',action='store_true');run(parser.parse_args().cumulative)
