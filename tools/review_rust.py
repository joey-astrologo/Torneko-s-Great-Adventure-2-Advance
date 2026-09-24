"""Source/English and native acid/rust messages, fields and equipment outcomes."""
import argparse
import html,json
from tools.rom import ROOT,digest,require
from tools.verify_rust import OUT


def run(cumulative=False):
    global OUT
    if cumulative:OUT=ROOT/'build/english/rust-validation'
    build=json.loads((ROOT/'build/english/build.json' if cumulative else OUT/'build.json').read_text());report=json.loads((OUT/'report.json').read_text())
    require(report['passed'] and report['rom_sha256']==build['output_sha256'],'Rust evidence stale')
    sources=''.join('<pre>'+html.escape(r['source']['japanese'])+'</pre><pre>'+html.escape(r['english'])+'</pre><p>Maximum fallback widths: '+str(r['maximum_line_widths'])+'px; maximum formatted size: '+str(r['maximum_bytes'])+' bytes.</p>' for r in build['rust']['entries'])
    cards=[];images={}
    for case in report['cases']:
        pictures=[]
        for name,expected in case['images'].items():
            relative=case['case']+'/'+name;require(digest((OUT/relative).read_bytes())==expected,'Rust screenshot changed');images[relative]=expected
            pictures.append('<img loading="lazy" width="480" height="320" src="'+html.escape(relative)+'">')
        cards.append('<details open><summary>'+html.escape(case['case'])+'</summary>'+''.join(pictures)+'</details>')
    page='''<!doctype html><html lang="en"><meta charset="utf-8"><title>Torneko 2 acid and rust</title><style>body{background:#171923;color:#eee;font:16px system-ui;margin:24px}details{background:#242838;padding:16px;margin:12px 0}pre{white-space:pre-wrap}img{image-rendering:pixelated;max-width:100%;height:auto;margin:8px}</style><h1>Torneko 2 acid and rust</h1><p>Separate eleven-binding prototype. Nineteen native cases cover acid activation/failure, shield/weapon degradation, empty equipment, material immunity, controlled protection/ring branches and the -99 limit. Native item-definition properties are retained in test records. The named resistance message uses the existing conditional break: ordinary names stay on one line; a maximum-width field safely uses two. Item colours,64-byte fields,256-byte output guards, native equipment changes and return state pass. Ordinary discovery and protection acquisition remain separate.</p>'''
    if cumulative:page=page.replace('Separate ', 'Integrated ').replace('prototype.', 'consumer.')
    (OUT/'index.html').write_text(page+sources+''.join(cards)+'\n');(OUT/'preview.json').write_text(json.dumps({'rom_sha256':build['output_sha256'],'cases':len(report['cases']),'images':images},indent=2)+'\n');print(OUT/'index.html')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cumulative',action='store_true')
    run(parser.parse_args().cumulative)
