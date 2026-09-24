"""Source text and bounded native well picker evidence."""
import argparse
import html,json
from tools.rom import ROOT,digest,require
from tools.verify_well_picker import OUT


def run(cumulative=False):
    global OUT
    if cumulative:OUT=ROOT/'build/english/well-picker-validation'
    build=json.loads((ROOT/'build/english/build.json' if cumulative else OUT/'build.json').read_text());report=json.loads((OUT/'report.json').read_text())
    require(report['passed'] and report['rom_sha256']==build['output_sha256'],'Stale well picker evidence');cards=[];images={}
    for case in report['cases']:
        pics=[]
        for name,expected in case['images'].items():
            relative=case['case']+'/'+name;require(digest((OUT/relative).read_bytes())==expected,'Well picker image changed');images[relative]=expected
            pics.append('<img loading="lazy" width="480" height="320" src="'+html.escape(relative)+'">')
        cards.append('<details><summary>'+html.escape(case['case'])+'</summary>'+''.join(pics)+'</details>')
    source=''.join('<pre>'+html.escape(row['source']['japanese'])+'</pre><pre>'+html.escape(row['english'])+'</pre><p>'+html.escape(str(row['layout']))+'</p>' for row in build['well_picker']['entries'])
    page='''<!doctype html><html lang="en"><meta charset="utf-8"><title>Torneko 2 well picker</title><style>body{background:#171923;color:#eee;font:16px system-ui;margin:24px}details{background:#242838;padding:16px;margin:12px 0}pre{white-space:pre-wrap}img{image-rendering:pixelated;max-width:100%;height:auto;margin:8px}</style><h1>Torneko 2 well picker</h1><p>Separate two-source prototype. Original geometry and native bounded number input. Controlled progress-getter returns; cancellation, minimum/maximum and native output flags checked. The English level template reuses Remi's measured proportional-font resource. Ordinary unlocking and dungeon entry remain separate.</p>'''
    page=page.replace('Separate six-source prototype.', 'Six owned sources.').replace('Separate two-source prototype.', 'Two owned sources.').replace('Separate five-source prototype.', 'Five owned sources.') if cumulative else page
    (OUT/'index.html').write_text(page+source+''.join(cards)+'\n');(OUT/'preview.json').write_text(json.dumps({'rom_sha256':build['output_sha256'],'cases':len(report['cases']),'images':images},indent=2)+'\n');print(OUT/'index.html')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cumulative',action='store_true')
    run(parser.parse_args().cumulative)

